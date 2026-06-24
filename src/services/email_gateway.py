from __future__ import annotations

import base64
import html
import logging
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import msal
import requests

from src.infrastructure.redis_client import get_redis

_ATTACHMENT_DIR = Path(tempfile.gettempdir()) / "cpa_bot_uploads"
_ATTACHMENT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
# Attachments at or under this size are sent inline (base64) in one request.
# Larger ones require a chunked upload session.
_SMALL_ATTACHMENT_LIMIT = 3 * 1024 * 1024  # 3 MB
# Upload-session chunks must be a multiple of 320 KiB (except the final chunk).
_UPLOAD_CHUNK = 320 * 1024 * 10  # 3,276,800 bytes

# Signature: (platform, chat_id, reply_text, attachment_paths, close_requested) -> None
ReplyCallback = Callable[[str, str, str, list[str], bool], None]


class GraphEmailGateway:
    _CLOSE_MARKER = "#close"
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        mailbox: str,
        secretariat_address: str,
    ) -> None:
        self._mailbox = mailbox
        self._secretariat = secretariat_address
        self._msal = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        self._reply_callback: Optional[ReplyCallback] = None
        self._polling = False

    # --------------------------------------------------------------- auth

    def _token(self) -> str:
        # MSAL caches the token in memory and auto-refreshes near expiry, so it is
        # cheap and safe to call this before every request.
        result = self._msal.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise RuntimeError(
                f"Token acquisition failed: {result.get('error')} - "
                f"{result.get('error_description')}"
            )
        return result["access_token"]

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def _url(self, suffix: str = "") -> str:
        return f"{GRAPH_BASE}/users/{self._mailbox}{suffix}"

    # --------------------------------------------------------------- public API

    def set_reply_callback(self, callback: ReplyCallback) -> None:
        self._reply_callback = callback

    def send(
        self,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        chat_id: Optional[str] = None,
        platform: str = "telegram",
    ) -> Optional[str]:
        draft = {
            "subject": subject,
            "body": {"contentType": "html", "content": self._build_rtl_html(body)},
            "toRecipients": [{"emailAddress": {"address": self._secretariat}}],
        }
        try:
            # 1) Create a draft first so we can capture conversationId before sending
            #    (the sendMail action returns no body, so it can't give us the id).
            r = requests.post(
                self._url("/messages"), headers=self._headers(), json=draft, timeout=30
            )
            r.raise_for_status()
            msg = r.json()
            message_id = msg["id"]
            conversation_id = msg["conversationId"]

            # 2) Attach the file, if any.
            if attachment_path and Path(attachment_path).exists():
                self._attach_file(message_id, Path(attachment_path))

            # 3) Send the draft.
            r = requests.post(
                self._url(f"/messages/{message_id}/send"),
                headers=self._headers(), timeout=30,
            )
            r.raise_for_status()

            if chat_id:
                get_redis().set(f"thread:{conversation_id}", f"{platform}:{chat_id}", ex=604_800)  # 7 days
            logger.info("Email sent: %s", subject)
            return conversation_id
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            return None

    # --------------------------------------------------------------- attachments (send)

    def _attach_file(self, message_id: str, path: Path) -> None:
        size = path.stat().st_size
        if size <= _SMALL_ATTACHMENT_LIMIT:
            payload = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": path.name,
                "contentBytes": base64.b64encode(path.read_bytes()).decode(),
            }
            r = requests.post(
                self._url(f"/messages/{message_id}/attachments"),
                headers=self._headers(), json=payload, timeout=60,
            )
            r.raise_for_status()
        else:
            self._attach_large_file(message_id, path, size)

    def _attach_large_file(self, message_id: str, path: Path, size: int) -> None:
        session_payload = {
            "AttachmentItem": {
                "attachmentType": "file",
                "name": path.name,
                "size": size,
            }
        }
        r = requests.post(
            self._url(f"/messages/{message_id}/attachments/createUploadSession"),
            headers=self._headers(), json=session_payload, timeout=30,
        )
        r.raise_for_status()
        upload_url = r.json()["uploadUrl"]

        with open(path, "rb") as f:
            start = 0
            while start < size:
                chunk = f.read(_UPLOAD_CHUNK)
                end = start + len(chunk) - 1
                # The upload URL is pre-authorized — do NOT attach the bearer token.
                resp = requests.put(
                    upload_url,
                    headers={
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end}/{size}",
                    },
                    data=chunk, timeout=120,
                )
                if resp.status_code not in (200, 201, 202):
                    resp.raise_for_status()
                start = end + 1

    # --------------------------------------------------------------- polling

    def start_polling(self, interval_seconds: int = 30) -> None:
        self._polling = True
        t = threading.Thread(
            target=self._poll_loop, args=(interval_seconds,),
            daemon=True, name="graph-email-poller",
        )
        t.start()
        logger.info("Graph email poller started (every %ds)", interval_seconds)

    def stop_polling(self) -> None:
        self._polling = False

    def _poll_loop(self, interval: int) -> None:
        while self._polling:
            try:
                self._check_inbox()
            except Exception as exc:
                logger.error("Email poller error: %s", exc)
            time.sleep(interval)

    def _check_inbox(self) -> None:
        params = {
            "$filter": "isRead eq false",
            "$select": "id,conversationId,subject,uniqueBody,from",
            "$expand": "attachments",
            "$orderby": "receivedDateTime asc",
            "$top": "25",
        }
        # Prefer header => body/uniqueBody returned as plain text (no HTML parsing).
        headers = self._headers({"Prefer": 'outlook.body-content-type="text"'})
        r = requests.get(
            self._url("/mailFolders/inbox/messages"),
            headers=headers, params=params, timeout=30,
        )
        r.raise_for_status()
        messages = r.json().get("value", [])
        if messages:
            logger.debug("Checking %d unread message(s)", len(messages))
        for msg in messages:
            msg_id = msg["id"]
            try:
                self._process_reply(msg)
            except Exception as exc:
                logger.error("Failed to process message %s: %s", msg_id, exc)
            finally:
                # Always mark read, even on failure, so one poison message can't
                # wedge the poller into reprocessing it every cycle forever.
                self._mark_read(msg_id)

    def _mark_read(self, message_id: str) -> None:
        try:
            requests.patch(
                self._url(f"/messages/{message_id}"),
                headers=self._headers(), json={"isRead": True}, timeout=30,
            ).raise_for_status()
        except Exception as exc:
            logger.error("Failed to mark message read %s: %s", message_id, exc)

    def _process_reply(self, msg: dict) -> None:
        if not self._reply_callback:
            return
        conversation_id = msg.get("conversationId", "")
        raw = get_redis().get(f"thread:{conversation_id}")
        if not raw:
            logger.debug("Skipping message: conversationId not in thread map")
            return
        platform, _, chat_id = raw.partition(":")
        if not chat_id:  # legacy value without platform prefix
            platform, chat_id = "telegram", raw

        unique_body = msg.get("uniqueBody") or {}
        raw_text = unique_body.get("content", "")
        body_type = unique_body.get("contentType", "unknown")
        logger.info("RAW uniqueBody contentType=%s len=%d content=%r", body_type, len(raw_text), raw_text[:500])
        subject = msg.get("subject", "")
        body, close_requested = self._extract_body_and_marker(raw_text, subject)
        logger.info("AFTER STRIP len=%d content=%r close=%s", len(body), body[:200], close_requested)
        attachments = self._save_attachments(msg)
        self._reply_callback(platform, chat_id, body, attachments, close_requested)

    _FOOTER_SEPARATOR = '* אם ברצונך לסיים שיחה זו הוסיפי: "#close" להודעה'

    @staticmethod
    def _build_rtl_html(body: str) -> str:
        lines = html.escape(body).replace("\n", "<br>")
        footer_html = html.escape('* אם ברצונך לסיים שיחה זו הוסיפי: "#close" להודעה')
        return (
            '<html><body dir="rtl" lang="he" '
            'style="direction:rtl;text-align:right;font-family:Arial,sans-serif;">'
            f"<p>{lines}</p>"
            '<hr style="border:none;border-top:1px solid #ccc;margin:16px 0;">'
            f'<p style="color:#888;font-size:0.85em;">{footer_html}</p>'
            "</body></html>"
        )

    def _extract_body_and_marker(self, text: str, subject: str) -> tuple[str, bool]:
        clean = (text or "").strip()
        clean = clean.replace("\r\n", "\n")
        clean = self._strip_our_footer(clean)
        clean = self._strip_quoted_text(clean)

        close_requested = (
            self._CLOSE_MARKER in clean.lower()
            or self._CLOSE_MARKER in (subject or "").lower()
        )
        if close_requested:
            clean = re.sub(r"#close", "", clean, flags=re.IGNORECASE).strip()
        return clean, close_requested

    def _strip_our_footer(self, body: str) -> str:
        idx = body.find(self._FOOTER_SEPARATOR)
        if idx != -1:
            return body[:idx].strip()
        return body

    @staticmethod
    def _strip_quoted_text(body: str) -> str:
        match = re.search(r"\nOn\s.{5,300}wrote:\s*\n", body, re.DOTALL)
        if match:
            return body[: match.start()].strip()
        match = re.search(r"(?:^|\n)[‎‏‪-‮‫⁦-⁩]*בתאריך\s", body)
        if match:
            return body[: match.start()].strip()
        match = re.search(r"\n[-_]{3,}\s*\n.*?From:.*?Sent:", body, re.DOTALL)
        if match:
            return body[: match.start()].strip()
        lines = [line for line in body.splitlines() if not line.startswith(">")]
        return "\n".join(lines).strip()


    def _save_attachments(self, msg: dict) -> list[str]:
        saved: list[str] = []
        for att in msg.get("attachments", []):
            if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
                continue  # skip itemAttachment / referenceAttachment
            # Sanitize: strip any directory components a crafted name might carry.
            name = Path(att.get("name") or f"attachment_{att.get('id', '')}").name
            content_b64 = att.get("contentBytes")
            if content_b64 is None:
                # $expand does not inline very large attachments — fetch separately.
                content_b64 = self._fetch_attachment_bytes(msg["id"], att["id"])
            if not content_b64:
                continue
            dest = _ATTACHMENT_DIR / name
            dest.write_bytes(base64.b64decode(content_b64))
            saved.append(str(dest))
            logger.debug("Saved secretary attachment: %s", dest)
        return saved

    def _fetch_attachment_bytes(self, message_id: str, attachment_id: str) -> Optional[str]:
        r = requests.get(
            self._url(f"/messages/{message_id}/attachments/{attachment_id}"),
            headers=self._headers(), timeout=60,
        )
        r.raise_for_status()
        return r.json().get("contentBytes")