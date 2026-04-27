#!/usr/bin/env python3
"""Fetches today's and tomorrow's Google Calendar events and creates a Daily Brief in Notion."""

import os
import pickle
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from notion_client import Client as NotionClient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

TIMEZONE = "Asia/Hong_Kong"
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_PARENT_PAGE_ID = "2187181b-0f40-8015-8e41-d752899e9aed"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "token.pickle")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CALENDAR_IDS = [
    "rentonchan@gmail.com",
    "zh-tw.hong_kong#holiday@group.v.calendar.google.com",
    "6f7ef1de68264677ba377ec90ede8cad560d6466ddbef258e8fa1ee91927d5b4@group.calendar.google.com",
    "family15902092864072555763@group.calendar.google.com",
]


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("calendar", "v3", credentials=creds)


def fetch_events_for_day(service, day: datetime) -> list:
    tz = ZoneInfo(TIMEZONE)
    start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=tz)

    events = []
    for cal_id in CALENDAR_IDS:
        try:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events.extend(result.get("items", []))
        except Exception as e:
            print(f"  Skipping calendar {cal_id}: {e}")

    events.sort(key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")))
    return events


def format_event_text(event: dict) -> str:
    summary = event.get("summary", "Untitled")
    start = event.get("start", {})

    if "dateTime" in start:
        start_dt = datetime.fromisoformat(start["dateTime"])
        end_dt = datetime.fromisoformat(event["end"]["dateTime"])
        return f"🕐 {start_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}   {summary}"
    else:
        return f"📌 All day   {summary}"


def make_heading(text: str, color: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }


def make_bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def make_paragraph(text: str, color: str = "default") -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": text}, "annotations": {"color": color}}
            ]
        },
    }


def build_blocks(today_events: list, tomorrow_events: list, today: datetime, tomorrow: datetime) -> list:
    blocks = []

    today_label = today.strftime("%A, %-d %B %Y")
    blocks.append(make_heading(f"☀️ Today — {today_label}", "yellow_background"))

    if today_events:
        for event in today_events:
            blocks.append(make_bullet(format_event_text(event)))
    else:
        blocks.append(make_paragraph("No events scheduled.", "gray"))

    blocks.append({"object": "block", "type": "divider", "divider": {}})

    tomorrow_label = tomorrow.strftime("%A, %-d %B %Y")
    blocks.append(make_heading(f"🌙 Tomorrow — {tomorrow_label}", "blue_background"))

    if tomorrow_events:
        for event in tomorrow_events:
            blocks.append(make_bullet(format_event_text(event)))
    else:
        blocks.append(make_paragraph("No events scheduled.", "gray"))

    return blocks


def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not found in .env — see .env.example")

    tz = ZoneInfo(TIMEZONE)
    today = datetime.now(tz)
    tomorrow = today + timedelta(days=1)

    print("Connecting to Google Calendar...")
    service = get_calendar_service()

    print("Fetching today's events...")
    today_events = fetch_events_for_day(service, today)
    print(f"  Found {len(today_events)} event(s)")

    print("Fetching tomorrow's events...")
    tomorrow_events = fetch_events_for_day(service, tomorrow)
    print(f"  Found {len(tomorrow_events)} event(s)")

    print("Creating Notion Daily Brief...")
    notion = NotionClient(auth=NOTION_TOKEN)
    title = f"📅 Daily Brief — {today.strftime('%-d %b %Y')}"
    blocks = build_blocks(today_events, tomorrow_events, today, tomorrow)

    page = notion.pages.create(
        parent={"page_id": NOTION_PARENT_PAGE_ID},
        properties={"title": [{"text": {"content": title}}]},
        children=blocks,
    )

    print(f"\n✅ Done! Open your Daily Brief here:\n   {page['url']}")


if __name__ == "__main__":
    main()
