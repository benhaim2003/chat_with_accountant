from __future__ import annotations
import logging
from src.models.internal_message import InternalMessage, MessageType
from src.core import session_manager
from src.services.email_gateway import EmailGateway
from src.services.file_handler import FileHandler
from src.services.classifier import classify_document

logger = logging.getLogger(__name__)

_MENU_TEXT = (
    "Welcome to the CPA Office Bot.\n\n"
    "Please choose an option:\n"
    "  A — Upload an invoice or bill of costs\n"
    "  B — Request a file from the office\n"
    "  C — Leave a message for your accountant\n"
    "  D — Other"
)

_SESSION_DECISION_TEXT = (
    "Is there anything else you'd like to send to the office?\n\n"
    "  1 — Yes, keep this session open\n"
    "  2 — No, close this session"
)

_CLOSE_KEYWORDS = {"2", "no", "close", "done", "end", "finish", "stop", "exit"}
_KEEP_KEYWORDS = {"1", "yes", "keep", "continue", "more", "send", "open"}

_STATE_HANDLERS = {
    "awaiting_option":            "_route_option",
    "awaiting_file_upload":       "_handle_upload",
    "awaiting_file_request":      "_handle_file_request",
    "awaiting_accountant_message":"_handle_accountant_message",
    "awaiting_other":             "_handle_other",
    "awaiting_session_decision":  "_handle_session_decision",
    "session_open":               "_handle_session_open",
}


class MenuHandler:
    def __init__(self, email_gateway: EmailGateway, file_handler: FileHandler) -> None:
        self._email = email_gateway
        self._files = file_handler

    def handle(self, message: InternalMessage) -> str:
        session = session_manager.get_session(message.chat_id, message.platform)

        if session.state == "idle" or message.text in ("/start", "/menu"):
            return self._show_menu(message)

        handler_name = _STATE_HANDLERS.get(session.state)
        if handler_name:
            return getattr(self, handler_name)(message)

        logger.warning("Unknown state '%s' for %s — resetting", session.state, message.chat_id)
        return self._show_menu(message)

    # ------------------------------------------------------------------ menu

    def _show_menu(self, message: InternalMessage) -> str:
        session_manager.set_state(message.chat_id, "awaiting_option", message.platform)
        return _MENU_TEXT

    # ---------------------------------------------------------- option router

    def _route_option(self, message: InternalMessage) -> str:
        choice = (message.text or "").strip().upper()

        if choice == "A":
            session_manager.set_state(message.chat_id, "awaiting_file_upload", message.platform)
            return "Please upload the invoice or bill of costs as a PDF."

        if choice == "B":
            session_manager.set_state(message.chat_id, "awaiting_file_request", message.platform)
            return "Please describe which file you need from the office."

        if choice == "C":
            session_manager.set_state(
                message.chat_id, "awaiting_accountant_message", message.platform
            )
            return "Please type your message for your accountant."

        if choice == "D":
            session_manager.set_state(message.chat_id, "awaiting_other", message.platform)
            return "Please type your message and we will get back to you."

        return f"Please reply with A, B, C, or D.\n\n{_MENU_TEXT}"

    # ---------------------------------------------------- option A: upload

    def _handle_upload(self, message: InternalMessage) -> str:
        if message.message_type not in (MessageType.DOCUMENT, MessageType.PHOTO):
            return "Please send the file as a document or photo attachment."

        doc_type = classify_document(message.file_path) if message.file_path else "other"
        subject = f"[CPA Bot] Document upload — chat {message.chat_id}"
        body = (
            f"A client (chat ID: {message.chat_id}) uploaded a document.\n"
            f"Classified as: {doc_type}\n"
            f"Filename: {message.file_name or 'unknown'}"
        )
        thread_id = self._email.send(
            subject=subject,
            body=body,
            attachment_path=message.file_path,
            chat_id=message.chat_id,
        )
        session_manager.set_state(
            message.chat_id, "awaiting_session_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
        )
        return (
            "Thank you! Your document has been received and forwarded to the office.\n\n"
            + _SESSION_DECISION_TEXT
        )

    # ------------------------------------------------- option B: file request

    def _handle_file_request(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] File request — chat {message.chat_id}"
        body = (
            f"A client (chat ID: {message.chat_id}) is requesting a file.\n\n"
            f"Request: {message.text}"
        )
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id)
        session_manager.set_state(
            message.chat_id, "awaiting_session_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
        )
        return (
            "Your request has been forwarded to the office.\n\n"
            + _SESSION_DECISION_TEXT
        )

    # ------------------------------------------ option C: accountant message

    def _handle_accountant_message(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] Client message — chat {message.chat_id}"
        body = (
            f"A client (chat ID: {message.chat_id}) left a message:\n\n"
            f"{message.text}"
        )
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id)
        session_manager.set_state(
            message.chat_id, "awaiting_session_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
        )
        return (
            "Your message has been forwarded to your accountant.\n\n"
            + _SESSION_DECISION_TEXT
        )

    # ---------------------------------------------------- option D: other

    def _handle_other(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] General inquiry — chat {message.chat_id}"
        body = (
            f"A client (chat ID: {message.chat_id}) sent a general inquiry:\n\n"
            f"{message.text}"
        )
        # Phase 3 hook: replace email send with LLM processing here
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id)
        session_manager.set_state(
            message.chat_id, "idle", message.platform, active_thread_id=thread_id
        )
        return "Thank you! Your message has been received. We will get back to you soon."

    # ------------------------------------------- session close/keep decision

    def _handle_session_decision(self, message: InternalMessage) -> str:
        text = (message.text or "").strip().lower()

        if text in _CLOSE_KEYWORDS:
            session_manager.set_state(message.chat_id, "idle", message.platform)
            return (
                "Session closed. Whenever you need us again, just send a message and "
                "we'll show you the menu."
            )

        if text in _KEEP_KEYWORDS:
            session_manager.set_state(message.chat_id, "session_open", message.platform)
            return "Got it! Send your next message and it will be forwarded to the office."

        return f"Please reply with 1 (keep) or 2 (close).\n\n{_SESSION_DECISION_TEXT}"

    # ----------------------------------------- open session: free-form relay

    def _handle_session_open(self, message: InternalMessage) -> str:
        session = session_manager.get_session(message.chat_id, message.platform)
        subject = session.context.get(
            "follow_up_subject", f"[CPA Bot] Follow-up — chat {message.chat_id}"
        )

        if message.message_type in (MessageType.DOCUMENT, MessageType.PHOTO):
            doc_type = classify_document(message.file_path) if message.file_path else "other"
            body = (
                f"Follow-up from client (chat ID: {message.chat_id}) — document.\n"
                f"Classified as: {doc_type}\n"
                f"Filename: {message.file_name or 'unknown'}"
            )
            self._email.send(
                subject=subject,
                body=body,
                attachment_path=message.file_path,
                chat_id=message.chat_id,
            )
        else:
            body = f"Follow-up from client (chat ID: {message.chat_id}):\n\n{message.text}"
            self._email.send(subject=subject, body=body, chat_id=message.chat_id)

        session_manager.set_state(
            message.chat_id, "awaiting_session_decision", message.platform
        )
        return f"Message forwarded to the office.\n\n{_SESSION_DECISION_TEXT}"
