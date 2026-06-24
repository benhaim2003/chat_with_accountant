from __future__ import annotations
import logging
from src.models.internal_message import InternalMessage, MessageType
from src.models.menu_response import MenuResponse, MenuButton
from src.core import session_manager
from src.services.email_gateway import GraphEmailGateway
from src.services.file_handler import FileHandler

logger = logging.getLogger(__name__)

_MENU_TEXT = (
    "תודה שפנית למוקד של רבינוביץ אבן ממן :)\n\n"
    "איך נוכל לעזור לך?"
)

_SESSION_DECISION_TEXT = "האם לסגור את השיחה?"

_TAP_BUTTON_REMINDER = "תודה שפנית למוקד של רבינוביץ אבן ממן :)\nכיצד נוכל לעזור?"

_MENU_BUTTONS = (
    MenuButton(label="שליחת מסמך", payload="1"),
    MenuButton(label="בקשת מסמך",  payload="2"),
    MenuButton(label="השארת הודעה", payload="3"),
)

_YES_NO_BUTTONS = (
    MenuButton(label="כן", payload="1"),
    MenuButton(label="לא", payload="2"),
)

_CLOSE_CONTINUE_BUTTONS = (
    MenuButton(label="סיים שיחה", payload="1"),
    MenuButton(label="המשך",      payload="2"),
)

_FOLLOWUP_BUTTONS_BY_KIND = {
    "upload":  (
        MenuButton(label="שלח/י עוד מסמך",  payload="1"),
        MenuButton(label="תפריט ראשי",      payload="2"),
        MenuButton(label="סיים שיחה",       payload="3"),
    ),
    "request": (
        MenuButton(label="בקש/י מסמך נוסף", payload="1"),
        MenuButton(label="תפריט ראשי",      payload="2"),
        MenuButton(label="סיים שיחה",       payload="3"),
    ),
    "message": (
        MenuButton(label="שלח/י הודעה נוספת", payload="1"),
        MenuButton(label="תפריט ראשי",        payload="2"),
        MenuButton(label="סיים שיחה",         payload="3"),
    ),
}

_FOLLOWUP_PROMPT = "מה תרצה/י לעשות עכשיו?"

_CLOSE_PAYLOAD = "1"
_KEEP_PAYLOAD  = "2"

_OPTION_A_PAYLOAD = "1"
_OPTION_B_PAYLOAD = "2"
_OPTION_C_PAYLOAD = "3"

_YES_PAYLOAD = "1"
_NO_PAYLOAD  = "2"

_FOLLOWUP_AGAIN_PAYLOAD = "1"
_FOLLOWUP_MENU_PAYLOAD  = "2"
_FOLLOWUP_CLOSE_PAYLOAD = "3"

_STATE_HANDLERS = {
    "awaiting_option":                   "_route_option",
    "awaiting_file_upload":              "_handle_upload",
    "awaiting_description_choice":       "_handle_description_choice",
    "awaiting_description":              "_handle_description",
    "awaiting_file_request":             "_handle_file_request",
    "awaiting_accountant_message":       "_handle_accountant_message",
    "awaiting_session_decision":         "_handle_session_decision",
    "awaiting_followup_decision":        "_handle_followup_decision",
}


class MenuHandler:
    def __init__(self, email_gateway: GraphEmailGateway, file_handler: FileHandler) -> None:
        self._email = email_gateway
        self._files = file_handler

    def handle(self, message: InternalMessage) -> MenuResponse:
        session = session_manager.get_session(message.chat_id, message.platform)

        if session.state == "idle" or message.text in ("/start", "/menu"):
            return self._show_menu(message)

        handler_name = _STATE_HANDLERS.get(session.state)
        if handler_name:
            return getattr(self, handler_name)(message)

        logger.warning("Unknown state '%s' for %s — resetting", session.state, message.chat_id)
        return self._show_menu(message)

    @staticmethod
    def _show_menu(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, "awaiting_option", message.platform)
        return MenuResponse(text=_MENU_TEXT, buttons=_MENU_BUTTONS)

    def _route_option(self, message: InternalMessage) -> MenuResponse:
        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=_MENU_BUTTONS)

        choice = (message.text or "").strip()

        if choice == _OPTION_A_PAYLOAD:
            return self._start_flow_upload(message)
        if choice == _OPTION_B_PAYLOAD:
            return self._start_flow_request(message)
        if choice == _OPTION_C_PAYLOAD:
            return self._start_flow_message(message)

        return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=_MENU_BUTTONS)

    @staticmethod
    def _start_flow_upload(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, "awaiting_file_upload", message.platform)
        return MenuResponse(text="אנא שלח/י את המסמך או החשבונית.")

    @staticmethod
    def _start_flow_request(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, "awaiting_file_request", message.platform)
        return MenuResponse(text="איזה מסמך היית רוצה לקבל מהמשרד?")

    @staticmethod
    def _start_flow_message(message: InternalMessage) -> MenuResponse:
        session_manager.set_state(message.chat_id, "awaiting_accountant_message", message.platform)
        return MenuResponse(text="אנא שלח/י את ההודעה שלך לרואה החשבון.")


    def _handle_upload(self, message: InternalMessage) -> MenuResponse:
        if message.message_type not in (MessageType.DOCUMENT, MessageType.PHOTO):
            return MenuResponse(text="אנא שלח/י את הקובץ כמסמך או תמונה מצורפת.")

        session_manager.set_state(
            message.chat_id, "awaiting_description_choice", message.platform,
            pending_file_path=message.file_path,
            pending_file_name=message.file_name or "לא ידוע",
        )
        return MenuResponse(
            text="האם תרצה/י להוסיף תיאור למסמך?",
            buttons=_YES_NO_BUTTONS,
        )

    def _handle_description_choice(self, message: InternalMessage) -> MenuResponse:
        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=_YES_NO_BUTTONS)

        answer = (message.text or "").strip()

        if answer == _YES_PAYLOAD:
            session_manager.set_state(message.chat_id, "awaiting_description", message.platform)
            return MenuResponse(text="אנא כתוב/י את התיאור למסמך.")

        if answer == _NO_PAYLOAD:
            return self._send_upload_email(message, description=None)

        return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=_YES_NO_BUTTONS)

    def _handle_description(self, message: InternalMessage) -> MenuResponse:
        return self._send_upload_email(message, description=message.text)

    def _send_upload_email(self, message: InternalMessage, description: str | None) -> MenuResponse:
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
            message.chat_id, "awaiting_followup_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            flow_kind="upload",
        )
        return MenuResponse(
            text="תודה! המסמך שלך התקבל והועבר למשרד.\n\n" + _FOLLOWUP_PROMPT,
            buttons=_FOLLOWUP_BUTTONS_BY_KIND["upload"],
        )


    def _handle_file_request(self, message: InternalMessage) -> MenuResponse:
        subject = f"[CPA Bot] בקשת קובץ — {message.chat_id}"
        body = (
            f"לקוח/ה (מזהה צ'אט: {message.chat_id}) מבקש/ת קובץ.\n\n"
            f"בקשה: {message.text}"
        )
        thread_id = self._email.send(subject=subject, body=body, chat_id=message.chat_id, platform=message.platform.value)
        session_manager.set_state(
            message.chat_id, "awaiting_followup_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            flow_kind="request",
        )
        return MenuResponse(
            text="בקשתך הועברה למשרד.\n\n" + _FOLLOWUP_PROMPT,
            buttons=_FOLLOWUP_BUTTONS_BY_KIND["request"],
        )


    def _handle_accountant_message(self, message: InternalMessage) -> MenuResponse:
        subject = f"[CPA Bot] הודעת לקוח — {message.chat_id}"
        body = f"לקוח/ה (מזהה צ'אט: {message.chat_id}) השאיר/ה הודעה:\n\n{message.text or ''}"
        thread_id = self._email.send(
            subject=subject,
            body=body,
            chat_id=message.chat_id,
            platform=message.platform.value,
        )
        session_manager.set_state(
            message.chat_id, "awaiting_followup_decision", message.platform,
            active_thread_id=thread_id,
            follow_up_subject=subject,
            flow_kind="message",
        )
        return MenuResponse(
            text="ההודעה שלך נשלחה לרואה החשבון.\n\n" + _FOLLOWUP_PROMPT,
            buttons=_FOLLOWUP_BUTTONS_BY_KIND["message"],
        )

    def handle_close(self, chat_id: str, platform) -> MenuResponse:
        session_manager.clear_session(chat_id, platform)
        return MenuResponse(
            text="השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט."
        )

    def _handle_session_decision(self, message: InternalMessage) -> MenuResponse:
        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=_CLOSE_CONTINUE_BUTTONS)

        text = (message.text or "").strip()

        if text == _CLOSE_PAYLOAD:
            session_manager.set_state(message.chat_id, "idle", message.platform)
            return MenuResponse(
                text="השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט :)"
            )

        if text == _KEEP_PAYLOAD:
            return self._show_menu(message)

        return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=_CLOSE_CONTINUE_BUTTONS)

    def _handle_followup_decision(self, message: InternalMessage) -> MenuResponse:
        session = session_manager.get_session(message.chat_id, message.platform)
        flow_kind = session.context.get("flow_kind", "upload")
        buttons = _FOLLOWUP_BUTTONS_BY_KIND.get(flow_kind, _FOLLOWUP_BUTTONS_BY_KIND["upload"])

        if message.message_type != MessageType.BUTTON:
            return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=buttons)

        choice = (message.text or "").strip()

        if choice == _FOLLOWUP_AGAIN_PAYLOAD:
            if flow_kind == "upload":
                return self._start_flow_upload(message)
            if flow_kind == "request":
                return self._start_flow_request(message)
            if flow_kind == "message":
                return self._start_flow_message(message)
            return self._show_menu(message)

        if choice == _FOLLOWUP_MENU_PAYLOAD:
            return self._show_menu(message)

        if choice == _FOLLOWUP_CLOSE_PAYLOAD:
            session_manager.set_state(message.chat_id, "idle", message.platform)
            return MenuResponse(
                text="השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט :)"
            )

        return MenuResponse(text=_TAP_BUTTON_REMINDER, buttons=buttons)
