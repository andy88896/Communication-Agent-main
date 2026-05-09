import json
import os

_PATH = "processed_ids.json"


def _load() -> dict:
    if not os.path.exists(_PATH):
        return {"primary": [], "secondary": []}
    with open(_PATH, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_PATH, "w") as f:
        json.dump(data, f, indent=2)


def is_processed(inbox: str, email_id: str) -> bool:
    data = _load()
    return email_id in data.get(inbox, [])


def mark_processed(inbox: str, email_id: str) -> None:
    data = _load()
    if inbox not in data:
        data[inbox] = []
    if email_id not in data[inbox]:
        data[inbox].append(email_id)
    _save(data)
