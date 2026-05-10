import os
import pytest
import src.dedup as dedup_module


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup_module, "_cache", None)
    monkeypatch.setattr(dedup_module, "_PATH", str(tmp_path / "processed_ids.json"))


def test_new_email_is_not_processed():
    assert not dedup_module.is_processed("primary", "abc123")


def test_marked_email_is_processed():
    dedup_module.mark_processed("primary", "abc123")
    assert dedup_module.is_processed("primary", "abc123")


def test_inboxes_do_not_cross_contaminate():
    dedup_module.mark_processed("primary", "abc123")
    assert not dedup_module.is_processed("secondary", "abc123")


def test_in_memory_cache_avoids_disk_reads(monkeypatch):
    dedup_module.mark_processed("primary", "abc123")
    os.remove(dedup_module._PATH)
    assert dedup_module.is_processed("primary", "abc123")


def test_persists_to_disk_and_reloads(monkeypatch):
    dedup_module.mark_processed("primary", "abc123")
    monkeypatch.setattr(dedup_module, "_cache", None)
    assert dedup_module.is_processed("primary", "abc123")


def test_duplicate_mark_does_not_error():
    dedup_module.mark_processed("primary", "abc123")
    dedup_module.mark_processed("primary", "abc123")
    assert dedup_module.is_processed("primary", "abc123")