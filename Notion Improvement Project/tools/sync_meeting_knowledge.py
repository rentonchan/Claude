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


def rich_to_text(rich: list) -> str:
    return "".join(t.get("plain_text", "") for t in rich).strip()


def get_meeting_content(notion: NotionClient, page_id: str) -> tuple[str, str]:
    """
    Returns (title, structured_notes) by diving into the transcription block.
    The transcription block has children:
      - first paragraph child  → structured notes (headings + bullets + action items)
      - second paragraph child → raw transcript (verbose, skipped)
    """
    title   = ""
    content = []
    try:
        top = notion.blocks.children.list(block_id=page_id, page_size=5)
        for block in top.get("results", []):
            if block.get("type") != "transcription":
                continue

            # Extract title
            rich  = block.get("transcription", {}).get("title", [])
            title = " ".join(t.get("plain_text", "") for t in rich if t.get("plain_text", "").strip()).strip()

            if not block.get("has_children"):
                break

            # Get transcription's children (paragraphs wrapping content)
            children = notion.blocks.children.list(block_id=block["id"], page_size=10)
            for child in children.get("results", []):
                if not child.get("has_children"):
                    continue

                # Go one level deeper
                grandchildren = notion.blocks.children.list(block_id=child["id"], page_size=100)
                blocks_list   = grandchildren.get("results", [])

                # Detect if this is structured notes (contains heading_3) vs raw transcript (all paragraphs)
                has_headings = any(b.get("type") == "heading_3" for b in blocks_list)
                if not has_headings:
                    continue  # skip raw transcript

                for b in blocks_list:
                    btype = b.get("type")
                    btext = rich_to_text(b.get(btype, {}).get("rich_text", []))

                    if btype == "heading_3" and btext:
                        content.append(f"\n**{btext}**")
                    elif btype == "bulleted_list_item" and btext:
                        content.append(f"- {btext}")
                    elif btype == "to_do" and btext:
                        done   = b.get("to_do", {}).get("checked", False)
                        prefix = "- [x]" if done else "- [ ]"
                        content.append(f"{prefix} {btext}")
                    elif btype == "paragraph" and btext:
                        content.append(btext)
            break  # only process first transcription block

    except Exception as e:
        pass

    return title, "\n".join(content)


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

        raw_title = "".join([t.get("plain_text", "") for t in props.get("Title", {}).get("title", [])])
        if raw_title.startswith("📋 TEMPLATE"):
            skipped += 1
            continue

        # Fetch full content (title + structured notes)
        trans_title, notes_content = get_meeting_content(notion, page["id"])
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
        if notes_content:
            lines.append(notes_content)
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
