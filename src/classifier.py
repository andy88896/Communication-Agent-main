import json
import logging
import re
from dataclasses import dataclass

import anthropic

from src import config

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


_SYSTEM = """You are an email classification assistant. You will be given the subject, sender, and body of an email.

Your task is to:
1. Classify the email into exactly one of the following categories: "Career Opportunities", "AI News", "Cryptocurrency News", or "Unmatched".
2. If the category is "Career Opportunities", determine whether the email requires a reply from the recipient.
3. Return your response as a JSON object only. No explanation, no preamble.

Classification rules:
- "Career Opportunities": any email related to job searching, recruiting, interviews, hiring, assessments, offers, or rejections.
- "AI News": newsletters, articles, or updates about artificial intelligence, ML, LLMs, AI companies, or AI policy.
- "Cryptocurrency News": newsletters, price alerts, or updates about crypto, blockchain, DeFi, or Web3.
- "Unmatched": anything else.

If an email could fit multiple categories, apply this priority: Career Opportunities > AI News > Cryptocurrency News.

Reply-required logic (only applies to Career Opportunities):
- reply_required: true — if the email asks a question, invites scheduling, requests documents, or requires acknowledgement
- reply_required: false — if the email is automated, a rejection, or a one-way status update

Response format:
{
  "category": "Career Opportunities" | "AI News" | "Cryptocurrency News" | "Unmatched",
  "reply_required": true | false | null,
  "reply_required_reason": "brief reason string or null",
  "confidence": "high" | "medium" | "low"
}"""


@dataclass
class ClassificationResult:
    category: str
    reply_required: bool | None
    reply_required_reason: str | None
    confidence: str


def classify_email(subject: str, sender: str, body: str) -> ClassificationResult:
    prompt = f"Subject: {subject}\nFrom: {sender}\n\nBody:\n{body[:4000]}"

    try:
        response = _get_client().messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=256,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?```\s*$', '', raw)
        data = json.loads(raw)
        return ClassificationResult(
            category=data.get("category", "Unmatched"),
            reply_required=data.get("reply_required"),
            reply_required_reason=data.get("reply_required_reason"),
            confidence=data.get("confidence", "low"),
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in classify_email: {e} | raw: {raw!r}")
        return ClassificationResult(
            category="Unmatched",
            reply_required=None,
            reply_required_reason=None,
            confidence="low",
        )
    except Exception as e:
        logger.error(f"Claude API error in classify_email: {e}")
        return ClassificationResult(
            category="Unmatched",
            reply_required=None,
            reply_required_reason=None,
            confidence="low",
        )
