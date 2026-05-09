import base64
import json
import logging
import re as _re
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class AuthError(Exception):
    pass


def _build_credentials(inbox: str) -> Credentials:
    if inbox == "primary":
        token_json = config.GMAIL_TOKEN_PRIMARY()
        creds_json = config.GMAIL_CREDENTIALS_PRIMARY()
    else:
        token_json = config.GMAIL_TOKEN_SECONDARY()
        creds_json = config.GMAIL_CREDENTIALS_SECONDARY()

    token_data = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            raise AuthError(
                f"OAuth token for '{inbox}' inbox has expired and could not be refreshed.\n"
                f"Run `python setup_oauth.py` to re-authenticate.\nDetail: {e}"
            )
    elif not creds.valid:
        raise AuthError(
            f"OAuth token for '{inbox}' inbox is invalid.\n"
            f"Run `python setup_oauth.py` to re-authenticate."
        )

    return creds


def _decode_body(payload: dict) -> str:
    """Extract plain-text body from a Gmail message payload."""
    def _extract(p, target_mime):
        if p.get("mimeType", "") == target_mime:
            data = p.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in p.get("parts", []):
            result = _extract(part, target_mime)
            if result:
                return result
        return ""

    text = _extract(payload, "text/plain")
    if text:
        return text

    html = _extract(payload, "text/html")
    if html:
        text = _re.sub(r"<[^>]+>", " ", html)
        return _re.sub(r"\s+", " ", text).strip()

    return ""


def _header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


class GmailClient:
    def __init__(self, inbox: str):
        if inbox not in ("primary", "secondary"):
            raise ValueError(f"inbox must be 'primary' or 'secondary', got '{inbox}'")
        self.inbox = inbox
        self.email = config.INBOX_EMAILS[inbox]
        creds = _build_credentials(inbox)
        self._service = build("gmail", "v1", credentials=creds)

    def get_emails(self, after_date: date) -> list[dict]:
        query = f"after:{after_date.strftime('%Y/%m/%d')}"
        results = []
        page_token = None

        while True:
            kwargs = {"userId": "me", "q": query, "maxResults": 500}
            if page_token:
                kwargs["pageToken"] = page_token
            response = self._service.users().messages().list(**kwargs).execute()
            messages = response.get("messages", [])

            for msg_ref in messages:
                try:
                    msg = self._service.users().messages().get(
                        userId="me", id=msg_ref["id"], format="full"
                    ).execute()
                    headers = msg.get("payload", {}).get("headers", [])
                    body = _decode_body(msg.get("payload", {}))
                    results.append({
                        "id":        msg["id"],
                        "thread_id": msg.get("threadId", ""),
                        "subject":   _header(headers, "Subject") or "(no subject)",
                        "sender":    _header(headers, "From"),
                        "date":      _header(headers, "Date"),
                        "body":      body,
                    })
                except Exception as e:
                    logger.warning(f"Could not fetch email {msg_ref['id']}: {e}")

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def ensure_label(self, name: str) -> str:
        labels_resp = self._service.users().labels().list(userId="me").execute()
        for lbl in labels_resp.get("labels", []):
            if lbl["name"] == name:
                return lbl["id"]

        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }

        created = self._service.users().labels().create(userId="me", body=body).execute()
        logger.info(f"Created label '{name}' in {self.inbox} inbox")
        return created["id"]

    def apply_label(self, message_id: str, label_id: str) -> None:
        self._service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()

    def create_draft(self, to: str, subject: str, body: str, thread_id: str) -> str:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body: dict = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id

        draft = self._service.users().drafts().create(
            userId="me", body=draft_body
        ).execute()
        return draft["id"]

    def send_message(self, to: str, subject: str, body: str) -> None:
        message = MIMEText(body)
        message["to"] = to
        message["from"] = self.email
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        self._service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
