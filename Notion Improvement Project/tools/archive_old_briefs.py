#!/usr/bin/env python3
"""
Archives (soft-deletes) Daily Brief pages older than 7 days from the Daily Briefs folder.
Archived pages move to Notion trash — still recoverable, just off your screen.
Runs daily at 7:10am HKT (after the new brief is created).
"""

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from notion_client import Client as NotionClient

load_dotenv()

NOTION_TOKEN        = os.environ.get("NOTION_TOKEN")
DAILY_BRIEFS_FOLDER = "34d7181b-0f40-8179-b542-ce63b30616c1"
CUTOFF_DAYS         = 7


def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set")

    notion  = NotionClient(auth=NOTION_TOKEN)
    cutoff  = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
    archived = 0

    print(f"Scanning Daily Briefs older than {CUTOFF_DAYS} days...")
    children = notion.blocks.children.list(block_id=DAILY_BRIEFS_FOLDER, page_size=100)

    for block in children.get("results", []):
        if block.get("type") != "child_page":
            continue

        page_id      = block["id"]
        created_time = block.get("created_time", "")

        try:
            created_dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        except Exception:
            continue

        if created_dt >= cutoff:
            continue

        page  = notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        title = "".join([t.get("plain_text", "") for t in props.get("title", {}).get("title", [])])

        print(f"  Archiving: {title} (created {created_time[:10]})")
        notion.pages.update(page_id=page_id, archived=True)
        archived += 1

    print(f"\n✅ Done. Archived {archived} old Daily Brief(s).")


if __name__ == "__main__":
    main()
