#!/usr/bin/env python3
"""Enriches Meeting Notes DB: renames timestamp pages using transcription titles and infers Type."""

import os
import re
from dotenv import load_dotenv
from notion_client import Client as NotionClient

load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
MEETING_NOTES_DB_ID = "34d7181b-0f40-8191-8e63-e880c90e8556"
TEMPLATE_PAGE_TITLE = "📋 TEMPLATE"

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

TYPE_RULES = [
    (["1-on-1", "1on1", "one on one", "one-on-one", "status meeting"], "1-on-1"),
    (["team", "standup", "stand-up", "all hands", "wog", "management", "group"], "Team"),
    (["client", "external", "vendor", "partner", "cisco", "resales", "maeva"], "External"),
]


def infer_type(title: str) -> str | None:
    lower = title.lower()
    for keywords, meeting_type in TYPE_RULES:
        if any(k in lower for k in keywords):
            return meeting_type
    return None


def get_transcription_title(notion: NotionClient, page_id: str) -> str | None:
    try:
        children = notion.blocks.children.list(block_id=page_id, page_size=10)
        for block in children.get("results", []):
            if block.get("type") == "transcription":
                rich = block.get("transcription", {}).get("title", [])
                parts = [t.get("plain_text", "") for t in rich if t.get("plain_text", "").strip()]
                title = " ".join(parts).strip()
                return title if title else None
    except Exception as e:
        print(f"  Warning: could not read blocks for {page_id}: {e}")
    return None


def update_page(notion: NotionClient, page_id: str, title: str, meeting_type: str | None):
    props: dict = {
        "Title": {"title": [{"text": {"content": title}}]}
    }
    if meeting_type:
        props["Type"] = {"select": {"name": meeting_type}}
    notion.pages.update(page_id=page_id, properties=props)


def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set in .env")

    notion = NotionClient(auth=NOTION_TOKEN)

    print("Querying Meeting Notes database...")
    results = notion.databases.query(database_id=MEETING_NOTES_DB_ID, page_size=100)
    pages = results.get("results", [])
    print(f"Found {len(pages)} pages\n")

    updated = 0
    skipped = 0

    for page in pages:
        page_id = page["id"]
        props = page.get("properties", {})
        current_title = "".join(
            [t.get("plain_text", "") for t in props.get("Title", {}).get("title", [])]
        )

        # Skip template and already-named pages
        if current_title.startswith(TEMPLATE_PAGE_TITLE):
            continue

        has_timestamp_title = TIMESTAMP_RE.match(current_title)
        current_type = (props.get("Type", {}).get("select") or {}).get("name")

        needs_rename = bool(has_timestamp_title)
        needs_type = not current_type

        if not needs_rename and not needs_type:
            skipped += 1
            continue

        print(f"Processing: {current_title[:60]}")

        new_title = current_title
        if needs_rename:
            transcription_title = get_transcription_title(notion, page_id)
            if transcription_title:
                new_title = transcription_title
                print(f"  Renamed → {new_title}")
            else:
                print(f"  No transcription title found, keeping as-is")

        inferred_type = infer_type(new_title) if needs_type else None
        if inferred_type:
            print(f"  Type → {inferred_type}")

        update_page(notion, page_id, new_title, inferred_type)
        updated += 1

    print(f"\n✅ Done. Updated: {updated} | Already complete: {skipped}")


if __name__ == "__main__":
    main()
