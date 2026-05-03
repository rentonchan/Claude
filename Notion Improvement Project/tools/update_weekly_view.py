#!/usr/bin/env python3
"""
Updates the 🗓️ This Week section on Renton's Daily Agenda Planner.
Renders a 7-column table — one box per day — showing calendar events and Google Tasks.
Runs daily at 7:03am HKT via crontab (inside run_morning.sh).
"""

import os
import pickle
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from notion_client import Client as NotionClient
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

NOTION_TOKEN    = os.environ.get("NOTION_TOKEN")
WEEK_HEADING_ID = "cfa3c9d3-a418-4697-9c71-7023332ab252"
WEEK_CALLOUT_ID = "fca8b0d4-7d7d-4404-80bc-5d6c8dbb0e90"

TIMEZONE   = "Asia/Hong_Kong"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "token.pickle")
CREDS_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
SCOPES     = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]
CALENDAR_IDS = [
    "rentonchan@gmail.com",
    "zh-tw.hong_kong#holiday@group.v.calendar.google.com",
    "6f7ef1de68264677ba377ec90ede8cad560d6466ddbef258e8fa1ee91927d5b4@group.calendar.google.com",
    "family15902092864072555763@group.calendar.google.com",
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


# ── Data fetchers ─────────────────────────────────────────────────────────────

def fetch_week_events(cal_service, monday: datetime) -> dict:
    tz     = ZoneInfo(TIMEZONE)
    week   = {(monday + timedelta(days=i)).date(): [] for i in range(7)}
    sunday = monday + timedelta(days=6)
    start  = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=tz)
    end    = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, tzinfo=tz)

    for cal_id in CALENDAR_IDS:
        try:
            result = cal_service.events().list(
                calendarId=cal_id,
                timeMin=start.isoformat(), timeMax=end.isoformat(),
                singleEvents=True, orderBy="startTime",
            ).execute()
            for event in result.get("items", []):
                summary = event.get("summary", "Untitled")
                estart  = event.get("start", {})
                if "dateTime" in estart:
                    s   = datetime.fromisoformat(estart["dateTime"])
                    txt = f"🕐 {s.strftime('%H:%M')}  {summary}"
                    key = s.date()
                else:
                    txt = f"📌 {summary}"
                    key = date.fromisoformat(estart["date"])
                if key in week and txt not in week[key]:
                    week[key].append(txt)
        except Exception as e:
            print(f"  Skip calendar {cal_id[:25]}: {e}")
    return week


def fetch_week_tasks(task_service, monday: datetime) -> dict:
    tz     = ZoneInfo(TIMEZONE)
    week   = {(monday + timedelta(days=i)).date(): [] for i in range(7)}
    sunday = monday + timedelta(days=6)
    due_min = datetime(monday.year, monday.month, monday.day, tzinfo=tz).isoformat()
    due_max = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, tzinfo=tz).isoformat()
    try:
        lists = task_service.tasklists().list(maxResults=10).execute()
        for tl in lists.get("items", []):
            tasks = task_service.tasks().list(
                tasklist=tl["id"],
                dueMin=due_min, dueMax=due_max,
                showCompleted=False, showHidden=False,
            ).execute()
            for task in tasks.get("items", []):
                if task.get("status") == "completed":
                    continue
                title = task.get("title", "").strip()
                due   = task.get("due", "")
                if title and due:
                    try:
                        d = date.fromisoformat(due[:10])
                        if d in week:
                            week[d].append(f"☑  {title}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"  Google Tasks: {e} (skipping)")
    return week


# ── Table builder ─────────────────────────────────────────────────────────────

def cell(text: str, bold: bool = False, color: str = "default") -> list:
    """A single table cell = list of rich_text objects."""
    ann = {
        "bold": bold, "italic": False, "strikethrough": False,
        "underline": False, "code": False, "color": color,
    }
    return [{"type": "text", "text": {"content": text}, "annotations": ann}]


def table_row(cells: list) -> dict:
    return {"object": "block", "type": "table_row", "table_row": {"cells": cells}}


def build_week_table(days: list, cal_week: dict, task_week: dict) -> dict:
    tz    = ZoneInfo(TIMEZONE)
    today = datetime.now(tz).date()

    # ── Header row ────────────────────────────────────────────────────────────
    header_cells = []
    for d in days:
        is_today = d.date() == today
        label    = d.strftime("%a %-d %b")
        if is_today:
            label = f"▸ {label}"
        header_cells.append(cell(label, bold=True, color="blue" if is_today else "default"))

    # ── Content: merge events + tasks per day, one item per row ───────────────
    day_content = []
    for d in days:
        items = sorted(cal_week.get(d.date(), [])) + task_week.get(d.date(), [])
        day_content.append(items if items else ["—"])

    max_rows = max(len(c) for c in day_content)

    content_rows = []
    for row_idx in range(max_rows):
        row_cells = []
        for col_idx in range(7):
            col = day_content[col_idx]
            text = col[row_idx] if row_idx < len(col) else ""
            is_today = days[col_idx].date() == today
            color    = "default" if text else "default"
            if text == "—":
                color = "gray"
            row_cells.append(cell(text, color=color))
        content_rows.append(table_row(row_cells))

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 7,
            "has_column_header": True,
            "has_row_header": False,
            "children": [table_row(header_cells)] + content_rows,
        },
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set")

    tz    = ZoneInfo(TIMEZONE)
    today = datetime.now(tz)

    # Weekends → show NEXT week so you always see what's ahead
    if today.weekday() >= 5:
        monday = today + timedelta(days=(7 - today.weekday()))
    else:
        monday = today - timedelta(days=today.weekday())

    days       = [monday + timedelta(days=i) for i in range(7)]
    week_label = f"{days[0].strftime('%-d %b')} – {days[-1].strftime('%-d %b %Y')}"
    refresh_at = today.strftime("%-d %b %Y, %H:%M HKT")

    print(f"Updating weekly grid: {week_label}")

    creds       = get_credentials()
    cal_service = build("calendar", "v3", credentials=creds)

    task_service = None
    try:
        task_service = build("tasks", "v1", credentials=creds)
        print("  Google Tasks: connected ✅")
    except Exception:
        print("  Google Tasks: not available")

    print("  Fetching calendar events...")
    cal_week  = fetch_week_events(cal_service, monday)

    task_week = {d.date(): [] for d in days}
    if task_service:
        print("  Fetching Google Tasks...")
        task_week = fetch_week_tasks(task_service, monday)

    notion = NotionClient(auth=NOTION_TOKEN)

    # Update heading label
    notion.blocks.update(
        block_id=WEEK_HEADING_ID,
        **{"heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"🗓️  This Week — {week_label}"}}],
            "color": "default",
        }},
    )

    # Update callout to show refresh time only (table lives inside it)
    notion.blocks.update(
        block_id=WEEK_CALLOUT_ID,
        **{"callout": {
            "icon": {"type": "emoji", "emoji": "🗓️"},
            "rich_text": [{"type": "text", "text": {
                "content": f"Updated {refresh_at}  ·  🕐 = calendar event   ☑ = Google Task   📌 = all day"
            }}],
            "color": "gray_background",
        }},
    )

    # Delete all old children from callout (previous table / toggles)
    old = notion.blocks.children.list(block_id=WEEK_CALLOUT_ID)
    for block in old.get("results", []):
        notion.blocks.delete(block_id=block["id"])

    # Build and append the 7-column table inside the callout
    week_table = build_week_table(days, cal_week, task_week)
    notion.blocks.children.append(block_id=WEEK_CALLOUT_ID, children=[week_table])

    total_events = sum(len(v) for v in cal_week.values())
    total_tasks  = sum(len(v) for v in task_week.values())
    print(f"✅ Weekly grid updated — {total_events} events, {total_tasks} tasks  ({week_label})")


if __name__ == "__main__":
    main()
