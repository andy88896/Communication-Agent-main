# Email Inbox Management Agent

Processes two Gmail inboxes on demand, classifies emails with the Claude API, applies labels, drafts replies for job application emails, logs action items to Notion, and sends a post-run digest.

---

## Prerequisites

- Python 3.10+
- A Google Cloud project with the Gmail API enabled
- An Anthropic API key (set as `ANTHROPIC_API_KEY` in your environment)
- A Notion integration token and page ID

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Google Cloud project and OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services → Library**, search for **Gmail API**, and click **Enable**
4. Navigate to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth client ID**
6. Application type: **Desktop app**
7. Download the credentials JSON file — you'll need this in the next step

### 3. Authenticate both Gmail accounts

```bash
python setup_oauth.py
```

This will open a browser window for each account. Sign in as prompted and grant the required permissions. Two token files will be created: `token_primary.json` and `token_secondary.json`.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in all six values:

| Variable | How to get it |
|---|---|
| `GMAIL_CREDENTIALS_PRIMARY` | Paste the contents of your downloaded credentials JSON (as a single line) |
| `GMAIL_CREDENTIALS_SECONDARY` | Same credentials JSON — both accounts share one Google Cloud project |
| `GMAIL_TOKEN_PRIMARY` | Run: `python -c "import json; print(json.dumps(json.load(open('token_primary.json'))))"` |
| `GMAIL_TOKEN_SECONDARY` | Run: `python -c "import json; print(json.dumps(json.load(open('token_secondary.json'))))"` |
| `NOTION_API_KEY` | From [notion.so/my-integrations](https://www.notion.so/my-integrations) |
| `NOTION_PAGE_ID` | From your Notion page URL: `notion.so/Page-Title-**<THIS-PART>**` |

Also set your Anthropic API key:

```bash
# Add to .env or export directly
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Share the Notion page with your integration

In Notion, open the target page → **Share** → add your integration by name.

---

## Usage

```bash
# Process emails from the last 7 days (both inboxes)
python agent.py --days 7

# Process emails from a specific date
python agent.py --since 2026-05-01

# Process only the primary inbox
python agent.py --days 3 --inbox primary

# Process only the secondary inbox
python agent.py --days 3 --inbox secondary
```

If you run the agent without `--days` or `--since`, it will print an error and exit rather than defaulting silently.

---

## What the agent does

For each email in the specified time range:

1. **Classifies** the email using the Claude API into one of:
   - `Career Opportunities` → green label
   - `AI News` → blue label
   - `Cryptocurrency News` → yellow label
   - Unmatched → no action

2. **Applies the Gmail label** (creates labels on first run if they don't exist)

3. **For Job Application emails that require a reply:**
   - Generates a draft reply with the Claude API
   - Saves the draft to your Gmail Drafts folder (never sends)
   - Appends an action item to your Notion to-do page

4. **Sends a digest email** to `andrewch810@gmail.com` summarising the run

---

## Files

| File | Purpose |
|---|---|
| `agent.py` | Main entry point |
| `setup_oauth.py` | One-time OAuth setup for both Gmail accounts |
| `src/` | Core modules (classifier, draft generator, Gmail/Notion clients) |
| `processed_ids.json` | Deduplication store — emails already processed won't be reprocessed |
| `run_log.json` | Append-only audit log of every agent run |
| `agent.log` | Detailed runtime log |

---

## Notes

- The agent **never sends emails** on your behalf — except the digest to your own primary inbox
- The agent **never deletes or archives** emails
- Emails with low classification confidence are skipped and logged as `low_confidence_unmatched`
- If a Notion write fails, labelling and drafting continue uninterrupted
- Re-running the agent over the same time range is safe — `processed_ids.json` prevents double-processing
