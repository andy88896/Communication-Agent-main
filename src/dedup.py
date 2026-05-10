import json
import os

_PATH = "processed_ids.json"
_cache: dict[str, set[str]] | None = None


def _ensure_loaded() -> dict[str, set[str]]:
    global _cache
    if _cache is None:
        if not os.path.exists(_PATH):
            _cache = {"primary": set(), "secondary": set()}
        else:
            with open(_PATH) as f:
                raw = json.load(f)
            _cache = {k: set(v) for k, v in raw.items()}
    return _cache


def _save() -> None:
    data = {k: list(v) for k, v in _cache.items()}
    with open(_PATH, "w") as f:
        json.dump(data, f, indent=2)


def is_processed(inbox: str, email_id: str) -> bool:
    return email_id in _ensure_loaded().get(inbox, set())


def mark_processed(inbox: str, email_id: str) -> None:
    cache = _ensure_loaded()
    if inbox not in cache:
        cache[inbox] = set()
    if email_id not in cache[inbox]:
        cache[inbox].add(email_id)
        _save()