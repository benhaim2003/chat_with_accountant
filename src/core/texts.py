from __future__ import annotations

from src.models.menu_response import MenuButton

GREETING = (
    "תודה שפנית למוקד של רבינוביץ אבן ממן :)\n\n"
    "איך נוכל לעזור לך?"
)

TAP_BUTTON_REMINDER = "תודה שפנית למוקד של רבינוביץ אבן ממן :)\nכיצד נוכל לעזור?"

CONVERSATION_CLOSED = (
    "השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט."
)
CONVERSATION_CLOSED_SMILEY = CONVERSATION_CLOSED[:-1] + " :)"

OPTION_UPLOAD = "1"
OPTION_REQUEST = "2"
OPTION_MESSAGE = "3"

MAIN_MENU_BUTTONS = (
    MenuButton(label="📥 בקשת מסמך", payload=OPTION_REQUEST),
    MenuButton(label="📤 שליחת מסמך", payload=OPTION_UPLOAD),
    MenuButton(label="💬 השארת הודעה", payload=OPTION_MESSAGE),
)

UPLOAD_PROMPT = "אנא שלח/י את המסמך או החשבונית."
UPLOAD_NOT_A_FILE = "אנא שלח/י את הקובץ כמסמך או תמונה מצורפת."
UPLOAD_ASK_DESCRIPTION = "האם תרצה/י להוסיף תיאור למסמך?"
UPLOAD_DESCRIPTION_PROMPT = "אנא כתוב/י את התיאור למסמך."
UPLOAD_DONE = "תודה! המסמך שלך התקבל והועבר למשרד."

YES = "1"
NO = "2"

YES_NO_BUTTONS = (
    MenuButton(label="כן", payload=YES),
    MenuButton(label="לא", payload=NO),
)

REQUEST_TYPE_PROMPT = "איזה מסמך תרצה/י לקבל מהמשרד?"
REQUEST_FREE_TEXT_PROMPT = "איזה מסמך היית רוצה לקבל מהמשרד?"
REQUEST_DONE = "בקשתך הועברה למשרד."

REQUEST_OTHER = "6"

REQUEST_TYPES = {
    "1": "אישור ניכוי מס במקור וניהול ספרים",
    "2": "דיווחים תקופתיים למע\"מ",
    "3": "תלוש שכר",
    "4": "אישור קיזוז מע\"מ על רכב",
    "5": "שומת מס",
}

REQUEST_TYPE_BUTTONS = (
    MenuButton(label="אישור ניכוי מס במקור", payload="1"),
    MenuButton(label="דוח מע\"מ תקופתי", payload="2"),
    MenuButton(label="תלוש שכר", payload="3"),
    MenuButton(label="ניכוי מע\"מ על רכבים", payload="4"),
    MenuButton(label="שומת מס", payload="5"),
    MenuButton(label="אחר", payload=REQUEST_OTHER),
)

REQUEST_DETAIL_PROMPTS = {
    "2": "לאיזו שנה תרצה/י את הדיווחים התקופתיים?",
    "3": "אנא כתוב/י את שם העובד/ת ואת התקופה המבוקשת.",
    "4": "אנא כתוב/י את חברת הרכב ואת מספר הרישוי שלו.",
}

MESSAGE_PROMPT = "אנא שלח/י את ההודעה שלך לרואה החשבון."
MESSAGE_DONE = "ההודעה שלך נשלחה לרואה החשבון."

FOLLOWUP_PROMPT = "מה תרצה/י לעשות עכשיו?"

FOLLOWUP_AGAIN = "1"
FOLLOWUP_MENU = "2"
FOLLOWUP_CLOSE = "3"

_FOLLOWUP_COMMON = (
    MenuButton(label="תפריט ראשי", payload=FOLLOWUP_MENU),
    MenuButton(label="סיים שיחה", payload=FOLLOWUP_CLOSE),
)

FOLLOWUP_BUTTONS = {
    "upload": (MenuButton(label="שלח/י עוד מסמך", payload=FOLLOWUP_AGAIN), *_FOLLOWUP_COMMON),
    "request": (MenuButton(label="בקש/י מסמך נוסף", payload=FOLLOWUP_AGAIN), *_FOLLOWUP_COMMON),
    "message": (MenuButton(label="שלח/י הודעה נוספת", payload=FOLLOWUP_AGAIN), *_FOLLOWUP_COMMON),
}

SECRETARY_REPLY_PREFIX = "הודעה ממשרד רואה החשבון שלך:"


def upload_email(client: str, file_name: str, description: str | None) -> tuple[str, str]:
    subject = f"[CPA Bot] {client} · העלאת מסמך"
    body = f"{client} העלה/תה מסמך.\nשם קובץ: {file_name}"
    if description:
        body += f"\n\nתיאור: {description}"
    return subject, body


def request_email(client: str, subject_detail: str, request_text: str) -> tuple[str, str]:
    subject = f"[CPA Bot] {client} · {subject_detail}"
    body = f"{client} מבקש/ת מסמך.\n\nבקשה: {request_text}"
    return subject, body


def accountant_message_email(client: str, text: str) -> tuple[str, str]:
    subject = f"[CPA Bot] {client} · הודעה לרו״ח"
    body = f"{client} השאיר/ה הודעה:\n\n{text}"
    return subject, body


def attachments_failed(failed: int, total: int) -> str:
    return f"⚠️ {failed} מתוך {total} קבצים לא הצליחו להישלח. המשרד יצור קשר."
