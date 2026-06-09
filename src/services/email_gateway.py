from __future__ import annotations
import email as email_lib
import imaplib
import logging
import re
import smtplib
import threading
import time
import uuid
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Signature: (chat_id, reply_text, attachment_paths, close_requested) -> None
ReplyCallback = Callable[[str, str, list[str], bool], None]


class EmailGateway:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        imap_host: str,
        imap_port: int,
        username: str,
        password: str,
        secretariat_address: str,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._username = username
        self._password = password
        self._secretariat = secretariat_address
        # message-id → chat_id, used to match secretary replies back to clients
        self._thread_map: dict[str, str] = {}
        self._reply_callback: Optional[ReplyCallback] = None
        self._polling = False

    def set_reply_callback(self, callback: ReplyCallback) -> None:
        self._reply_callback = callback

    def send(
        self,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> Optional[str]:
        message_id = f"<{uuid.uuid4()}@cpa-bot>"
        msg = MIMEMultipart()
        msg["From"] = self._username
        msg["To"] = self._secretariat
        msg["Subject"] = subject
        msg["Message-ID"] = message_id
        if chat_id:
            msg["X-CPA-Chat-ID"] = chat_id
        msg.attach(MIMEText(body, "plain"))

        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=Path(attachment_path).name)
            part["Content-Disposition"] = f'attachment; filename="{Path(attachment_path).name}"'
            msg.attach(part)

        try:
            self._smtp_send(msg.as_string())
            if chat_id:
                self._thread_map[message_id] = chat_id
            logger.info("Email sent: %s", subject)
            return message_id
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            return None

    def _smtp_send(self, raw: str) -> None:
        # Port 465 = implicit SSL (Yahoo, some others).
        # Any other port = explicit STARTTLS (Gmail 587, Yahoo 587, etc.).
        if self._smtp_port == 465:
            with smtplib.SMTP_SSL(self._smtp_host, self._smtp_port) as server:
                server.login(self._username, self._password)
                server.sendmail(self._username, self._secretariat, raw)
        else:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self._username, self._password)
                server.sendmail(self._username, self._secretariat, raw)

    # ---------------------------------------------------------------- polling

    def start_polling(self, interval_seconds: int = 30) -> None:
        self._polling = True
        t = threading.Thread(
            target=self._poll_loop, args=(interval_seconds,), daemon=True, name="email-poller"
        )
        t.start()
        logger.info("Email poller started (every %ds)", interval_seconds)

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
        with imaplib.IMAP4_SSL(self._imap_host, self._imap_port) as imap:
            imap.login(self._username, self._password)
            imap.select("INBOX")
            _, data = imap.search(None, "UNSEEN")
            uids = data[0].split()
            if uids:
                logger.debug("Checking %d unseen email(s)", len(uids))
            for uid in uids:
                _, msg_data = imap.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                self._process_reply(msg)
                imap.store(uid, "+FLAGS", "\\Seen")

    def _process_reply(self, msg) -> None:
        if not self._reply_callback:
            return

        # Only process genuine replies — emails that reference a bot-originated thread.
        # This prevents the bot from treating its own outgoing emails as replies,
        # which would happen when sender == secretariat address (e.g. during testing).
        in_reply_to = msg.get("In-Reply-To", "").strip()
        if not in_reply_to:
            logger.debug("Skipping email: no In-Reply-To header")
            return

        chat_id = self._thread_map.get(in_reply_to)
        if not chat_id:
            logger.debug("Skipping email: In-Reply-To not in thread map")
            return

        body, close_requested = self._extract_body_and_marker(msg)
        self._reply_callback(chat_id, body, [], close_requested)

    def _extract_body_and_marker(self, msg) -> tuple[str, bool]:
        raw = self._get_raw_text(msg)
        clean = self._strip_quoted_text(raw)
        close_requested = "#סגור" in clean
        if close_requested:
            clean = re.sub(r"#סגור", "", clean).strip()
        return clean, close_requested

    @staticmethod
    def _get_raw_text(msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    return payload.decode(errors="replace") if payload else ""
        payload = msg.get_payload(decode=True)
        return payload.decode(errors="replace") if payload else ""

    @staticmethod
    def _strip_quoted_text(body: str) -> str:
        # Pattern 1 — Gmail / Yahoo / Apple Mail: "On <date>, <name> wrote:" (single or multi-line)
        match = re.search(r"\nOn\s.{5,300}wrote:\s*\n", body, re.DOTALL)
        if match:
            return body[: match.start()].strip()
        # Pattern 2 — Outlook: "From: ... Sent: ... To: ... Subject: ..."
        match = re.search(r"\n[-_]{3,}\s*\n.*?From:.*?Sent:", body, re.DOTALL)
        if match:
            return body[: match.start()].strip()
        # Pattern 3 — standard > quote markers
        lines = [line for line in body.splitlines() if not line.startswith(">")]
        return "\n".join(lines).strip()
