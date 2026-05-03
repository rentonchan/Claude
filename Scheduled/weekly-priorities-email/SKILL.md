---
name: weekly-priorities-email
description: Every Monday at 9am, pull the user's calendar for the week and draft a weekly priorities email.
---

Objective: Pull Renton's calendar for the upcoming week and draft a weekly priorities email summarizing key meetings, focus areas, and action items.

Steps:

1. Determine the date range for the current week (today through the upcoming Sunday). Use bash `date` if needed to confirm today's date.

2. Pull calendar events for the week:
   - Use the Google Calendar connector tool `mcp__36d20d2f-54a8-4ece-a1ee-2624df9556a1__list_events` to retrieve all events from today through the end of Sunday.
   - If multiple calendars exist, call `mcp__36d20d2f-54a8-4ece-a1ee-2624df9556a1__list_calendars` first to identify the primary calendar.
   - Capture event titles, times, attendees, locations/links, and descriptions.

3. Analyze the week's calendar and identify:
   - Key meetings (1:1s, customer/external meetings, leadership reviews, decision meetings)
   - Recurring meetings vs. one-off meetings
   - Days with heavy meeting load vs. focus-time blocks
   - Any meetings requiring prep work or pre-reads
   - Conflicts or back-to-back stretches worth flagging

4. Draft a weekly priorities email. Save it as a Gmail draft using `mcp__f6218981-a205-4678-a2db-502a19aa3f99__create_draft` addressed to rentonchan@gmail.com (a self-note).
   - Subject: "Weekly Priorities — Week of [Monday Date]"
   - Structure the body as:
     * Top 3-5 priorities for the week (inferred from the most important meetings/themes)
     * Day-by-day overview of key meetings (Mon-Fri), in concise bullet form
     * Prep work needed (meetings that need pre-reads, decisions to make, materials to prepare)
     * Focus time available (gaps for deep work)
     * Heads-up flags (conflicts, back-to-backs, travel, anything unusual)
   - Keep tone direct and action-oriented; this is a self-note for planning the week.

5. Confirm the draft was created and report:
   - Total meetings for the week
   - Number of focus-time blocks (>= 90 min)
   - Subject line of the draft
   - Brief summary of the top priorities identified

Constraints:
- Do not send the email — only create a draft.
- If the calendar tool is unavailable or returns no events, still create a draft email noting that the calendar could not be pulled, and suggest the user check connector status.
- Keep the draft email concise — aim for something Renton can scan in under 2 minutes.