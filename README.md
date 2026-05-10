# Email Inbox Management Agent

On-demand CLI agent that processes two Gmail inboxes, classifies each email with the Claude API, applies Gmail labels, drafts replies for actionable career emails, logs them to a Notion to-do page, and emails a digest summary at the end of the run.

The agent never sends mail on your behalf (except the digest to your own primary inbox), never deletes or archives, and is safe to re-run over the same time range.

---

## Prerequisites

- Python 3.10+
- A Google Cloud project with the Gmail API enabled
- An Anthropic API key
- A Notion integration token and a target page ID

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Google Cloud OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services → Library**, search for **Gmail API**, and click **Enable**
4. Navigate to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth client ID**
6. Application type: **Desktop app**
7. Download the credentials JSON file

Both Gmail accounts can share the same credentials — Google prompts you for the account at sign-in time.

### 3. Authenticate both Gmail accounts

```bash
python setup_oauth.py
```

The script prompts for your two Gmail addresses and the path to the credentials JSON, then opens a browser for each account in turn. Sign in as the matching address and grant all requested permissions. Two token files are written: `token_primary.json` and `token_secondary.json`.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in all values:

| Variable | How to get it |
|---|---|
| `GMAIL_EMAIL_PRIMARY` | The primary Gmail address |
| `GMAIL_EMAIL_SECONDARY` | The secondary Gmail address |
| `GMAIL_CREDENTIALS_PRIMARY` | Contents of the credentials JSON, as a single line |
| `GMAIL_CREDENTIALS_SECONDARY` | Same credentials JSON — both accounts share one project |
| `GMAIL_TOKEN_PRIMARY` | Contents of `token_primary.json`, as a single line |
| `GMAIL_TOKEN_SECONDARY` | Contents of `token_secondary.json`, as a single line |
| `NOTION_API_KEY` | From [notion.so/my-integrations](https://www.notion.so/my-integrations) |
| `NOTION_PAGE_ID` | From your Notion page URL: `notion.so/Page-Title-<THIS-PART>` |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com/) |

To collapse a JSON file to a single line:

```bash
# bash / zsh / macOS / Linux
python -c "import json; print(json.dumps(json.load(open('token_primary.json'))))"
```

```powershell
# Windows PowerShell
python -c "import json; print(json.dumps(json.load(open(\"token_primary.json\"))))"
```

### 5. Share the Notion page with your integration

Open the target page in Notion → **Share** → invite your integration by name. Without this, Notion appends fail with a permissions error.

---

## Usage

```bash
# Last 7 days, both inboxes (default)
python agent.py --days 7

# From a specific date forward
python agent.py --since 2026-05-01

# Single inbox
python agent.py --days 3 --inbox primary
python agent.py --days 3 --inbox secondary
```

A time range is mandatory. Running `python agent.py` with neither `--days` nor `--since` exits with an error rather than silently defaulting.

---

## What the agent does

For each email in the specified time range:

1. **Classifies** the email via Claude (`claude-sonnet-4-6`) into one of:
   - `Career Opportunities`
   - `AI News`
   - `Cryptocurrency News`
   - `Business News`
   - `Unmatched` (no label applied)

   When multiple categories could apply, the order above is the priority. Low-confidence classifications are recorded as `low_confidence_unmatched` and no label is applied.

2. **Applies the matching Gmail label.** Labels are auto-created on first run if they don't exist. Colours can be customised in Gmail; the agent does not set them.

3. **For `Career Opportunities` emails that require a reply:**
   - Generates a draft reply via Claude in a warm, professional tone, with `[placeholders]` for facts the agent does not know
   - Saves it to your Gmail Drafts folder, threaded with the original message — never sends
   - Appends an action item to the configured Notion page

   "Requires a reply" means the email asks a question, requests scheduling, asks for documents, or otherwise needs acknowledgement. Automated rejections and one-way status updates are labelled but not drafted.

4. **Sends a digest email** from your primary inbox to itself (`GMAIL_EMAIL_PRIMARY`), summarising the run: counts per category, drafts created, Notion items added, plus a per-email list of career opportunities. Skipped if zero emails were processed.

---

## Files

| Path | Purpose |
|---|---|
| `agent.py` | CLI entry point and orchestration |
| `setup_oauth.py` | One-time interactive OAuth setup |
| `src/config.py` | Env-var validation and getters |
| `src/anthropic_client.py` | Lazy singleton Anthropic client |
| `src/classifier.py` | Claude email classification |
| `src/draft_generator.py` | Claude reply drafting |
| `src/gmail_client.py` | Gmail OAuth, fetch, label, draft, send |
| `src/dedup.py` | Per-inbox processed-id store |
| `src/notion_writer.py` | Append action items to a Notion page |
| `src/run_logger.py` | In-memory run counts → append-only `run_log.json` |
| `tests/` | Pytest suite |
| `processed_ids.json` | Auto-created — emails already processed won't be reprocessed |
| `run_log.json` | Auto-created — append-only audit log of every run |
| `agent.log` | Auto-created — detailed runtime log |

---

## Tests

```bash
pytest
```

Covers the classifier (with mocked Anthropic responses), the dedup store (tmp-path isolation), the run logger, and the agent's argument-parsing helpers. The Gmail, Notion, and draft-generation modules are not currently covered by tests.

---

## Notes

- The agent **never sends emails** on your behalf except the run digest to your own primary inbox.
- The agent **never deletes or archives** emails.
- Re-running over the same time range is safe — `processed_ids.json` prevents double-processing per inbox.
- If a Notion write fails, labelling and drafting continue uninterrupted; the failure is logged.
- Auth, fetch, classify, label, draft, and Notion errors are caught at distinct boundaries — one bad email does not abort the run.
- Email body content is truncated to the first 4000 characters before being sent to Claude for classification or drafting.
- A 0.5 s delay between Claude calls and 0.35 s between Notion appends is built in to stay polite to upstream APIs.
