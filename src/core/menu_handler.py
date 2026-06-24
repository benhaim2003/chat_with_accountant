from __future__ import annotations
import logging
from src.models.internal_message import InternalMessage, MessageType
from src.core import session_manager
from src.services.email_gateway import GraphEmailGateway
from src.services.file_handler import FileHandler

logger = logging.getLogger(__name__)

_MENU_TEXT = (
    "תודה שפנית למוקד של רבינוביץ אבן ממן :)\n\n"
    "איך נוכל לעזור לך:\n"
    "  1 — שליחת מסמך/חשבונית למשרד\n"
    "  2 — בקשת מסמך מהמשרד\n"
    "  3 — השארת הודעה לרואה החשבון\n\n"
    "ניתן בכל עת לשלוח /close לסיום השיחה."
)

_SESSION_DECISION_TEXT = (
    "האם לסגור את השיחה?\n\n"
    "  1 — כן, סגור את השיחה\n"
    "  2 — לא, אני רוצה להמשיך לשלוח הודעות"
)

_CLOSE_KEYWORDS = {"1", "כן", "סגור", "סיים", "סגירה", "יציאה"}
_KEEP_KEYWORDS  = {"2", "לא", "פתוח", "המשך", "עוד"}

_OPTION_A = {"1"}
_OPTION_B = {"2"}
_OPTION_C = {"3"}

_YES_KEYWORDS = {"כן", "1", "y", "yes"}
_NO_KEYWORDS  = {"לא", "2", "n", "no"}

_STATE_HANDLERS = {
    "awaiting_option":                   "_route_option",
    "awaiting_file_upload":              "_handle_upload",
    "awaiting_description_choice":       "_handle_description_choice",
    "awaiting_description":              "_handle_description",
    "awaiting_file_request":             "_handle_file_request",
    "awaiting_accountant_message":       "_handle_accountant_message",
    "collecting_accountant_messages":    "_handle_collecting_accountant_messages",
    "awaiting_session_decision":         "_handle_session_decision",
}


class MenuHandler:
    def __init__(self, email_gateway: GraphEmailGateway, file_handler: FileHandler) -> None:
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

    @staticmethod
    def _show_menu(message: InternalMessage) -> str:
        session_manager.set_state(message.chat_id, "awaiting_option", message.platform)
        return _MENU_TEXT

    @staticmethod
    def _route_option(message: InternalMessage) -> str:
        choice = (message.text or "").strip()

        if choice in _OPTION_A:
            session_manager.set_state(message.chat_id, "awaiting_file_upload", message.platform)
            return "אנא שלח/י את המסמך או החשבונית."

        if choice in _OPTION_B:
            session_manager.set_state(message.chat_id, "awaiting_file_request", message.platform)
            return "איזה מסמך היית רוצה לקבל מהמשרד?"

        if choice in _OPTION_C:
            session_manager.set_state(
                message.chat_id, "awaiting_accountant_message", message.platform
            )
            return "אנא שלח/י את ההודעה שלך לרואה החשבון."

        return f"אנא ענה/י עם 1, 2, או 3.\n\n{_MENU_TEXT}"


    def _handle_upload(self, message: InternalMessage) -> str:
        if message.message_type not in (MessageType.DOCUMENT, MessageType.PHOTO):
            return "אנא שלח/י את הקובץ כמסמך או תמונה מצורפת."

        session_manager.set_state(
            message.chat_id, "awaiting_description_choice", message.platform,
            pending_file_path=message.file_path,
            pending_file_name=message.file_name or "לא ידוע",
        )
        return "האם תרצה/י להוסיף תיאור למסמך?\n\n  1 — כן\n  2 — לא"

    def _handle_description_choice(self, message: InternalMessage) -> str:
        answer = (message.text or "").strip().lower()

        if answer in _YES_KEYWORDS:
            session_manager.set_state(message.chat_id, "awaiting_description", message.platform)
            return "אנא כתוב/י את התיאור למסמך."

        if answer in _NO_KEYWORDS:
            return self._send_upload_email(message, description=None)

        return "אנא ענה/י 1 (כן) או 2 (לא)."

    def _handle_description(self, message: InternalMessage) -> str:
        return self._send_upload_email(message, description=message.text)

    def _send_upload_email(self, message: InternalMessage, description: str | None) -> str:
        session = session_manager.get_session(message.chat_id, message.platform)
        file_path = session.context.get("pending_file_path")
        file_name = session.context.get("pending_file_name", "לא ידוע")

        subject = f"[CPA Bot] העלאת מסמך — {message.chat_id}"
        body = f"לקוח/ה (מזהה צ'אט: {message.chat_id}) העלה/תה מסמך.\nשם קובץ: {file_name}"
        if description:
            body += f"\n\nתיאור: {description}"

        thread_id = self._email.send(
            subject=subject,
            body=body,
            attachment_path=file_path,
            chat_id=message.chat_id,
            platform=message.platform.value,
        )
        session_manager.set_state(
            message.chat_id, "awaiting_session_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
        )
        return "תודה! המסמך שלך התקבל והועבר למשרד.\n\n" + _SESSION_DECISION_TEXT


    def _handle_file_request(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] בקשת קובץ — {message.chat_id}"
        body = (
            f"לקוח/ה (מזהה צ'אט: {message.chat_id}) מבקש/ת קובץ.\n\n"
            f"בקשה: {message.text}"
        )
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id, platform=message.platform.value)
        session_manager.set_state(
            message.chat_id, "awaiting_session_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
        )
        return "בקשתך הועברה למשרד.\n\n" + _SESSION_DECISION_TEXT


    def _handle_accountant_message(self, message: InternalMessage) -> str:
        buffer = [message.text or ""]
        session_manager.set_state(
            message.chat_id, "collecting_accountant_messages", message.platform,
            message_buffer=buffer,
        )
        self._send_accountant_email(message.chat_id, message.platform.value, buffer)
        return (
            "ההודעה שלך נשלחה לרואה החשבון. ניתן לשלוח הודעות נוספות.\n"
            "שלח/י /close לסיום השיחה."
        )

    def _handle_collecting_accountant_messages(self, message: InternalMessage) -> str:
        session = session_manager.get_session(message.chat_id, message.platform)
        buffer: list = session.context.get("message_buffer", [])
        buffer.append(message.text or "")
        session_manager.set_state(
            message.chat_id, "collecting_accountant_messages", message.platform,
            message_buffer=buffer,
        )
        self._send_accountant_email(message.chat_id, message.platform.value, buffer)
        return "✓ נשלח."

    def _send_accountant_email(self, chat_id: str, platform_str: str, messages: list) -> None:
        full_text = "\n\n".join(messages)
        subject = f"[CPA Bot] הודעת לקוח — {chat_id}"
        body = f"לקוח/ה (מזהה צ'אט: {chat_id}) השאיר/ה הודעה:\n\n{full_text}"
        self._email.send(subject=subject, body=body, chat_id=chat_id, platform=platform_str)

    def handle_close(self, chat_id: str, platform) -> str:
        session_manager.clear_session(chat_id, platform)
        return "השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט."

    def _handle_session_decision(self, message: InternalMessage) -> str:
        text = (message.text or "").strip()

        if text in _CLOSE_KEYWORDS:
            session_manager.set_state(message.chat_id, "idle", message.platform)
            return "השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט :)"

        if text in _KEEP_KEYWORDS:
            return self._show_menu(message)

        return f"אנא ענה/י 1 (לסגירה) או 2 (להמשך).\n\n{_SESSION_DECISION_TEXT}"


