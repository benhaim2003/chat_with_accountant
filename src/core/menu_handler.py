from __future__ import annotations

import logging

from src.core import session_manager, texts
from src.models.internal_message import InternalMessage, MessageType
from src.models.menu_response import MenuResponse
from src.repositories.pilot_clients import client_label
from src.services.email_gateway import GraphEmailGateway

logger = logging.getLogger(__name__)


class State:
    # Values are persisted in Redis sessions — renaming one breaks live conversations.
    IDLE = "idle"
    MAIN_MENU = "awaiting_option"
    REQUEST_TYPE = "awaiting_request_type"
    REQUEST_DETAILS = "awaiting_request_details"
    FILE_UPLOAD = "awaiting_file_upload"
    DESCRIPTION_CHOICE = "awaiting_description_choice"
    DESCRIPTION = "awaiting_description"
    FREE_TEXT_REQUEST = "awaiting_file_request"
    ACCOUNTANT_MESSAGE = "awaiting_accountant_message"
    FOLLOWUP = "awaiting_followup_decision"


class FlowKind:
    UPLOAD = "upload"
    REQUEST = "request"
    MESSAGE = "message"


class MenuHandler:
    def __init__(self, email_gateway: GraphEmailGateway) -> None:
        self._email = email_gateway
        self._handlers = {
            State.MAIN_MENU: self._handle_main_menu,
            State.FILE_UPLOAD: self._handle_file_upload,
            State.DESCRIPTION_CHOICE: self._handle_description_choice,
            State.DESCRIPTION: self._handle_description,
            State.REQUEST_TYPE: self._handle_request_type,
            State.REQUEST_DETAILS: self._handle_request_details,
            State.FREE_TEXT_REQUEST: self._handle_free_text_request,
            State.ACCOUNTANT_MESSAGE: self._handle_accountant_message,
            State.FOLLOWUP: self._handle_followup,
        }

    def handle(self, message: InternalMessage) -> MenuResponse:
        session = session_manager.get_session(message.chat_id, message.platform)

        if session.state == State.IDLE or message.text in ("/start", "/menu"):
            return self._show_main_menu(message)

        handler = self._handlers.get(session.state)
        if handler is None:
            logger.warning("Unknown state '%s' for %s — resetting", session.state, message.chat_id)
            return self._show_main_menu(message)
        return handler(message)

    def handle_close(self, chat_id: str, platform) -> MenuResponse:
        session_manager.clear_session(chat_id, platform)
        return MenuResponse(text=texts.CONVERSATION_CLOSED)

    @staticmethod
    def _show_main_menu(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, State.MAIN_MENU, message.platform)
        return MenuResponse(text=texts.GREETING, buttons=texts.MAIN_MENU_BUTTONS)

    def _handle_main_menu(self, message: InternalMessage) -> MenuResponse:
        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=texts.MAIN_MENU_BUTTONS)

        choice = (message.text or "").strip()
        if choice == texts.OPTION_UPLOAD:
            return self._start_upload(message)
        if choice == texts.OPTION_REQUEST:
            return self._start_request(message)
        if choice == texts.OPTION_MESSAGE:
            return self._start_message(message)
        return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=texts.MAIN_MENU_BUTTONS)

    @staticmethod
    def _start_upload(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, State.FILE_UPLOAD, message.platform)
        return MenuResponse(text=texts.UPLOAD_PROMPT)

    def _handle_file_upload(self, message: InternalMessage) -> MenuResponse:
        if message.message_type not in (MessageType.DOCUMENT, MessageType.PHOTO):
            return MenuResponse(text=texts.UPLOAD_NOT_A_FILE)

        session_manager.set_state(
            message.chat_id, State.DESCRIPTION_CHOICE, message.platform,
            pending_file_path=message.file_path,
            pending_file_name=message.file_name or "לא ידוע",
        )
        return MenuResponse(text=texts.UPLOAD_ASK_DESCRIPTION, buttons=texts.YES_NO_BUTTONS)

    def _handle_description_choice(self, message: InternalMessage) -> MenuResponse:
        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=texts.YES_NO_BUTTONS)

        answer = (message.text or "").strip()
        if answer == texts.YES:
            session_manager.set_state(message.chat_id, State.DESCRIPTION, message.platform)
            return MenuResponse(text=texts.UPLOAD_DESCRIPTION_PROMPT)
        if answer == texts.NO:
            return self._finish_upload(message, description=None)
        return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=texts.YES_NO_BUTTONS)

    def _handle_description(self, message: InternalMessage) -> MenuResponse:
        return self._finish_upload(message, description=message.text)

    def _finish_upload(self, message: InternalMessage, description: str | None) -> MenuResponse:
        session = session_manager.get_session(message.chat_id, message.platform)
        subject, body = texts.upload_email(
            client=client_label(message.chat_id),
            file_name=session.context.get("pending_file_name", "לא ידוע"),
            description=description,
        )
        thread_id = self._email.send(
            subject=subject,
            body=body,
            attachment_path=session.context.get("pending_file_path"),
            chat_id=message.chat_id,
            platform=message.platform.value,
        )
        return self._finish_flow(message, FlowKind.UPLOAD, texts.UPLOAD_DONE, subject, thread_id)

    @staticmethod
    def _start_request(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, State.REQUEST_TYPE, message.platform)
        return MenuResponse(text=texts.REQUEST_TYPE_PROMPT, buttons=texts.REQUEST_TYPE_BUTTONS)

    def _handle_request_type(self, message: InternalMessage) -> MenuResponse:
        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=texts.REQUEST_TYPE_BUTTONS)

        choice = (message.text or "").strip()

        if choice == texts.REQUEST_OTHER:
            session_manager.set_state(message.chat_id, State.FREE_TEXT_REQUEST, message.platform)
            return MenuResponse(text=texts.REQUEST_FREE_TEXT_PROMPT)

        doc_type = texts.REQUEST_TYPES.get(choice)
        if doc_type is None:
            return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=texts.REQUEST_TYPE_BUTTONS)

        detail_prompt = texts.REQUEST_DETAIL_PROMPTS.get(choice)
        if detail_prompt:
            session_manager.set_state(
                message.chat_id, State.REQUEST_DETAILS, message.platform,
                pending_request_type=doc_type,
                pending_request_prompt=detail_prompt,
            )
            return MenuResponse(text=detail_prompt)

        return self._finish_request(message, f"בקשת מסמך — {doc_type}", doc_type)

    def _handle_request_details(self, message: InternalMessage) -> MenuResponse:
        session = session_manager.get_session(message.chat_id, message.platform)
        details = (message.text or "").strip()

        if message.message_type != MessageType.TEXT or not details:
            prompt = session.context.get("pending_request_prompt", texts.REQUEST_TYPE_PROMPT)
            return MenuResponse(text=prompt)

        doc_type = session.context.get("pending_request_type", "מסמך")
        return self._finish_request(
            message, f"בקשת מסמך — {doc_type}", f"{doc_type}\nפרטים: {details}"
        )

    def _handle_free_text_request(self, message: InternalMessage) -> MenuResponse:
        return self._finish_request(message, "בקשת קובץ", message.text or "")

    def _finish_request(self, message: InternalMessage, subject_detail: str, request_text: str) -> MenuResponse:
        subject, body = texts.request_email(client_label(message.chat_id), subject_detail, request_text)
        thread_id = self._email.send(
            subject=subject,
            body=body,
            chat_id=message.chat_id,
            platform=message.platform.value,
        )
        return self._finish_flow(message, FlowKind.REQUEST, texts.REQUEST_DONE, subject, thread_id)

    @staticmethod
    def _start_message(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, State.ACCOUNTANT_MESSAGE, message.platform)
        return MenuResponse(text=texts.MESSAGE_PROMPT)

    def _handle_accountant_message(self, message: InternalMessage) -> MenuResponse:
        subject, body = texts.accountant_message_email(client_label(message.chat_id), message.text or "")
        thread_id = self._email.send(
            subject=subject,
            body=body,
            chat_id=message.chat_id,
            platform=message.platform.value,
        )
        return self._finish_flow(message, FlowKind.MESSAGE, texts.MESSAGE_DONE, subject, thread_id)

    def _finish_flow(
        self,
        message: InternalMessage,
        flow_kind: str,
        confirmation: str,
        subject: str,
        thread_id: str | None,
    ) -> MenuResponse:
        session_manager.set_state(
            message.chat_id, State.FOLLOWUP, message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            flow_kind=flow_kind,
        )
        return MenuResponse(
            text=confirmation + "\n\n" + texts.FOLLOWUP_PROMPT,
            buttons=texts.FOLLOWUP_BUTTONS[flow_kind],
        )

    def _handle_followup(self, message: InternalMessage) -> MenuResponse:
        session = session_manager.get_session(message.chat_id, message.platform)
        flow_kind = session.context.get("flow_kind", FlowKind.UPLOAD)
        buttons = texts.FOLLOWUP_BUTTONS.get(flow_kind, texts.FOLLOWUP_BUTTONS[FlowKind.UPLOAD])

        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=buttons)

        choice = (message.text or "").strip()

        if choice == texts.FOLLOWUP_AGAIN:
            starters = {
                FlowKind.UPLOAD: self._start_upload,
                FlowKind.REQUEST: self._start_request,
                FlowKind.MESSAGE: self._start_message,
            }
            starter = starters.get(flow_kind, self._show_main_menu)
            return starter(message)

        if choice == texts.FOLLOWUP_MENU:
            return self._show_main_menu(message)

        if choice == texts.FOLLOWUP_CLOSE:
            session_manager.set_state(message.chat_id, State.IDLE, message.platform)
            return MenuResponse(text=texts.CONVERSATION_CLOSED_SMILEY)

        return MenuResponse(text=texts.TAP_BUTTON_REMINDER, buttons=buttons)
