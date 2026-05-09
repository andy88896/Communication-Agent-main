import os
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = [
    "GMAIL_CREDENTIALS_PRIMARY",
    "GMAIL_CREDENTIALS_SECONDARY",
    "GMAIL_TOKEN_PRIMARY",
    "GMAIL_TOKEN_SECONDARY",
    "NOTION_API_KEY",
    "NOTION_PAGE_ID",
]

def validate():
    missing = [k for k in _REQUIRED if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            "Missing required environment variables:\n"
            + "\n".join(f"  - {k}" for k in missing)
            + "\n\nCopy .env.example to .env and fill in all values."
        )

GMAIL_CREDENTIALS_PRIMARY    = lambda: os.environ["GMAIL_CREDENTIALS_PRIMARY"]
GMAIL_CREDENTIALS_SECONDARY  = lambda: os.environ["GMAIL_CREDENTIALS_SECONDARY"]
GMAIL_TOKEN_PRIMARY          = lambda: os.environ["GMAIL_TOKEN_PRIMARY"]
GMAIL_TOKEN_SECONDARY        = lambda: os.environ["GMAIL_TOKEN_SECONDARY"]
NOTION_API_KEY               = lambda: os.environ["NOTION_API_KEY"]
NOTION_PAGE_ID               = lambda: os.environ["NOTION_PAGE_ID"]

PRIMARY_EMAIL   = "andrewch810@gmail.com"
SECONDARY_EMAIL = "andrewcn196@gmail.com"

INBOX_EMAILS = {
    "primary":   PRIMARY_EMAIL,
    "secondary": SECONDARY_EMAIL,
}


CLAUDE_MODEL = "claude-sonnet-4-6"
