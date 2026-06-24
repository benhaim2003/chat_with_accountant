from __future__ import annotations

import logging
import threading
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from src.adapters.base import PlatformAdapter
from src.core.message_router import MessageRouter
from src.models.internal_message import InternalMessage, MessageType, Platform
from src.models.menu_response import MenuResponse
from src.services.file_handler import FileHandler

logger = logging.getLogger(__name__)

_WA_BASE = "https://graph.facebook.com/v19.0"
_WA_BUTTON_LABEL_MAX = 20
_WA_MAX_BUTTONS = 3


class WhatsAppAdapter(PlatformAdapter):
    def __init__(
        self,
        token: str,
        phone_number_id: str,
        verify_token: str,
        router: MessageRouter,
        file_handler: FileHandler,
        port: int = 8080,
    ) -> None:
        self._token = token
        self._phone_number_id = phone_number_id
        self._verify_token = verify_token
        self._router = router
        self._files = file_handler
        self._port = port
        self._fastapi_app = self._build_app()

    # ---------------------------------------------------------------- public

    def send_text(self, chat_id: str, text: str) -> None:
        self._post_message(chat_id, {"type": "text", "text": {"body": text}})

    def send_response(self, chat_id: str, response: MenuResponse) -> None:
        if not response.buttons:
            self.send_text(chat_id, response.text)
            return

        buttons = response.buttons[:_WA_MAX_BUTTONS]
        payload = {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": response.text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": b.payload,
                                "title": b.label[:_WA_BUTTON_LABEL_MAX],
                            },
                        }
                        for b in buttons
                    ]
                },
            },
        }
        self._post_message(chat_id, payload)

    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> None:
        media_id = self._upload_media(file_path)
        self._post_message(chat_id, {
            "type": "document",
            "document": {"id": media_id, "caption": caption},
        })

    def start(self) -> None:
        t = threading.Thread(
            target=uvicorn.run,
            kwargs={"app": self._fastapi_app, "host": "0.0.0.0", "port": self._port, "log_level": "warning"},
            daemon=True,
            name="whatsapp-webhook",
        )
        t.start()
        logger.info("WhatsApp webhook server started on port %d", self._port)

    # ---------------------------------------------------------------- FastAPI

    def _build_app(self) -> FastAPI:
        app = FastAPI()
        adapter = self  # capture for closures

        @app.get("/webhook/whatsapp")
        async def verify(request: Request):
            params = dict(request.query_params)
            mode = params.get("hub.mode")
            token = params.get("hub.verify_token")
            challenge = params.get("hub.challenge")
            if mode == "subscribe" and token == adapter._verify_token:
                return PlainTextResponse(challenge)
            return Response(status_code=403)

        @app.post("/webhook/whatsapp")
        async def receive(request: Request):
            try:
                data = await request.json()
                adapter._handle_payload(data)
            except Exception as exc:
                logger.error("WhatsApp webhook error: %s", exc)
            return {"status": "ok"}

        return app

    # ---------------------------------------------------------------- webhook dispatch

    def _handle_payload(self, data: dict) -> None:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                for msg in change.get("value", {}).get("messages", []):
                    try:
                        self._dispatch(msg)
                    except Exception as exc:
                        logger.error("Failed to dispatch WhatsApp message: %s", exc)

    def _dispatch(self, msg: dict) -> None:
        chat_id = msg.get("from", "")
        msg_type = msg.get("type", "")

        if msg_type == "text":
            text = msg.get("text", {}).get("body", "")
            internal = InternalMessage(
                platform=Platform.WHATSAPP,
                chat_id=chat_id,
                message_type=MessageType.TEXT,
                text=text,
            )
        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
            payload = reply.get("id", "")
            internal = InternalMessage(
                platform=Platform.WHATSAPP,
                chat_id=chat_id,
                message_type=MessageType.TEXT,
                text=payload,
            )
        elif msg_type == "document":
            doc = msg.get("document", {})
            filename = doc.get("filename", "upload.pdf")
            file_path = self._download_media(doc.get("id", ""), filename)
            internal = InternalMessage(
                platform=Platform.WHATSAPP,
                chat_id=chat_id,
                message_type=MessageType.DOCUMENT,
                file_path=file_path,
                file_name=filename,
            )
        elif msg_type == "image":
            image = msg.get("image", {})
            media_id = image.get("id", "")
            filename = f"{media_id}.jpg"
            file_path = self._download_media(media_id, filename)
            internal = InternalMessage(
                platform=Platform.WHATSAPP,
                chat_id=chat_id,
                message_type=MessageType.PHOTO,
                file_path=file_path,
                file_name=filename,
            )
        else:
            logger.debug("Unsupported WhatsApp message type: %s", msg_type)
            return

        response = self._router.route(internal)
        self.send_response(chat_id, response)

    # ---------------------------------------------------------------- Graph API helpers

    def _post_message(self, chat_id: str, payload: dict) -> None:
        r = requests.post(
            f"{_WA_BASE}/{self._phone_number_id}/messages",
            headers=self._auth_headers(),
            json={"messaging_product": "whatsapp", "to": chat_id, **payload},
            timeout=30,
        )
        r.raise_for_status()

    def _upload_media(self, file_path: str) -> str:
        path = Path(file_path)
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{_WA_BASE}/{self._phone_number_id}/media",
                headers={"Authorization": f"Bearer {self._token}"},
                files={"file": (path.name, f, "application/octet-stream")},
                data={"messaging_product": "whatsapp"},
                timeout=60,
            )
        r.raise_for_status()
        return r.json()["id"]

    def _download_media(self, media_id: str, filename: str) -> str:
        r = requests.get(
            f"{_WA_BASE}/{media_id}",
            headers=self._auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        url = r.json()["url"]

        r = requests.get(url, headers=self._auth_headers(), timeout=60)
        r.raise_for_status()
        return self._files.save_bytes(r.content, filename)

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
