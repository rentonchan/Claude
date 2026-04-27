#!/usr/bin/env python3
"""
Daily Brief — Renton's Command Centre
Runs every morning at 7am HKT. Creates a full navigation + action page in Notion.

Sections:
  1. Morning Snapshot  — weather + yesterday's Make Time highlight
  2. North Star        — 3 empty priority checkboxes
  3. Today's Schedule  — Google Calendar + meeting note links
  4. Open Loops        — unchecked meeting actions + overdue/due tasks
  5. Active Projects   — in-progress projects from Projects DB
  6. Currently Reading — from Reading List
  7. Tomorrow Preview  — tomorrow's calendar
  8. Quick Capture     — toggle blocks for ideas and notes
  9. Command Centre    — links to all key databases
 10. Evening Reflection — pre-filled Make Time prompts
"""

import os
import pickle
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from notion_client import Client as NotionClient
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

TIMEZONE       = "Asia/Hong_Kong"
NOTION_TOKEN   = os.environ.get("NOTION_TOKEN")
PARENT_PAGE_ID = "34d7181b-0f40-8179-b542-ce63b30616c1"  # 📅 Daily Briefs folder
TOKEN_PATH     = os.path.join(os.path.dirname(__file__), "..", ".tmp", "token.pickle")
CREDS_PATH     = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
SCOPES         = ["https://www.googleapis.com/auth/calendar.readonly"]

CALENDAR_IDS = [
    "rentonchan@gmail.com",
    "zh-tw.hong_kong#holiday@group.v.calendar.google.com",
    "6f7ef1de68264677ba377ec90ede8cad560d6466ddbef258e8fa1ee91927d5b4@group.calendar.google.com",
    "family15902092864072555763@group.calendar.google.com",
]

DB = {
    "meeting_notes": "34d7181b-0f40-8191-8e63-e880c90e8556",
    "projects":      "2187181b-0f40-81d5-afbc-ddc2798397f5",
    "tasks":         "2187181b-0f40-818d-9d08-f98029386e45",
    "reading":       "5e22b105-ae9b-40ad-afd6-0d91b3cb8a8a",
    "make_time":     "2187181b-0f40-8198-8496-c3750fef8a48",
}

DB_LABELS = {
    "meeting_notes": "🗣️ Meeting Notes",
    "projects":      "📋 Projects",
    "tasks":         "✅ All Tasks",
    "reading":       "📚 Reading List",
    "make_time":     "🌟 Make Time",
}


# ─────────────────────────────────────────────
# Block helpers
# ─────────────────────────────────────────────

def divider():
    return {"object": "block", "type": "divider", "divider": {}}

def h2(text: str, color: str = "default"):
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }

def paragraph(text: str, color: str = "default"):
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}, "annotations": {"color": color}}],
        },
    }

def bullet(text: str, color: str = "default"):
    return {
        "object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}, "annotations": {"color": color}}],
        },
    }

def todo(text: str, checked: bool = False):
    return {
        "object": "block", "type": "to_do",
        "to_do": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "checked": checked,
        },
    }

def callout(text: str, emoji: str = "☀️", color: str = "yellow_background"):
    return {
        "object": "block", "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }

def toggle(text: str, children: list = None):
    block = {
        "object": "block", "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": "default",
        },
    }
    if children:
        block["toggle"]["children"] = children
    return block

def db_mention_row(db_keys: list):
    rich = []
    for i, key in enumerate(db_keys):
        rich.append({
            "type": "mention",
            "mention": {"type": "database", "database": {"id": DB[key]}},
        })
        if i < len(db_keys) - 1:
            rich.append({"type": "text", "text": {"content": "   ·   "}})
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": rich},
    }


# ─────────────────────────────────────────────
# Data fetchers
# ─────────────────────────────────────────────

def get_weather() -> str:
    try:
        r = requests.get("https://wttr.in/Hong+Kong?format=3", timeout=5)
        r.encoding = "utf-8"
        return r.text.strip()
    except Exception:
        return "Hong Kong: (weather unavailable)"


def get_yesterday_highlight(notion: NotionClient) -> str:
    try:
        res = notion.databases.query(
            database_id=DB["make_time"],
            sorts=[{"property": "Date", "direction": "descending"}],
            page_size=1,
        )
        if res["results"]:
            props = res["results"][0]["properties"]
            highlight = "".join([t.get("plain_text", "") for t in props.get("Highlight", {}).get("rich_text", [])])
            grateful  = "".join([t.get("plain_text", "") for t in props.get("Grateful", {}).get("rich_text", [])])
            day_date  = (props.get("Date", {}).get("date") or {}).get("start", "")
            return f"{highlight}  ·  Grateful: {grateful}  ({day_date})" if highlight else ""
    except Exception:
        pass
    return ""


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return build("calendar", "v3", credentials=creds)


def fetch_events(service, day: datetime) -> list:
    tz = ZoneInfo(TIMEZONE)
    start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    end   = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=tz)
    events = []
    for cal_id in CALENDAR_IDS:
        try:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=start.isoformat(), timeMax=end.isoformat(),
                singleEvents=True, orderBy="startTime",
            ).execute()
            events.extend(result.get("items", []))
        except Exception as e:
            print(f"  Skipping calendar {cal_id}: {e}")
    events.sort(key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")))
    return events


def format_event(event: dict) -> str:
    summary = event.get("summary", "Untitled")
    start   = event.get("start", {})
    if "dateTime" in start:
        s = datetime.fromisoformat(start["dateTime"])
        e = datetime.fromisoformat(event["end"]["dateTime"])
        return f"🕐 {s.strftime('%H:%M')} – {e.strftime('%H:%M')}   {summary}"
    return f"📌 All day   {summary}"


def get_open_action_items(notion: NotionClient) -> list:
    try:
        res = notion.databases.query(
            database_id=DB["meeting_notes"],
            filter={"property": "Action Items Done", "checkbox": {"equals": False}},
            sorts=[{"property": "Date", "direction": "descending"}],
            page_size=8,
        )
        items = []
        for p in res["results"]:
            props = p["properties"]
            title = "".join([t.get("plain_text", "") for t in props.get("Title", {}).get("title", [])])
            date_val = (props.get("Date", {}).get("date") or {}).get("start", "")
            date_str = date_val[:10] if date_val else "no date"
            if not title.startswith("📋 TEMPLATE"):
                items.append(f"{title}  ({date_str})")
        return items
    except Exception:
        return []


def get_todays_tasks(notion: NotionClient, today_str: str) -> list:
    try:
        res = notion.databases.query(
            database_id=DB["tasks"],
            filter={
                "and": [
                    {"property": "Done", "checkbox": {"equals": False}},
                    {"property": "Due", "date": {"on_or_before": today_str}},
                ]
            },
            sorts=[{"property": "Due", "direction": "ascending"}],
            page_size=10,
        )
        tasks = []
        for p in res["results"]:
            props = p["properties"]
            name = "".join([t.get("plain_text", "") for t in props.get("Task", {}).get("title", [])])
            due  = (props.get("Due", {}).get("date") or {}).get("start", "")
            prio = (props.get("Priority", {}).get("select") or {}).get("name", "")
            label = f"{name}"
            if due: label += f"  (due {due[:10]})"
            if prio: label += f"  [{prio}]"
            if name:
                tasks.append(label)
        return tasks
    except Exception:
        return []


def get_active_projects(notion: NotionClient) -> list:
    try:
        res = notion.databases.query(
            database_id=DB["projects"],
            filter={
                "and": [
                    {"property": "Status", "select": {"does_not_equal": "Done"}},
                    {"property": "Archive", "checkbox": {"equals": False}},
                ]
            },
            page_size=10,
        )
        projects = []
        for p in res["results"]:
            props  = p["properties"]
            name   = "".join([t.get("plain_text", "") for t in props.get("Name", {}).get("title", [])])
            status = (props.get("Status", {}).get("select") or {}).get("name", "")
            if name:
                projects.append(f"{name}  [{status}]")
        return projects
    except Exception:
        return []


def get_current_reading(notion: NotionClient) -> list:
    try:
        res = notion.databases.query(
            database_id=DB["reading"],
            page_size=20,
        )
        reading = []
        for p in res["results"]:
            props  = p["properties"]
            name   = "".join([t.get("plain_text", "") for t in props.get("Name", {}).get("title", [])])
            status = (props.get("Status", {}).get("select") or {}).get("name", "")
            rtype  = (props.get("Type", {}).get("select") or {}).get("name", "")
            completed = (props.get("Completed", {}).get("date") or {})
            if status and "read" in status.lower() and not completed:
                reading.append(f"{name}  ({rtype})")
        # fall back to most recently added without completion date
        if not reading:
            for p in res["results"][:3]:
                props = p["properties"]
                name  = "".join([t.get("plain_text", "") for t in props.get("Name", {}).get("title", [])])
                rtype = (props.get("Type", {}).get("select") or {}).get("name", "")
                completed = (props.get("Completed", {}).get("date") or {})
                if not completed and name:
                    reading.append(f"{name}  ({rtype})")
        return reading[:3]
    except Exception:
        return []


# ─────────────────────────────────────────────
# Block builders
# ─────────────────────────────────────────────

def build_morning_snapshot(weather: str, highlight: str) -> list:
    text = weather
    if highlight:
        text += f"\n✨ Yesterday: {highlight}"
    return [callout(text, "☀️", "yellow_background")]


def build_north_star() -> list:
    return [
        h2("🎯 North Star — Big 3 for Today", "orange_background"),
        todo(""),
        todo(""),
        todo(""),
        paragraph(""),
    ]


def build_schedule(events: list, label: str, color: str) -> list:
    blocks = [h2(label, color)]
    if events:
        for ev in events:
            blocks.append(bullet(format_event(ev)))
    else:
        blocks.append(paragraph("Nothing scheduled.", "gray"))
    return blocks


def build_open_loops(action_items: list, tasks: list) -> list:
    blocks = [h2("⚠️ Open Loops", "red_background")]

    blocks.append(paragraph("From meetings:", "red"))
    if action_items:
        for item in action_items:
            blocks.append(bullet(f"↩ {item}", "red"))
    else:
        blocks.append(paragraph("All clear.", "gray"))

    blocks.append(paragraph(""))
    blocks.append(paragraph("Tasks due today / overdue:", "orange"))
    if tasks:
        for task in tasks:
            blocks.append(todo(task))
    else:
        blocks.append(paragraph("Nothing due today.", "gray"))

    return blocks


def build_active_projects(projects: list) -> list:
    blocks = [h2("📋 Active Projects")]
    if projects:
        for proj in projects:
            blocks.append(bullet(proj))
    else:
        blocks.append(paragraph("No active projects.", "gray"))
    return blocks


def build_reading(books: list) -> list:
    blocks = [h2("📚 Currently Reading / Watching")]
    if books:
        for b in books:
            blocks.append(bullet(b))
    else:
        blocks.append(paragraph("Add something to your reading list.", "gray"))
    return blocks


def build_quick_capture() -> list:
    return [
        h2("💡 Quick Capture"),
        toggle("💭 Ideas", [paragraph(""), paragraph(""), paragraph("")]),
        toggle("📎 Notes & Info", [paragraph(""), paragraph(""), paragraph("")]),
        toggle("📬 Things to Follow Up", [paragraph(""), paragraph(""), paragraph("")]),
    ]


def build_command_centre() -> list:
    return [
        h2("🔗 Command Centre"),
        db_mention_row(["meeting_notes", "projects", "tasks"]),
        db_mention_row(["reading", "make_time"]),
    ]


def build_evening_reflection() -> list:
    return [
        h2("🌟 Evening Reflection (Make Time)", "purple_background"),
        paragraph("🙌 Highlight of the day:"),
        paragraph(""),
        paragraph("😁 Grateful for:"),
        paragraph(""),
        paragraph("💪 Let go of:"),
        paragraph(""),
    ]


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set in .env")

    tz      = ZoneInfo(TIMEZONE)
    today   = datetime.now(tz)
    tomorrow = today + timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")

    notion = NotionClient(auth=NOTION_TOKEN)

    print("Fetching data...")
    weather   = get_weather()
    highlight = get_yesterday_highlight(notion)
    print(f"  Weather: {weather}")
    print(f"  Highlight: {highlight or '(none)'}")

    print("Fetching Google Calendar events...")
    cal_service     = get_calendar_service()
    today_events    = fetch_events(cal_service, today)
    tomorrow_events = fetch_events(cal_service, tomorrow)
    print(f"  Today: {len(today_events)} event(s), Tomorrow: {len(tomorrow_events)} event(s)")

    print("Fetching Notion data...")
    action_items = get_open_action_items(notion)
    tasks        = get_todays_tasks(notion, today_str)
    projects     = get_active_projects(notion)
    reading      = get_current_reading(notion)
    print(f"  Open loops: {len(action_items)} meeting items, {len(tasks)} tasks")
    print(f"  Active projects: {len(projects)} | Reading: {len(reading)}")

    today_label    = today.strftime("%A, %-d %B %Y")
    tomorrow_label = tomorrow.strftime("%A, %-d %B")
    title          = f"📅 Daily Brief — {today_label}"

    # Build all blocks in order
    all_blocks = (
        build_morning_snapshot(weather, highlight)
        + [divider()]
        + build_north_star()
        + [divider()]
        + build_schedule(today_events, f"☀️ Today — {today_label}", "yellow_background")
        + [divider()]
        + build_open_loops(action_items, tasks)
        + [divider()]
        + build_active_projects(projects)
        + [divider()]
        + build_reading(reading)
        + [divider()]
        + build_schedule(tomorrow_events, f"🌙 Tomorrow — {tomorrow_label}", "blue_background")
        + [divider()]
        + build_quick_capture()
        + [divider()]
        + build_command_centre()
        + [divider()]
        + build_evening_reflection()
    )

    # Notion API: max 100 children per call — create page with first batch, append the rest
    print("Creating Daily Brief in Notion...")
    first_batch = all_blocks[:95]
    rest        = all_blocks[95:]

    page = notion.pages.create(
        parent={"page_id": PARENT_PAGE_ID},
        icon={"type": "emoji", "emoji": "📅"},
        properties={"title": [{"text": {"content": title}}]},
        children=first_batch,
    )
    page_id = page["id"]

    if rest:
        notion.blocks.children.append(block_id=page_id, children=rest)

    print(f"\n✅ Daily Brief ready:\n   {page['url']}")


if __name__ == "__main__":
    main()
