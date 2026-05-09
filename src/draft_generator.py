import logging

import anthropic

from src import config

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


_SYSTEM = """You are a professional email assistant helping to draft replies on behalf of a job applicant. Your writing style is warm and professional — friendly but polished.

You will be given the content of an email received by the user. Draft a reply that:
- Acknowledges the email's content directly
- Responds appropriately to any questions or invitations
- Expresses genuine interest where relevant
- Is concise (3–6 sentences for standard replies)
- Uses [placeholders] in square brackets for anything the user needs to fill in (dates, specific details, etc.)
- Does not invent facts about the user's background or experience

Do not include a subject line in your response. Return the email body only."""


def generate_draft(original_subject: str, sender: str, body: str) -> str:
    prompt = (
        f"Original email from {sender}:\n"
        f"Subject: {original_subject}\n\n"
        f"{body[:4000]}"
    )

    try:
        response = _get_client().messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude API error in generate_draft: {e}")
        return (
            "Thank you for reaching out. I appreciate your message and will follow up shortly.\n\n"
            "[Please review and personalise this draft before sending.]\n\nBest regards,\n[Your name]"
        )
