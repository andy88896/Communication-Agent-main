#!/usr/bin/env python3
"""
One-time OAuth setup script.
Run this once per Gmail account before using agent.py.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def print_prereqs():
    print("""
┌─────────────────────────────────────────────────────────────────┐
│              Gmail OAuth Setup — Prerequisites                  │
└─────────────────────────────────────────────────────────────────┘

Before running this script, you need a Google Cloud project with the
Gmail API enabled and OAuth 2.0 credentials downloaded.

Steps (takes ~5 minutes):

  1. Go to https://console.cloud.google.com/
  2. Create a new project (or select an existing one)
  3. Go to "APIs & Services" → "Library"
  4. Search for "Gmail API" and click Enable
  5. Go to "APIs & Services" → "Credentials"
  6. Click "Create Credentials" → "OAuth client ID"
  7. Application type: Desktop app
  8. Download the credentials JSON file

You can use the same credentials JSON for BOTH Gmail accounts —
Google will prompt you to choose which account to authorise each time.

Press Enter when you have the credentials JSON file ready...
""")
    input()


def authenticate_inbox(inbox: dict, credentials_path: str) -> dict:
    print(f"\n── Authenticating {inbox['name']} inbox ({inbox['email']}) ──")
    print("A browser window will open. Sign in as:", inbox["email"])
    print("Grant all requested permissions, then return here.\n")
    input("Press Enter to open the browser...")

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = json.loads(creds.to_json())

    # Save to file
    with open(inbox["token_file"], "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n✓ Token saved to {inbox['token_file']}")
    return token_data


def print_env_instructions(results: list[dict]):
    print("""
┌─────────────────────────────────────────────────────────────────┐
│              Next steps — configure your .env file              │
└─────────────────────────────────────────────────────────────────┘

Copy .env.example to .env, then fill in the values below.

Add your email addresses:
  GMAIL_EMAIL_PRIMARY=<your primary Gmail address>
  GMAIL_EMAIL_SECONDARY=<your secondary Gmail address>

Your credentials JSON file contents go into GMAIL_CREDENTIALS_PRIMARY
and GMAIL_CREDENTIALS_SECONDARY (both accounts can use the same
credentials JSON — paste the raw file contents as a single line).

The token values below have been saved to local JSON files. To put
them in your .env, run:

  python -c "import json; d=json.load(open('token_primary.json')); print(json.dumps(d))"
  python -c "import json; d=json.load(open('token_secondary.json')); print(json.dumps(d))"

Copy each output line as the value for GMAIL_TOKEN_PRIMARY and
GMAIL_TOKEN_SECONDARY respectively.

NOTION_API_KEY: Get this from https://www.notion.so/my-integrations
NOTION_PAGE_ID: Extract from the Notion page URL
  e.g. notion.so/Email-to-do-list-35ad5fe2fda580f89a4fdc94cfffa253
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                    this part is the page ID

Once your .env is configured, run:
  python agent.py --days 7
""")


def main():
    print_prereqs()

    primary_email   = input("Primary Gmail address: ").strip()
    secondary_email = input("Secondary Gmail address: ").strip()
    if not primary_email or not secondary_email:
        print("Both email addresses are required. Exiting.")
        sys.exit(1)

    inboxes = [
        {"name": "primary",   "email": primary_email,   "token_env": "GMAIL_TOKEN_PRIMARY",   "token_file": "token_primary.json"},
        {"name": "secondary", "email": secondary_email, "token_env": "GMAIL_TOKEN_SECONDARY", "token_file": "token_secondary.json"},
    ]

    credentials_path = input("Enter the path to your downloaded credentials JSON file: ").strip()
    if not credentials_path:
        print("No path provided. Exiting.")
        sys.exit(1)

    results = []
    for inbox in inboxes:
        try:
            token = authenticate_inbox(inbox, credentials_path)
            results.append({"inbox": inbox, "token": token, "ok": True})
        except Exception as e:
            print(f"\nERROR authenticating {inbox['name']} inbox: {e}")
            results.append({"inbox": inbox, "ok": False, "error": str(e)})

    print_env_instructions(results)

    failed = [r for r in results if not r["ok"]]
    if failed:
        print(f"WARNING: {len(failed)} inbox(es) failed to authenticate:")
        for r in failed:
            print(f"  - {r['inbox']['name']}: {r['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
