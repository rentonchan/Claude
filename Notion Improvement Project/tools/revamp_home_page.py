#!/usr/bin/env python3
"""
One-time script to revamp Renton's Daily Agenda Planner home page.
Clears old clutter, adds: command centre, weekly habit tracker,
active projects, vault links, and a daily brief guide callout.
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from notion_client import Client as NotionClient

load_dotenv()

NOTION_TOKEN   = os.environ.get("NOTION_TOKEN")
HOME_PAGE_ID   = "2187181b-0f40-8015-8e41-d752899e9aed"

DB = {
    "meeting_notes": "34d7181b-0f40-8191-8e63-e880c90e8556",
    "projects":      "2187181b-0f40-81d5-afbc-ddc2798397f5",
    "tasks":         "2187181b-0f40-818d-9d08-f98029386e45",
    "reading":       "5e22b105-ae9b-40ad-afd6-0d91b3cb8a8a",
    "make_time":     "2187181b-0f40-8198-8496-c3750fef8a48",
}

# Blocks to DELETE (old clutter — layout, headings, to_dos, empty paragraphs)
# child_database and child_page blocks are intentionally preserved
BLOCKS_TO_DELETE = [
    "2187181b-0f40-812c-b0ad-ccd439c731f2",  # embed
    "2187181b-0f40-81e1-94cc-e1121644e133",  # column_list (old layout)
    "2187181b-0f40-8101-98f9-e88937d395b9",  # paragraph (empty)
    "2187181b-0f40-81f8-8d14-d84846c88773",  # heading "☀ Daily Tasks"
    "2187181b-0f40-81f5-ada7-e67e4939939b",  # unsupported (old Notion AI widget)
    "2297181b-0f40-8041-8387-cbd22b595527",  # to_do Make Time
    "2297181b-0f40-8089-90fd-f743271a86cc",  # to_do To-do
    "2297181b-0f40-80c9-af1a-c6c38fb7268f",  # to_do Exercise
    "2297181b-0f40-8032-af11-f4c13d47b195",  # to_do Read 1 page
    "2297181b-0f40-80f6-bdd0-d2499fdabe7d",  # to_do Meditate
    "2187181b-0f40-81b9-b462-e3d4907c3003",  # heading "😴 For Tomorrow"
    "21b7181b-0f40-80a1-8eda-e4a8f7e7899a",  # paragraph (empty)
    "2187181b-0f40-81c4-b9cc-da6de4a16fd9",  # heading "🗄️ The Vault"
    "2187181b-0f40-8129-99f9-f44c0ebd2497",  # column_list (old layout)
    "2187181b-0f40-8146-86cb-ef96dc535363",  # divider
    "21b7181b-0f40-809e-9bbb-c42eefce6293",  # heading "Tasks"
    "2187181b-0f40-810b-bdb5-f2997f116ee0",  # paragraph (empty)
    "2187181b-0f40-8100-b471-d018c24a08b3",  # divider
    "2187181b-0f40-81cf-beba-e6059b64d937",  # paragraph "Jeff's Daily Agenda..."
    "2187181b-0f40-805e-b0f0-ca32746859aa",  # paragraph (empty)
    "2187181b-0f40-80dc-aaed-f8986f1ac34e",  # paragraph (empty)
    "2187181b-0f40-805a-9def-c142fbcc414d",  # heading "Knowledge"
    "2247181b-0f40-807c-84b6-e7f118161d3f",  # paragraph (empty)
]


# ─────────────────────────────────────────────
# Block helpers
# ─────────────────────────────────────────────

def divider():
    return {"object": "block", "type": "divider", "divider": {}}

def h2(text, color="default"):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": color}}

def h3(text, color="default"):
    return {"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": color}}

def paragraph(text, color="default"):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text},
                                          "annotations": {"color": color}}]}}

def bullet(text, color="default"):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text},
                                                  "annotations": {"color": color}}]}}

def todo(text, checked=False):
    return {"object": "block", "type": "to_do",
            "to_do": {"rich_text": [{"type": "text", "text": {"content": text}}], "checked": checked}}

def callout(text, emoji="💡", color="blue_background"):
    return {"object": "block", "type": "callout",
            "callout": {"icon": {"type": "emoji", "emoji": emoji},
                        "rich_text": [{"type": "text", "text": {"content": text}}],
                        "color": color}}

def toggle(text, children, color="default"):
    return {"object": "block", "type": "toggle",
            "toggle": {"rich_text": [{"type": "text", "text": {"content": text}}],
                       "color": color,
                       "children": children}}

def db_link(db_key):
    return {"type": "mention", "mention": {"type": "database", "database": {"id": DB[db_key]}}}

def page_link(page_id):
    return {"type": "mention", "mention": {"type": "page", "page": {"id": page_id}}}

def inline_row(*mentions):
    rich = []
    for i, m in enumerate(mentions):
        rich.append(m)
        if i < len(mentions) - 1:
            rich.append({"type": "text", "text": {"content": "     ·     "}})
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich}}


# ─────────────────────────────────────────────
# Data fetchers
# ─────────────────────────────────────────────

def get_active_projects(notion):
    try:
        res = notion.databases.query(
            database_id=DB["projects"],
            filter={"and": [
                {"property": "Status", "select": {"does_not_equal": "Done"}},
                {"property": "Archive", "checkbox": {"equals": False}},
            ]},
            page_size=10,
        )
        out = []
        for p in res["results"]:
            props = p["properties"]
            name   = "".join([t.get("plain_text","") for t in props.get("Name",{}).get("title",[])])
            status = (props.get("Status",{}).get("select") or {}).get("name","")
            if name:
                out.append((name, status, p["id"]))
        return out
    except Exception:
        return []


# ─────────────────────────────────────────────
# Build weekly habit blocks
# ─────────────────────────────────────────────

def week_days(reference: datetime) -> list:
    """Return Mon–Sun dates for the week containing reference."""
    tz    = reference.tzinfo
    # Find Monday of this week
    monday = reference - timedelta(days=reference.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def habit_toggle(habit_name: str, emoji: str, days: list) -> dict:
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    children = []
    for i, d in enumerate(days):
        label = f"{day_labels[i]}  {d.strftime('%-d %b')}"
        children.append(todo(label))
    return toggle(f"{emoji}  {habit_name}", children)


def build_habit_section(days: list) -> list:
    week_label = f"{days[0].strftime('%-d %b')} – {days[-1].strftime('%-d %b %Y')}"
    blocks = [
        h2(f"🔄 Daily Habits — Week of {week_label}", "green_background"),
        callout(
            "Check each habit off as you complete it. Reset every Monday when the cron refreshes this section.",
            "💡", "gray_background"
        ),
        habit_toggle("Make Time  (journal your highlight, grateful, let go)", "🌟", days),
        habit_toggle("Exercise", "🏃", days),
        habit_toggle("Read 1 Page", "📖", days),
        habit_toggle("Meditate 1 min", "🧘", days),
        habit_toggle("Clear To-do List", "✅", days),
    ]
    return blocks


# ─────────────────────────────────────────────
# Build full new content
# ─────────────────────────────────────────────

def build_new_content(notion, today: datetime) -> list:
    days    = week_days(today)
    projects = get_active_projects(notion)

    blocks = []

    # ── Hero callout ──────────────────────────────────────────
    blocks.append(callout(
        "🏠  Renton's Command Centre\n\n"
        "Your Daily Brief is auto-created at 7:03am HKT each morning — find today's in the list above ↑\n"
        "This page is your permanent hub: habits, projects, databases, and the vault all live here.",
        "🏠", "blue_background"
    ))
    blocks.append(divider())

    # ── Command Centre ────────────────────────────────────────
    blocks.append(h2("🔗 Command Centre", "gray_background"))
    blocks.append(inline_row(db_link("meeting_notes"), db_link("projects"), db_link("tasks")))
    blocks.append(inline_row(db_link("reading"), db_link("make_time")))
    blocks.append(divider())

    # ── Habit Tracker ─────────────────────────────────────────
    blocks.extend(build_habit_section(days))
    blocks.append(divider())

    # ── Active Projects ───────────────────────────────────────
    blocks.append(h2("📋 Active Projects"))
    if projects:
        for name, status, pid in projects:
            blocks.append(bullet(f"{name}   [{status}]"))
    else:
        blocks.append(paragraph("No active projects — add one to the Projects database.", "gray"))
    blocks.append(divider())

    # ── The Vault ─────────────────────────────────────────────
    blocks.append(h2("🗄️ The Vault"))
    blocks.append(paragraph("Knowledge, saved prompts, and reference material:"))
    blocks.append(inline_row(
        page_link("2187181b-0f40-80c9-bbe3-c8e42d74c007"),  # Website
        page_link("2187181b-0f40-804f-8f0e-e362ef2c0304"),  # Prompts
    ))
    blocks.append(divider())

    # ── System Guide ─────────────────────────────────────────
    blocks.append(h2("⚙️ How This System Works"))
    blocks.append(toggle("📖 Read this once", [
        paragraph("DAILY BRIEF (child pages above ↑)"),
        bullet("Auto-created each morning at 7:03am HKT"),
        bullet("Contains: weather + yesterday's highlight, Big 3 priorities, today's schedule, open loops from meetings, overdue tasks, active projects, reading status, tomorrow preview, quick capture, and evening reflection"),
        bullet("Open it first thing each morning — it is your day's navigation page"),
        paragraph(""),
        paragraph("MEETING NOTES DATABASE"),
        bullet("After Notion AI finishes recording → Move to Database → select Meeting Notes"),
        bullet("Fill in: Attendees, Type (1-on-1 / Team / External), 1-line Summary"),
        bullet("Check off 'Action Items Done' when follow-ups are complete"),
        paragraph(""),
        paragraph("HABITS (this page)"),
        bullet("Check off each habit daily in the toggles above"),
        bullet("Resets every Monday morning"),
        paragraph(""),
        paragraph("MAKE TIME DB"),
        bullet("Each evening: open Make Time DB → New entry → fill Highlight, Grateful, Let Go"),
        bullet("Your highlight from yesterday appears in the next morning's Daily Brief"),
    ]))

    return blocks


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set in .env")

    notion = NotionClient(auth=NOTION_TOKEN)
    tz     = ZoneInfo("Asia/Hong_Kong")
    today  = datetime.now(tz)

    # Step 1: Delete old clutter blocks
    print(f"Deleting {len(BLOCKS_TO_DELETE)} old blocks...")
    for i, block_id in enumerate(BLOCKS_TO_DELETE):
        try:
            notion.blocks.delete(block_id=block_id)
            print(f"  [{i+1}/{len(BLOCKS_TO_DELETE)}] deleted {block_id[:8]}...")
        except Exception as e:
            print(f"  [{i+1}/{len(BLOCKS_TO_DELETE)}] skipped {block_id[:8]} ({e})")

    # Step 2: Build and append new content
    print("\nBuilding new content...")
    blocks = build_new_content(notion, today)
    print(f"  {len(blocks)} blocks to append")

    # Append in batches of 95 (Notion API limit)
    for i in range(0, len(blocks), 95):
        batch = blocks[i:i+95]
        notion.blocks.children.append(block_id=HOME_PAGE_ID, children=batch)
        print(f"  Appended blocks {i+1}–{i+len(batch)}")

    print(f"\n✅ Home page revamped!")
    print(f"   https://www.notion.so/{HOME_PAGE_ID.replace('-','')}")


if __name__ == "__main__":
    main()
