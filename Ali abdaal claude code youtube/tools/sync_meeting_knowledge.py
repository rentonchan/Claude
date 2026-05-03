#!/usr/bin/env python3
"""
Fetches all meeting notes from Notion, compiles them into a structured
knowledge document, and saves to knowledge/meeting_notes.md.
Also uploads to Anthropic Files API so Claude can reference it in queries.
Runs daily via GitHub Actions.
"""

import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from notion_client import Client as NotionClient

load_dotenv()

NOTION_TOKEN  = os.environ.get("NOTION_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
MEETING_DB_ID = "34d7181b-0f40-8191-8e63-e880c90e8556"
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")
NOTES_FILE    = os.path.join(KNOWLEDGE_DIR, "meeting_notes.md")
FILE_ID_PATH  = os.path.join(KNOWLEDGE_DIR, ".file_id")


def get_transcription_title(notion: NotionClient, page_id: str) -> str:
    """Read the AI-generated title from the transcription block."""
    try:
        blocks = notion.blocks.children.list(block_id=page_id, page_size=5)
        for block in blocks.get("results", []):
            if block.get("type") == "transcription":
                rich = block.get("transcription", {}).get("title", [])
                parts = [t.get("plain_text", "") for t in rich if t.get("plain_text", "").strip()]
                return " ".join(parts).strip()
    except Exception:
        pass
    return ""


def fetch_all_meetings(notion: NotionClient) -> list[dict]:
    meetings = []
    cursor = None
    while True:
        kwargs = {
            "database_id": MEETING_DB_ID,
            "sorts": [{"property": "Date", "direction": "descending"}],
            "page_size": 100,
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        result = notion.databases.query(**kwargs)
        meetings.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")
    return meetings


def build_markdown(meetings: list[dict], notion: NotionClient, updated_at: str) -> str:
    lines = [
        "# Renton's Work Meeting Knowledge Base",
        f"_Last updated: {updated_at} HKT_",
        "",
        "This document contains all meeting notes for Renton Chan, based in Hong Kong,",
        "working in enterprise IT sales. Use it to answer questions about his work,",
        "meetings, deals, colleagues, and action items.",
        "",
        "---",
        "",
        "## Meeting Log",
        "",
    ]

    skipped = 0
    for page in meetings:
        props = page["properties"]

        # Get title — prefer transcription title over raw timestamp title
        raw_title = "".join([t.get("plain_text", "") for t in props.get("Title", {}).get("title", [])])
        if raw_title.startswith("📋 TEMPLATE"):
            skipped += 1
            continue

        trans_title = get_transcription_title(notion, page["id"])
        display_title = trans_title or raw_title

        # Metadata
        date_val  = (props.get("Date", {}).get("date") or {}).get("start", "")
        date_str  = date_val[:10] if date_val else "unknown date"
        mtype     = (props.get("Type", {}).get("select") or {}).get("name", "")
        attendees = [a["name"] for a in props.get("Attendees", {}).get("multi_select", [])]
        summary   = "".join([t.get("plain_text", "") for t in props.get("Summary", {}).get("rich_text", [])])
        done      = props.get("Action Items Done", {}).get("checkbox", False)

        lines.append(f"### {date_str} — {display_title}")
        meta_parts = []
        if mtype:      meta_parts.append(f"**Type:** {mtype}")
        if attendees:  meta_parts.append(f"**Attendees:** {', '.join(attendees)}")
        meta_parts.append(f"**Action items done:** {'Yes' if done else 'No'}")
        lines.append("  ".join(meta_parts))
        if summary:
            lines.append(f"**Summary:** {summary}")
        lines.append("")

    lines.append("---")
    lines.append(f"_Total meetings: {len(meetings) - skipped}_")
    return "\n".join(lines)


def upload_to_anthropic(content: str) -> str | None:
    """Upload knowledge doc to Anthropic Files API. Returns file_id or None."""
    if not ANTHROPIC_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.beta.files.upload(
            file=("meeting_notes.md", content.encode("utf-8"), "text/plain"),
        )
        return response.id
    except Exception as e:
        print(f"  Anthropic Files API: {e}")
        return None


def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set")

    tz         = ZoneInfo("Asia/Hong_Kong")
    updated_at = datetime.now(tz).strftime("%-d %b %Y, %H:%M")

    notion = NotionClient(auth=NOTION_TOKEN)

    print("Fetching all meeting notes from Notion...")
    meetings = fetch_all_meetings(notion)
    print(f"  {len(meetings)} meetings found")

    print("Building knowledge document...")
    content = build_markdown(meetings, notion, updated_at)

    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved to {NOTES_FILE} ({len(content):,} chars)")

    print("Uploading to Anthropic Files API...")
    file_id = upload_to_anthropic(content)
    if file_id:
        with open(FILE_ID_PATH, "w") as f:
            f.write(file_id)
        print(f"  Uploaded — file_id: {file_id}")
    else:
        print("  Skipped (no credits or key)")

    print(f"\n✅ Meeting knowledge synced — {updated_at}")
    print(f"   File: knowledge/meeting_notes.md")
    print(f"   Ask questions with: python tools/ask_work.py \"your question\"")


if __name__ == "__main__":
    main()
