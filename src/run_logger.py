import json
import os
from datetime import datetime
from typing import Any

_PATH = "run_log.json"

_OUTCOME_FIELDS = {
    "labelled_job_applications":  "labelled_job_applications",
    "labelled_ai_news":           "labelled_ai_news",
    "labelled_cryptocurrency_news": "labelled_cryptocurrency_news",
    "draft_created":              "drafts_created",
    "notion_item_created":        "notion_items_created",
    "unmatched":                  "unmatched",
    "low_confidence_unmatched":   "unmatched",
    "decode_error":               "errors",
}


class RunLogger:
    def __init__(self):
        self._counts = {
            "emails_processed":             0,
            "labelled_job_applications":    0,
            "labelled_ai_news":             0,
            "labelled_cryptocurrency_news": 0,
            "drafts_created":               0,
            "notion_items_created":         0,
            "unmatched":                    0,
        }
        self._errors: list[str] = []
        self._job_application_emails: list[dict] = []

    def log_email(self, inbox: str, email_id: str, subject: str, sender: str, outcome: str) -> None:
        self._counts["emails_processed"] += 1

        if outcome == "draft_created":
            self._counts["drafts_created"] += 1
            self._counts["labelled_job_applications"] += 1
            self._counts["notion_items_created"] += 1
            self._job_application_emails.append({"inbox": inbox, "subject": subject, "sender": sender})
        elif outcome == "labelled_job_applications":
            self._counts["labelled_job_applications"] += 1
            self._job_application_emails.append({"inbox": inbox, "subject": subject, "sender": sender})
        elif outcome == "labelled_ai_news":
            self._counts["labelled_ai_news"] += 1
        elif outcome == "labelled_cryptocurrency_news":
            self._counts["labelled_cryptocurrency_news"] += 1
        elif outcome in ("unmatched", "low_confidence_unmatched", "decode_error"):
            self._counts["unmatched"] += 1

    def log_error(self, message: str) -> None:
        self._errors.append(message)

    def get_job_application_emails(self) -> list[dict]:
        return self._job_application_emails

    def get_counts(self) -> dict:
        return dict(self._counts)

    def write(self, time_range: str, inboxes_processed: list[str]) -> None:
        entry = {
            "run_timestamp": datetime.now().isoformat(),
            "time_range": time_range,
            "inbox": inboxes_processed,
            **self._counts,
            "errors": self._errors,
        }

        existing: list[Any] = []
        if os.path.exists(_PATH):
            with open(_PATH, "r") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        existing.append(entry)
        with open(_PATH, "w") as f:
            json.dump(existing, f, indent=2)
