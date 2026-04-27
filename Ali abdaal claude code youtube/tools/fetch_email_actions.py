#!/usr/bin/env python3
"""
Fetches yesterday's Gmail, uses Claude to extract actions and key thoughts,
then updates the 📧 Email Digest section on Renton's Daily Agenda Planner.
Runs daily at 7:03am HKT via run_morning.sh.
"""

import os
import pickle
import base64
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import anthropic
from google import genai
from dotenv import load_dotenv
from notion_client import Client as NotionClient
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

NOTION_TOKEN     = os.environ.get("NOTION_TOKEN")
ANTHROPIC_KEY    = os.environ.get("ANTHROPIC_API_KEY")
GEMINI_KEY       = os.environ.get("GEMINI_API_KEY")
HOME_PAGE_ID     = "2187181b-0f40-8015-8e41-d752899e9aed"
EMAIL_TOGGLE_ID  = None  # set after first run — see bottom of file

TIMEZONE   = "Asia/Hong_Kong"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "token.pickle")
CREDS_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
SCOPES     = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Senders/patterns to skip — automated noise
SKIP_SENDERS = [
    "no-reply", "noreply", "notification", "mailer", "newsletter",
    "digest", "donotreply", "do-not-reply", "quora", "iherb",
    "ted.com", "beehiiv", "marketing", "promo", "offer",
]
SKIP_SUBJECTS = [
    "unsubscribe", "newsletter", "promo", "offer", "deal",
    "digest", "security alert", "successful payment", "topped up",
    "eStatement", "eAdvice", "hide my email",
]


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
    if creds and not all(s in (creds.scopes or []) for s in SCOPES):
        creds = None
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return creds


# ── Gmail fetch ───────────────────────────────────────────────────────────────

def is_noise(sender: str, subject: str) -> bool:
    s = sender.lower()
    sub = subject.lower()
    if any(skip in s for skip in SKIP_SENDERS):
        return True
    if any(skip in sub for skip in SKIP_SUBJECTS):
        return True
    return False


def decode_body(payload: dict) -> str:
    """Extract plain text from email payload."""
    body = ""
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
    # Strip excessive whitespace
    body = re.sub(r'\n{3,}', '\n\n', body.strip())
    return body[:3000]  # Cap at 3000 chars for Claude


def fetch_emails(gmail_service, since_hours: int = 24) -> list[dict]:
    """Returns list of {sender, subject, snippet, body} for actionable emails."""
    tz        = ZoneInfo(TIMEZONE)
    since     = datetime.now(tz) - timedelta(hours=since_hours)
    query     = f"in:inbox newer_than:{since_hours}h"

    results   = gmail_service.users().messages().list(
        userId="me", q=query, maxResults=30
    ).execute()

    emails = []
    for msg_ref in results.get("messages", []):
        msg = gmail_service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender  = headers.get("From", "")
        subject = headers.get("Subject", "(no subject)")
        snippet = msg.get("snippet", "")

        if is_noise(sender, subject):
            continue

        body = decode_body(msg.get("payload", {}))
        emails.append({
            "sender":  sender,
            "subject": subject,
            "snippet": snippet,
            "body":    body or snippet,
        })

    return emails


# ── Claude analysis ───────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """You are reviewing emails for Renton Chan. He is based in Hong Kong and works in enterprise IT sales.

Analyse these emails and extract:
1. ACTIONS - specific things he needs to do, including deadlines
2. CONSIDER - things worth thinking about or requiring a decision
3. FYI - informational only, no action needed

Be concise. One short sentence per item. Skip truly irrelevant items.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "actions": ["Pay Rates and Government Rent by 30 Apr — eRVD Bill"],
  "consider": ["CoStar investment thesis — real estate digitisation angle"],
  "fyi": ["HSBC statement available"]
}}

Emails:
{email_text}"""


def build_email_text(emails: list[dict]) -> str:
    text = ""
    for i, e in enumerate(emails, 1):
        text += f"\n--- Email {i} ---\nFrom: {e['sender']}\nSubject: {e['subject']}\n{e['body'][:800]}\n"
    return text


def parse_json_result(text: str) -> dict:
    import json
    text = text.strip()
    if "```" in text:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        text  = match.group(0) if match else text
    return json.loads(text)


def analyse_with_claude(email_text: str) -> dict:
    client   = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    prompt   = ANALYSIS_PROMPT.format(email_text=email_text)
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_result(response.content[0].text)


def analyse_with_gemini(email_text: str) -> dict:
    client   = genai.Client(api_key=GEMINI_KEY)
    prompt   = ANALYSIS_PROMPT.format(email_text=email_text)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return parse_json_result(response.text)


ACTION_KEYWORDS   = ["due", "deadline", "by ", "urgent", "action required",
                     "please reply", "please respond", "please confirm",
                     "payment", "overdue", "reminder", "asap", "follow up"]
CONSIDER_KEYWORDS = ["consider", "review", "feedback", "thoughts", "what do you think",
                     "opportunity", "proposal", "invitation", "decision"]


def keyword_analyse(emails: list[dict]) -> dict:
    """Rule-based fallback — always works, no API needed."""
    actions, consider, fyi = [], [], []
    for e in emails:
        combined = (e["subject"] + " " + e["snippet"]).lower()
        label    = f"{e['subject']}  ({e['sender'].split('<')[0].strip()})"
        if any(k in combined for k in ACTION_KEYWORDS):
            actions.append(label)
        elif any(k in combined for k in CONSIDER_KEYWORDS):
            consider.append(label)
        else:
            fyi.append(label)
    return {"actions": actions, "consider": consider, "fyi": fyi}


def analyse_emails(emails: list[dict]) -> dict:
    """
    Priority order:
      1. Claude Haiku  — best quality, needs Anthropic credits
      2. Gemini Flash  — free tier, needs billing on Google Cloud project
      3. Keyword match — always works, no API needed
    """
    if not emails:
        return {"actions": [], "consider": [], "fyi": []}

    email_text = build_email_text(emails)

    # 1. Try Claude
    if ANTHROPIC_KEY:
        try:
            print("  Using Claude Haiku...")
            return analyse_with_claude(email_text)
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e).lower():
                print("  Claude: no credits — trying Gemini")
            else:
                raise

    # 2. Try Gemini
    if GEMINI_KEY:
        try:
            print("  Using Gemini Flash...")
            return analyse_with_gemini(email_text)
        except Exception as e:
            print(f"  Gemini unavailable ({type(e).__name__}) — using keyword fallback")

    # 3. Keyword fallback — always works
    print("  Using keyword matching...")
    return keyword_analyse(emails)


# ── Notion blocks ─────────────────────────────────────────────────────────────

def txt(content, bold=False, color="default"):
    return {"type": "text", "text": {"content": content},
            "annotations": {"bold": bold, "color": color,
                            "italic": False, "strikethrough": False,
                            "underline": False, "code": False}}

def bullet(text, color="default"):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [txt(text, color=color)]}}

def toggle(label, children, color="default"):
    return {"object": "block", "type": "toggle",
            "toggle": {"rich_text": [txt(label, bold=True)],
                       "color": color, "children": children}}

def para(text, color="default"):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [txt(text, color=color)]}}


def build_digest_blocks(result: dict, refresh_at: str, email_count: int) -> list:
    blocks = []

    # Actions
    actions = result.get("actions", [])
    action_children = [bullet(f"• {a}", "red") for a in actions] or [para("Nothing urgent.", "gray")]
    blocks.append(toggle(f"⚡ Actions needed  ({len(actions)})", action_children, "red_background"))

    # Consider
    consider = result.get("consider", [])
    consider_children = [bullet(f"• {c}", "orange") for c in consider] or [para("Nothing to consider.", "gray")]
    blocks.append(toggle(f"💭 Things to consider  ({len(consider)})", consider_children, "orange_background"))

    # FYI
    fyi = result.get("fyi", [])
    fyi_children = [bullet(f"• {f}") for f in fyi] or [para("Nothing.", "gray")]
    blocks.append(toggle(f"📬 FYI — no action  ({len(fyi)})", fyi_children))

    return blocks


# ── Notion update ─────────────────────────────────────────────────────────────

def get_or_create_email_section(notion: NotionClient) -> str:
    """Find the Email Digest toggle on the home page, or create it. Returns block ID."""
    children = notion.blocks.children.list(block_id=HOME_PAGE_ID, page_size=100)
    for block in children.get("results", []):
        if block.get("type") == "toggle":
            rich = block.get("toggle", {}).get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in rich)
            if "Email Digest" in text:
                return block["id"]

    # Not found — create heading + toggle at end of page
    notion.blocks.children.append(
        block_id=HOME_PAGE_ID,
        children=[
            {"object": "block", "type": "divider", "divider": {}},
            {"object": "block", "type": "heading_2",
             "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📧 Email Digest"}}],
                           "color": "purple_background"}},
        ]
    )
    # Now create the toggle so we can get its ID
    resp = notion.blocks.children.append(
        block_id=HOME_PAGE_ID,
        children=[toggle("📧 Email Digest — loading...", [para("Fetching...")])]
    )
    return resp["results"][0]["id"]


def update_email_section(notion: NotionClient, toggle_id: str, blocks: list, refresh_at: str, count: int):
    # Update toggle label
    notion.blocks.update(
        block_id=toggle_id,
        **{"toggle": {
            "rich_text": [txt(f"📧 Email Digest — {refresh_at}  ·  {count} emails analysed", bold=True)],
            "color": "purple_background",
        }}
    )
    # Clear old children
    old = notion.blocks.children.list(block_id=toggle_id)
    for b in old.get("results", []):
        notion.blocks.delete(block_id=b["id"])
    # Add new content
    notion.blocks.children.append(block_id=toggle_id, children=blocks)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set")
    if not ANTHROPIC_KEY:
        raise SystemExit("ERROR: ANTHROPIC_API_KEY not set")

    tz         = ZoneInfo(TIMEZONE)
    now        = datetime.now(tz)
    refresh_at = now.strftime("%-d %b %Y, %H:%M HKT")

    print("Fetching Gmail...")
    creds        = get_credentials()
    gmail        = build("gmail", "v1", credentials=creds)
    emails       = fetch_emails(gmail, since_hours=24)
    print(f"  {len(emails)} actionable emails found")

    if emails:
        print("  Analysing with Claude...")
        result = analyse_emails(emails)
    else:
        result = {"actions": [], "consider": [], "fyi": []}

    print(f"  Actions: {len(result.get('actions', []))} | "
          f"Consider: {len(result.get('consider', []))} | "
          f"FYI: {len(result.get('fyi', []))}")

    notion     = NotionClient(auth=NOTION_TOKEN)
    toggle_id  = get_or_create_email_section(notion)
    blocks     = build_digest_blocks(result, refresh_at, len(emails))
    update_email_section(notion, toggle_id, blocks, refresh_at, len(emails))

    print(f"✅ Email Digest updated — {refresh_at}")


if __name__ == "__main__":
    main()
