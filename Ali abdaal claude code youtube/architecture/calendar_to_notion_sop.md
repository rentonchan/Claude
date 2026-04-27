# SOP: Calendar → Notion Daily Brief

## Goal
Each morning, fetch today's and tomorrow's Google Calendar events from all calendars and create a "Daily Brief" sub-page inside Renton's Daily Agenda Planner in Notion.

## Input
- Google Calendar: 4 calendars (primary, HK public holidays, birthdays, family)
- Timezone: Asia/Hong_Kong

## Output
A new Notion sub-page titled "📅 Daily Brief — D Mon YYYY" created under:
- Page: Renton's Daily Agenda Planner
- Page ID: 2187181b-0f40-8015-8e41-d752899e9aed

Page structure:
- ☀️ Today — [date] (heading)
  - Bulleted list of events (HH:MM – HH:MM  Event Name, or 📌 All day  Event Name)
- Divider
- 🌙 Tomorrow — [date] (heading)
  - Bulleted list of events

## Calendar IDs
| Calendar | ID |
|----------|-----|
| Primary | rentonchan@gmail.com |
| HK Public Holidays | zh-tw.hong_kong#holiday@group.v.calendar.google.com |
| Birthdays | 6f7ef1de68264677ba377ec90ede8cad560d6466ddbef258e8fa1ee91927d5b4@group.calendar.google.com |
| Family | family15902092864072555763@group.calendar.google.com |

## Steps
1. Load `NOTION_TOKEN` from `.env`
2. Authenticate with Google Calendar via OAuth 2.0
   - Token is cached in `.tmp/token.pickle` after first run
   - On first run: browser opens for Google authorization
3. Fetch all events for today (midnight → 23:59) from all 4 calendar IDs
4. Fetch all events for tomorrow (midnight → 23:59) from all 4 calendar IDs
5. Sort each day's events by start time
6. Build Notion block structure (headings + bullets)
7. Create new Notion page as child of the planner page

## Edge Cases
- All-day events (holidays, birthdays) use `date` field, not `dateTime` — display as "📌 All day"
- If a calendar is inaccessible, skip it silently and continue
- If no events found for a day, display "No events scheduled."
- Duplicate events across calendars are not deduplicated (acceptable)

## Credentials Required
| Credential | Source | Stored In |
|-----------|--------|-----------|
| NOTION_TOKEN | notion.so/my-integrations | .env |
| Google OAuth | Google Cloud Console | credentials.json (first run only) |

## Error History
_None yet — update this section when errors are encountered._
