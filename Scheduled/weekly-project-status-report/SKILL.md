---
name: weekly-project-status-report
description: Generate a weekly status report across Apex Nexus, Chicago Marathon, and Accenture workstreams from Notion + Gmail, then publish it to the "Weekly Review" Notion page.
---

Generate a Weekly Project Status Report across three active workstreams and publish it to a designated Notion page.

## Objective
Produce a concise, well-structured weekly status report for the user (rentonchan@gmail.com) covering the past 7 days of activity across three workstreams:
1. **Apex Nexus** — side business development
2. **Chicago Marathon** — training and race preparation
3. **Accenture** — complex deal work

The report is appended/posted to a Notion page titled exactly **"Weekly Review"**.

## Steps

### 1. Determine the reporting window
- Use today's date as the report date.
- The reporting window is the trailing 7 days, ending today (Friday). Note the date range explicitly in the report header (e.g. "Week of <Mon date> – <Fri date>").

### 2. Gather inputs from Notion
Use the Notion MCP tools (notion-search, notion-fetch, notion-get-comments) to gather context for each workstream:
- Run `notion-search` with queries for each workstream name: "Apex Nexus", "Chicago Marathon" (also try "marathon", "training"), "Accenture" (also try active deal codenames if discoverable).
- For each match, fetch pages updated within the last 7 days using `notion-fetch`. Look at page properties, status fields, checkboxes, and recent edits.
- Pull task databases, project trackers, and meeting notes related to each workstream. Identify items marked Done/Completed, In Progress, Blocked, or Overdue.
- Capture comments and @mentions from the past week that signal blockers or decisions.

### 3. Gather inputs from Gmail
Use the Gmail MCP tools (search_threads, get_thread) to find correspondence from the past 7 days for each workstream. Suggested searches (use `newer_than:7d` and combine with workstream keywords):
- Apex Nexus: `newer_than:7d (subject:"Apex Nexus" OR "Apex Nexus")`
- Chicago Marathon: `newer_than:7d (marathon OR Chicago OR coach OR training)`
- Accenture: `newer_than:7d (Accenture OR deal OR proposal OR SOW OR MSA)`

For each thread, extract: decisions made, commitments, blockers raised, and action items assigned to the user.

### 4. Synthesize the report
For each of the three workstreams, produce four short sections:
- **Completed this week** — concrete shipped/finished items with brief context
- **In progress** — what's actively being worked on with current state
- **Blocked or overdue** — items stalled, waiting on someone, or past due, with the blocker named
- **Top priorities for next week** — 2–3 highest-leverage actions, action-oriented and specific

Keep each bullet to one or two lines. Cite the source briefly where useful (e.g. "(Notion: Apex Roadmap)" or "(Gmail: thread w/ Sarah, Tue)").

If there is little to no signal for a workstream in the past week, say so explicitly rather than padding.

### 5. Format the report
Use this structure:

```
# Weekly Review — Week of <Mon DD> – <Fri DD>, <YYYY>

## Apex Nexus
**Completed this week**
- ...
**In progress**
- ...
**Blocked / overdue**
- ...
**Top priorities next week**
1. ...
2. ...

## Chicago Marathon
(same four subsections)

## Accenture
(same four subsections)

## Cross-cutting notes
- Anything spanning multiple workstreams, conflicts, or trade-offs to flag
```

### 6. Publish to the Notion "Weekly Review" page
- Use `notion-search` to locate the page titled exactly **"Weekly Review"**.
- If the page exists: append a new section dated for this week to the top of the page (most recent on top). Use `notion-update-page` (or `notion-fetch` then update) to add the new content as a new H1 or H2 dated header followed by the report body. Do not delete prior weeks.
- If the page does NOT exist: create it under the user's workspace using `notion-create-pages`, then add this week's report as the first entry. Notify the user in the run output that the page was newly created.
- Verify the post succeeded by re-fetching the page and confirming the new section is present.

### 7. Output summary in this run
After publishing, output a short confirmation in the run that includes:
- Link to the Notion "Weekly Review" page
- The date range covered
- A 3–5 line TL;DR (one line per workstream + any cross-cutting flag)

## Constraints and preferences
- Tone: clear, professional, no fluff. Bullet points; minimal prose.
- Be honest about gaps: if a workstream has no signal, say so — don't fabricate progress.
- Do not include sensitive deal terms (specific contract values, internal pricing) in plaintext — summarize at a level appropriate for a personal weekly review.
- Prefer concrete verbs and outcomes ("Signed term sheet with X", "Hit 22 mile long run") over vague status ("worked on...").
- Never delete or overwrite prior weeks' entries on the Weekly Review page.

## Success criteria
- A new dated section for this week is visible on the Notion "Weekly Review" page.
- All three workstreams are covered with the four required subsections each.
- Top priorities for next week are concrete and actionable (not generic).
- The run output contains a link to the Notion page and a TL;DR.