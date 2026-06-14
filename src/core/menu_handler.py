from __future__ import annotations
import logging
from src.models.internal_message import InternalMessage, MessageType
from src.core import session_manager
from src.services.email_gateway import GraphEmailGateway
from src.services.file_handler import FileHandler

logger = logging.getLogger(__name__)

_MENU_TEXT = (
    "ברוכים הבאים לבוט של משרד רואה החשבון.\n\n"
    "אנא בחר/י אפשרות:\n"
    "  א — העלאת חשבונית או שטר עלויות\n"
    "  ב — בקשת קובץ מהמשרד\n"
    "  ג — השארת הודעה לרואה החשבון\n"
    "  ד — אחר"
)

_SESSION_DECISION_TEXT = (
    "האם תרצה/י לסגור את השיחה?\n\n"
    "  1 — כן, סגור את הסשן\n"
    "  2 — לא, אני רוצה להמשיך לשלוח הודעות"
)

_CLOSE_KEYWORDS = {"1", "כן", "סגור", "סיים", "סגירה", "יציאה"}
_KEEP_KEYWORDS  = {"2", "לא", "פתוח", "המשך", "עוד"}

_OPTION_A = {"א", "A"}
_OPTION_B = {"ב", "B"}
_OPTION_C = {"ג", "C"}
_OPTION_D = {"ד", "D"}

_STATE_HANDLERS = {
    "awaiting_option":             "_route_option",
    "awaiting_file_upload":        "_handle_upload",
    "awaiting_file_request":       "_handle_file_request",
    "awaiting_accountant_message": "_handle_accountant_message",
    "awaiting_other":              "_handle_other",
    "awaiting_session_decision":   "_handle_session_decision",
    "session_open":                "_handle_session_open",
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

    # ------------------------------------------------------------------ menu

    def _show_menu(self, message: InternalMessage) -> str:
        session_manager.set_state(message.chat_id, "awaiting_option", message.platform)
        return _MENU_TEXT

    # ---------------------------------------------------------- option router

    def _route_option(self, message: InternalMessage) -> str:
        choice = (message.text or "").strip().upper()

        if choice in _OPTION_A:
            session_manager.set_state(message.chat_id, "awaiting_file_upload", message.platform)
            return "אנא העלה/י את החשבונית או שטר העלויות כקובץ PDF."

        if choice in _OPTION_B:
            session_manager.set_state(message.chat_id, "awaiting_file_request", message.platform)
            return "אנא תאר/י איזה קובץ אתה/את צריך/ה מהמשרד."

        if choice in _OPTION_C:
            session_manager.set_state(
                message.chat_id, "awaiting_accountant_message", message.platform
            )
            return "אנא הקלד/י את ההודעה שלך לרואה החשבון."

        if choice in _OPTION_D:
            session_manager.set_state(message.chat_id, "awaiting_other", message.platform)
            return "אנא הקלד/י את הודעתך ונחזור אליך בהקדם."

        return f"אנא ענה/י עם א, ב, ג, או ד.\n\n{_MENU_TEXT}"

    # ---------------------------------------------------- option א: upload
    # Logical end = client finishes uploading → ask close/keep immediately.

    def _handle_upload(self, message: InternalMessage) -> str:
        if message.message_type not in (MessageType.DOCUMENT, MessageType.PHOTO):
            return "אנא שלח/י את הקובץ כמסמך או תמונה מצורפת."

        subject = f"[CPA Bot] העלאת מסמך — צ'אט {message.chat_id}"
        body = (
            f"לקוח/ה (מזהה צ'אט: {message.chat_id}) העלה/תה מסמך.\n"
            f"שם קובץ: {message.file_name or 'לא ידוע'}"
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
            "תודה! המסמך שלך התקבל והועבר למשרד.\n\n"
            + _SESSION_DECISION_TEXT
        )

    # ------------------------------------------------- option ב: file request
    # Logical end = secretary sends back the file → close/keep triggered from
    # the email reply callback in main.py, NOT here.

    def _handle_file_request(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] בקשת קובץ — צ'אט {message.chat_id}"
        body = (
            f"לקוח/ה (מזהה צ'אט: {message.chat_id}) מבקש/ת קובץ.\n\n"
            f"בקשה: {message.text}"
        )
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id)
        session_manager.set_state(
            message.chat_id, "session_open", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            session_type="file_request",
        )
        return "בקשתך הועברה למשרד. ניתן לשלוח הודעות נוספות בכל עת."

    # ------------------------------------------ option ג: accountant message
    # Logical end = secretary sends a response → close/keep triggered from
    # the email reply callback in main.py, NOT here.

    def _handle_accountant_message(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] הודעת לקוח — צ'אט {message.chat_id}"
        body = (
            f"לקוח/ה (מזהה צ'אט: {message.chat_id}) השאיר/ה הודעה:\n\n"
            f"{message.text}"
        )
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id)
        session_manager.set_state(
            message.chat_id, "session_open", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            session_type="accountant_message",
        )
        return "הודעתך הועברה לרואה החשבון שלך. ניתן לשלוח הודעות נוספות בכל עת."

    # ---------------------------------------------------- option ד: other

    def _handle_other(self, message: InternalMessage) -> str:
        subject = f"[CPA Bot] פנייה כללית — צ'אט {message.chat_id}"
        body = (
            f"לקוח/ה (מזהה צ'אט: {message.chat_id}) שלח/ה פנייה כללית:\n\n"
            f"{message.text}"
        )
        # Phase 3 hook: replace email send with LLM processing here
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id)
        session_manager.set_state(
            message.chat_id, "session_open", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            session_type="other",
        )
        return "תודה! הודעתך התקבלה. ניתן לשלוח הודעות נוספות בכל עת."

    # ------------------------------------------- session close/keep decision
    # Triggered after secretary sends a reply (via email callback in main.py)
    # or after option א completes.
    # Only 1/2 (or matching keywords) are accepted; anything else re-asks.

    def _handle_session_decision(self, message: InternalMessage) -> str:
        text = (message.text or "").strip()

        if text in _CLOSE_KEYWORDS:
            session_manager.set_state(message.chat_id, "idle", message.platform)
            return "הסשן נסגר. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט."

        if text in _KEEP_KEYWORDS:
            session_manager.set_state(message.chat_id, "session_open", message.platform)
            return "מצוין! שלח/י את ההודעה הבאה שלך והיא תועבר למשרד."

        return f"אנא ענה/י 1 (לסגירה) או 2 (להמשך).\n\n{_SESSION_DECISION_TEXT}"

    # ----------------------------------------- open session: free-form relay

    def _handle_session_open(self, message: InternalMessage) -> str:
        session = session_manager.get_session(message.chat_id, message.platform)
        subject = session.context.get(
            "follow_up_subject", f"[CPA Bot] המשך שיחה — צ'אט {message.chat_id}"
        )

        if message.message_type in (MessageType.DOCUMENT, MessageType.PHOTO):
            body = (
                f"המשך מלקוח/ה (מזהה צ'אט: {message.chat_id}) — מסמך.\n"
                f"שם קובץ: {message.file_name or 'לא ידוע'}"
            )
            self._email.send(
                subject=subject,
                body=body,
                attachment_path=message.file_path,
                chat_id=message.chat_id,
            )
        else:
            body = f"המשך מלקוח/ה (מזהה צ'אט: {message.chat_id}):\n\n{message.text}"
            self._email.send(subject=subject, body=body, chat_id=message.chat_id)

        # Stay open — close/keep will be triggered when the secretary replies
        session_manager.set_state(message.chat_id, "session_open", message.platform)
        return "✓ נשלח"
