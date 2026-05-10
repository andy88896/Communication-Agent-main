import json
import pytest
from unittest.mock import MagicMock, patch
from src.classifier import classify_email


def _make_api_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.content[0].text = json.dumps(data)
    return response


@pytest.fixture
def mock_anthropic(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("src.classifier.anthropic_client", mock)
    return mock


def test_valid_ai_news_classification(mock_anthropic):
    mock_anthropic.get.return_value.messages.create.return_value = _make_api_response({
        "category": "AI News",
        "reply_required": None,
        "reply_required_reason": None,
        "confidence": "high",
    })
    result = classify_email("AI Weekly", "news@example.com", "Body text")
    assert result.category == "AI News"
    assert result.confidence == "high"
    assert result.reply_required is None


def test_career_opportunity_with_reply_required(mock_anthropic):
    mock_anthropic.get.return_value.messages.create.return_value = _make_api_response({
        "category": "Career Opportunities",
        "reply_required": True,
        "reply_required_reason": "Invited to schedule an interview",
        "confidence": "high",
    })
    result = classify_email("Interview invite", "recruiter@example.com", "Body")
    assert result.category == "Career Opportunities"
    assert result.reply_required is True
    assert result.reply_required_reason == "Invited to schedule an interview"


def test_career_opportunity_no_reply_required(mock_anthropic):
    mock_anthropic.get.return_value.messages.create.return_value = _make_api_response({
        "category": "Career Opportunities",
        "reply_required": False,
        "reply_required_reason": "Automated rejection",
        "confidence": "high",
    })
    result = classify_email("Application update", "noreply@company.com", "Body")
    assert result.reply_required is False


def test_json_parse_error_falls_back_to_unmatched(mock_anthropic):
    response = MagicMock()
    response.content[0].text = "not valid json {{ at all"
    mock_anthropic.get.return_value.messages.create.return_value = response
    result = classify_email("Subject", "sender@x.com", "Body")
    assert result.category == "Unmatched"
    assert result.confidence == "low"
    assert result.reply_required is None


def test_api_exception_falls_back_to_unmatched(mock_anthropic):
    mock_anthropic.get.return_value.messages.create.side_effect = Exception("Connection error")
    result = classify_email("Subject", "sender@x.com", "Body")
    assert result.category == "Unmatched"
    assert result.confidence == "low"
    assert result.reply_required is None


def test_response_wrapped_in_code_block_is_parsed(mock_anthropic):
    response = MagicMock()
    response.content[0].text = (
        "```json\n"
        + json.dumps({"category": "Business News", "reply_required": None,
                      "reply_required_reason": None, "confidence": "medium"})
        + "\n```"
    )
    mock_anthropic.get.return_value.messages.create.return_value = response
    result = classify_email("Markets", "news@x.com", "Body")
    assert result.category == "Business News"
    assert result.confidence == "medium"