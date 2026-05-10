from src.run_logger import RunLogger


def test_draft_created_increments_draft_and_career_counts():
    rl = RunLogger()
    rl.log_email("primary", "id1", "Job offer", "recruiter@x.com", "draft_created")
    counts = rl.get_counts()
    assert counts["drafts_created"] == 1
    assert counts["labelled_career_opportunities"] == 1


def test_draft_created_does_not_increment_notion_count():
    rl = RunLogger()
    rl.log_email("primary", "id1", "Job offer", "recruiter@x.com", "draft_created")
    assert rl.get_counts()["notion_items_created"] == 0


def test_log_notion_item_increments_notion_count():
    rl = RunLogger()
    rl.log_notion_item()
    assert rl.get_counts()["notion_items_created"] == 1


def test_labelled_ai_news():
    rl = RunLogger()
    rl.log_email("primary", "id1", "AI digest", "news@x.com", "labelled_ai_news")
    assert rl.get_counts()["labelled_ai_news"] == 1


def test_labelled_business_news():
    rl = RunLogger()
    rl.log_email("primary", "id1", "Markets", "news@x.com", "labelled_business_news")
    assert rl.get_counts()["labelled_business_news"] == 1


def test_labelled_cryptocurrency_news():
    rl = RunLogger()
    rl.log_email("primary", "id1", "BTC update", "news@x.com", "labelled_cryptocurrency_news")
    assert rl.get_counts()["labelled_cryptocurrency_news"] == 1


def test_unmatched_and_low_confidence_both_count_as_unmatched():
    rl = RunLogger()
    rl.log_email("primary", "id1", "Random", "x@x.com", "unmatched")
    rl.log_email("primary", "id2", "Random", "x@x.com", "low_confidence_unmatched")
    assert rl.get_counts()["unmatched"] == 2


def test_emails_processed_increments_for_every_outcome():
    rl = RunLogger()
    rl.log_email("primary", "id1", "A", "x@x.com", "unmatched")
    rl.log_email("primary", "id2", "B", "x@x.com", "draft_created")
    rl.log_email("primary", "id3", "C", "x@x.com", "labelled_ai_news")
    assert rl.get_counts()["emails_processed"] == 3


def test_career_opportunity_emails_populated_on_draft_and_label():
    rl = RunLogger()
    rl.log_email("primary", "id1", "Offer", "r@x.com", "draft_created")
    rl.log_email("primary", "id2", "Lead", "r@x.com", "labelled_career_opportunities")
    emails = rl.get_career_opportunity_emails()
    assert len(emails) == 2
    assert emails[0]["subject"] == "Offer"
    assert emails[1]["subject"] == "Lead"


def test_get_counts_returns_copy():
    rl = RunLogger()
    counts = rl.get_counts()
    counts["emails_processed"] = 999
    assert rl.get_counts()["emails_processed"] == 0