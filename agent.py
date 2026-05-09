#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from datetime import date, datetime, timedelta

from src import config, dedup, run_logger as run_logger_module
from src.classifier import classify_email
from src.draft_generator import generate_draft
from src.gmail_client import AuthError, GmailClient
from src import notion_writer

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[union-attr]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

CATEGORIES = ["Career Opportunities", "AI News", "Cryptocurrency News", "Business News"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Email Inbox Management Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python agent.py --days 7\n"
            "  python agent.py --since 2026-05-01\n"
            "  python agent.py --days 3 --inbox primary\n"
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, metavar="N", help="Process emails from the last N days")
    group.add_argument("--since", type=str, metavar="YYYY-MM-DD", help="Process emails on or after this date")
    parser.add_argument(
        "--inbox",
        choices=["primary", "secondary", "both"],
        default="both",
        help="Which inbox(es) to process (default: both)",
    )
    return parser.parse_args()


def resolve_after_date(args) -> tuple[date, str]:
    if args.days is not None:
        after = date.today() - timedelta(days=args.days)
        return after, f"last {args.days} days"
    if args.since is not None:
        try:
            after = datetime.strptime(args.since, "%Y-%m-%d").date()
            return after, f"since {args.since}"
        except ValueError:
            print(f"ERROR: --since date must be in YYYY-MM-DD format, got '{args.since}'")
            sys.exit(1)
    print(
        "ERROR: You must specify a time range.\n"
        "  --days N          Process emails from the last N days\n"
        "  --since YYYY-MM-DD  Process emails on or after this date\n"
    )
    sys.exit(1)


def _parse_sender(raw_sender: str) -> tuple[str, str]:
    """Split 'Name <email>' into (name, email)."""
    if "<" in raw_sender and ">" in raw_sender:
        name = raw_sender.split("<")[0].strip().strip('"')
        email = raw_sender.split("<")[1].rstrip(">").strip()
        return name, email
    return raw_sender, raw_sender


def build_digest(run_log: run_logger_module.RunLogger, inboxes: list[str], time_range: str) -> str:
    counts = run_log.get_counts()
    job_emails = run_log.get_career_opportunity_emails()

    lines = [
        f"Email Agent — Run summary {date.today().strftime('%Y-%m-%d')}",
        f"Time range: {time_range}",
        f"Inboxes processed: {', '.join(inboxes)}",
        "",
        "── Summary ──────────────────────────────",
        f"  Total emails processed:   {counts['emails_processed']}",
        f"  Career Opportunities:      {counts['labelled_career_opportunities']}",
        f"  AI News:                  {counts['labelled_ai_news']}",
        f"  Cryptocurrency News:      {counts['labelled_cryptocurrency_news']}",
        f"  Business News:            {counts['labelled_business_news']}",
        f"  Drafts created:           {counts['drafts_created']}",
        f"  Notion items added:       {counts['notion_items_created']}",
        f"  Unmatched / skipped:      {counts['unmatched']}",
        "",
    ]

    if job_emails:
        lines.append("── Career Opportunity emails requiring attention ──")
        for e in job_emails:
            lines.append(f"  [{e['inbox']}] {e['sender']}  |  {e['subject']}")
        lines.append("")

    lines.append("This digest was generated automatically by your Email Agent.")
    return "\n".join(lines)


def process_inbox(inbox: str, after_date: date, run_log: run_logger_module.RunLogger) -> None:
    logger.info(f"Processing {inbox} inbox after {after_date}")

    try:
        gmail = GmailClient(inbox)
    except AuthError as e:
        logger.error(str(e))
        run_log.log_error(f"Auth failed for {inbox}: {e}")
        return

    # Ensure labels exist
    label_ids: dict[str, str] = {}
    for category in CATEGORIES:
        try:
            label_ids[category] = gmail.ensure_label(category)
        except Exception as e:
            logger.error(f"Label creation failed for '{category}' in {inbox}: {e}")
            run_log.log_error(f"Label creation failed '{category}' ({inbox}): {e}")

    # Fetch emails
    try:
        emails = gmail.get_emails(after_date)
    except Exception as e:
        logger.error(f"Failed to fetch emails from {inbox}: {e}")
        run_log.log_error(f"Email fetch failed ({inbox}): {e}")
        return

    logger.info(f"Fetched {len(emails)} emails from {inbox}")

    for email in emails:
        eid = email["id"]
        subject = email["subject"]
        sender = email["sender"]

        if dedup.is_processed(inbox, eid):
            logger.debug(f"Skipping already-processed email {eid}")
            continue

        if not email["body"]:
            logger.warning(f"Could not decode body for {eid} — skipping")
            run_log.log_email(inbox, eid, subject, sender, "decode_error")
            dedup.mark_processed(inbox, eid)
            continue

        time.sleep(0.5)
        result = classify_email(subject, sender, email["body"])

        if result.confidence == "low":
            logger.info(f"Low confidence for '{subject}' — skipping label")
            run_log.log_email(inbox, eid, subject, sender, "low_confidence_unmatched")
            continue

        if result.category in label_ids:
            try:
                gmail.apply_label(eid, label_ids[result.category])
            except Exception as e:
                logger.error(f"Failed to apply label to {eid}: {e}")
                run_log.log_error(f"Label apply failed {eid}: {e}")

        if result.category == "Career Opportunities" and result.reply_required:
            try:
                time.sleep(0.5)
                draft_body = generate_draft(subject, sender, email["body"])

                gmail.create_draft(
                    to=sender,
                    subject=f"Re: {subject}",
                    body=draft_body,
                    thread_id=email["thread_id"],
                )

                sender_name, sender_email = _parse_sender(sender)
                notion_writer.append_action_item(
                    subject=subject,
                    sender_name=sender_name,
                    sender_email=sender_email,
                    received_date=email["date"],
                    inbox_email=config.INBOX_EMAILS[inbox],
                    summary=f"Draft reply created. {result.reply_required_reason or ''}".strip(),
                )

                run_log.log_email(inbox, eid, subject, sender, "draft_created")
                logger.info(f"Draft created for '{subject}' from {sender}")

            except Exception as e:
                logger.error(f"Draft/Notion failed for {eid}: {e}")
                run_log.log_error(f"Draft/Notion failed {eid}: {e}")
                run_log.log_email(inbox, eid, subject, sender, "labelled_career_opportunities")

        elif result.category == "Unmatched":
            run_log.log_email(inbox, eid, subject, sender, "unmatched")
        else:
            outcome = "labelled_" + result.category.lower().replace(" ", "_")
            run_log.log_email(inbox, eid, subject, sender, outcome)

        dedup.mark_processed(inbox, eid)


def main():
    args = parse_args()
    after_date, time_range_desc = resolve_after_date(args)

    try:
        config.validate()
    except EnvironmentError as e:
        print(f"Configuration error:\n{e}")
        sys.exit(1)

    inboxes = ["primary", "secondary"] if args.inbox == "both" else [args.inbox]
    run_log = run_logger_module.RunLogger()

    logger.info(f"Agent starting — {time_range_desc}, inboxes: {inboxes}")

    for inbox in inboxes:
        process_inbox(inbox, after_date, run_log)

    run_log.write(time_range_desc, inboxes)

    # Send digest
    counts = run_log.get_counts()
    if counts["emails_processed"] == 0:
        logger.info("No emails found in the specified time range. Nothing to process.")
        print("\nNo emails found in the specified time range. Nothing to process.")
        return

    digest_body = build_digest(run_log, inboxes, time_range_desc)
    digest_subject = f"Email Agent — Run summary {date.today().strftime('%Y-%m-%d')}"

    try:
        primary_gmail = GmailClient("primary")
        primary_gmail.send_message(
            to=config.PRIMARY_EMAIL,
            subject=digest_subject,
            body=digest_body,
        )
        logger.info("Digest email sent to primary inbox")
    except Exception as e:
        logger.error(f"Failed to send digest email: {e}")
        run_log.log_error(f"Digest send failed: {e}")

    print(f"\n{digest_body}")
    logger.info("Agent run complete")


if __name__ == "__main__":
    main()
