import argparse
import pytest
from datetime import date, timedelta

from agent import _parse_sender, resolve_after_date


# ── _parse_sender ─────────────────────────────────────────────────────────────

def test_parse_sender_name_and_email():
    name, email = _parse_sender("John Doe <john@example.com>")
    assert name == "John Doe"
    assert email == "john@example.com"


def test_parse_sender_email_only():
    name, email = _parse_sender("john@example.com")
    assert name == "john@example.com"
    assert email == "john@example.com"


def test_parse_sender_quoted_name():
    name, email = _parse_sender('"John Doe" <john@example.com>')
    assert name == "John Doe"
    assert email == "john@example.com"


def test_parse_sender_strips_whitespace():
    name, email = _parse_sender("  Recruiter  <recruit@company.com>")
    assert name == "Recruiter"
    assert email == "recruit@company.com"


# ── resolve_after_date ────────────────────────────────────────────────────────

def test_resolve_after_date_with_days():
    args = argparse.Namespace(days=7, since=None)
    after, desc = resolve_after_date(args)
    assert after == date.today() - timedelta(days=7)
    assert "7" in desc


def test_resolve_after_date_with_since():
    args = argparse.Namespace(days=None, since="2026-01-01")
    after, desc = resolve_after_date(args)
    assert after == date(2026, 1, 1)
    assert "2026-01-01" in desc


def test_resolve_after_date_invalid_since_exits():
    args = argparse.Namespace(days=None, since="not-a-date")
    with pytest.raises(SystemExit):
        resolve_after_date(args)


def test_resolve_after_date_no_args_exits():
    args = argparse.Namespace(days=None, since=None)
    with pytest.raises(SystemExit):
        resolve_after_date(args)