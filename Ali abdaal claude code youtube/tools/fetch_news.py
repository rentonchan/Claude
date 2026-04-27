#!/usr/bin/env python3
"""
Fetches top headlines from RSS feeds and refreshes the News Radar
toggle on Renton's Daily Agenda Planner page.

Sources: SCMP (HK), BBC Asia/China, Ars Technica (Tech), BBC Business
Runs daily at 7:05am HKT alongside the Daily Brief.
"""

import os
import feedparser
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from notion_client import Client as NotionClient

load_dotenv()

NOTION_TOKEN     = os.environ.get("NOTION_TOKEN")
HOME_PAGE_ID     = "2187181b-0f40-8015-8e41-d752899e9aed"
NEWS_TOGGLE_ID   = "34d7181b-0f40-81c2-acb7-cecf461f06b7"  # News Radar toggle
NEWS_HEADING_ID  = "34d7181b-0f40-819c-8279-fdc077e08413"  # "📰 News Radar" h2

FEEDS = [
    {
        "label": "🇭🇰  HK",
        "url":   "https://www.scmp.com/rss/2/feed",
        "count": 3,
    },
    {
        "label": "🌏  Asia",
        "url":   "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "count": 2,
    },
    {
        "label": "💼  Tech",
        "url":   "https://feeds.arstechnica.com/arstechnica/index",
        "count": 2,
    },
    {
        "label": "📈  Business",
        "url":   "https://feeds.bbci.co.uk/news/business/rss.xml",
        "count": 2,
    },
]


def fetch_headlines() -> list[dict]:
    """Returns list of {label, title, link} dicts."""
    headlines = []
    for feed_cfg in FEEDS:
        try:
            parsed = feedparser.parse(feed_cfg["url"])
            entries = parsed.get("entries", [])
            seen_titles = {h["title"] for h in headlines}
            count = 0
            for entry in entries:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "")
                if title and title not in seen_titles:
                    headlines.append({
                        "label": feed_cfg["label"],
                        "title": title,
                        "link":  link,
                    })
                    seen_titles.add(title)
                    count += 1
                    if count >= feed_cfg["count"]:
                        break
        except Exception as e:
            print(f"  Warning: could not fetch {feed_cfg['label']}: {e}")
    return headlines


def make_bullet(item: dict) -> dict:
    text = f"{item['label']}   {item['title']}"
    rich = [{"type": "text", "text": {"content": text}}]
    if item["link"]:
        rich = [{
            "type": "text",
            "text": {"content": text, "link": {"url": item["link"]}},
        }]
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich},
    }


def main():
    if not NOTION_TOKEN:
        raise SystemExit("ERROR: NOTION_TOKEN not set in .env")

    notion = NotionClient(auth=NOTION_TOKEN)
    tz     = ZoneInfo("Asia/Hong_Kong")
    now    = datetime.now(tz)
    label  = now.strftime("%-d %b %Y, %H:%M HKT")

    print("Fetching headlines...")
    headlines = fetch_headlines()
    print(f"  {len(headlines)} headlines across {len(FEEDS)} feeds")

    # Delete old bullets from the toggle
    old = notion.blocks.children.list(block_id=NEWS_TOGGLE_ID)
    for block in old.get("results", []):
        notion.blocks.delete(block_id=block["id"])

    # Append fresh bullets
    bullets = [make_bullet(h) for h in headlines]
    if bullets:
        notion.blocks.children.append(block_id=NEWS_TOGGLE_ID, children=bullets)

    # Update toggle label to show refresh time
    notion.blocks.update(
        block_id=NEWS_TOGGLE_ID,
        **{
            "toggle": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Latest auto-refresh — {label}"},
                }]
            }
        }
    )

    print(f"✅ News Radar updated — {label}")
    for h in headlines:
        print(f"  {h['label']}  {h['title'][:65]}")


if __name__ == "__main__":
    main()
