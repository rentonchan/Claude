#!/usr/bin/env python3
"""
Runs every Monday at 7:01am HKT.
Resets the weekly habit tracker on the home page for the new week.
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from notion_client import Client as NotionClient

load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
HOME_PAGE_ID = "2187181b-0f40-8015-8e41-d752899e9aed"

HABIT_HEADING_ID = "34d7181b-0f40-8182-904b-d6aaa588d21f"
HABITS = [
    ("34d7181b-0f40-819a-8ece-da436b8b4fee", "🌟  Make Time  (Highlight · Grateful · Let Go)"),
    ("34d7181b-0f40-81dd-b063-fd29f918e8df", "🏃  Exercise"),
    ("34d7181b-0f40-81bf-976f-ed7e3a2a758c", "📖  Read 1 Page"),
    ("34d7181b-0f40-8135-98d2-e43a73328bbd", "🧘  Meditate 1 min"),
    ("c2e3d13d-5e53-4fb5-94bd-e3d49deb7608", "✅  Clear To-do List"),
]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def week_days(monday: datetime) -> list:
    return [monday + timedelta(days=i) for i in range(7)]


def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set")

    notion = NotionClient(auth=NOTION_TOKEN)
    tz     = ZoneInfo("Asia/Hong_Kong")
    today  = datetime.now(tz)

    # Find Monday of this week
    monday = today - timedelta(days=today.weekday())
    days   = week_days(monday)
    week_label = f"{days[0].strftime('%-d %b')} – {days[-1].strftime('%-d %b %Y')}"

    print(f"Resetting habits for week of {week_label}...")

    # Update the heading
    notion.blocks.update(
        block_id=HABIT_HEADING_ID,
        **{"heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"🔄  Daily Habits — Week of {week_label}"}}],
            "color": "green_background",
        }}
    )

    # Reset each habit toggle
    for toggle_id, label in HABITS:
        # Delete old to_do children
        old = notion.blocks.children.list(block_id=toggle_id)
        for block in old.get("results", []):
            notion.blocks.delete(block_id=block["id"])

        # Add fresh unchecked to_dos for each day
        new_todos = [
            {
                "object": "block", "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"{DAY_NAMES[i]}   {d.strftime('%-d %b')}"}}],
                    "checked": False,
                }
            }
            for i, d in enumerate(days)
        ]
        notion.blocks.children.append(block_id=toggle_id, children=new_todos)
        print(f"  Reset: {label}")

    print(f"✅ Habits reset for week of {week_label}")


if __name__ == "__main__":
    main()
