import logging
import time

from notion_client import Client

from src import config

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(auth=config.NOTION_API_KEY())
    return _client


def append_action_item(
    subject: str,
    sender_name: str,
    sender_email: str,
    received_date: str,
    inbox_email: str,
    summary: str,
) -> None:
    page_id = config.NOTION_PAGE_ID()
    client = _get_client()

    heading = f"☐ Review & send draft reply — {subject}"
    detail = (
        f"Inbox: {inbox_email} | "
        f"From: {sender_name} <{sender_email}> | "
        f"Received: {received_date}\n"
        f"{summary}"
    )

    blocks = [
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": heading}}],
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": detail}}]
                        },
                    }
                ],
            },
        }
    ]

    try:
        client.blocks.children.append(block_id=page_id, children=blocks)
        time.sleep(0.35)
    except Exception as e:
        logger.error(f"Notion write failed for '{subject}': {e}")
