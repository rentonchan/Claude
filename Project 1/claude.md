# claude.md — Project Constitution
> **This file is LAW.** Only update it when a schema changes, a rule is added, or architecture is modified.

---

## 🗺️ Project Map

- **Status:** 🟡 Discovery (Phase 1 — Blueprint not yet approved)
- **Protocol:** B.L.A.S.T. (Blueprint → Link → Architect → Stylize → Trigger)
- **Architecture:** A.N.T. 3-Layer (Architecture / Navigation / Tools)

---

## 📂 Directory Structure

```
├── claude.md          # Project Constitution (this file)
├── .env               # API Keys/Secrets (populated in Link phase)
├── architecture/      # Layer 1: SOPs in Markdown
├── tools/             # Layer 3: Deterministic Python scripts
└── .tmp/              # Ephemeral workbench (intermediates, logs, scraped data)
```

---

## 🧭 Discovery Answers

| Question | Answer |
|----------|--------|
| 🌟 North Star | Build and serve a website locally |
| 🔌 Integrations | None |
| 🗄️ Source of Truth | Local JSON files (`data/site_content.json`) |
| 📦 Delivery | `http://localhost:5000` in browser |
| 📋 Behavioral Rules | None |

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Web server | Flask (Python) |
| Templates | Jinja2 |
| Styling | Vanilla CSS |
| Data | Local JSON (`data/`) |
| Frontend JS | Vanilla JS |

---

## 📐 Data Schema

> **Status: DEFINED** ✅

### `data/site_content.json` — Source of Truth

```json
{
  "site": {
    "title": "string",
    "description": "string",
    "author": "string"
  },
  "nav": [
    { "label": "string", "href": "string" }
  ],
  "hero": {
    "headline": "string",
    "subheadline": "string",
    "cta_label": "string",
    "cta_href": "string"
  },
  "sections": [
    {
      "id": "string",
      "title": "string",
      "body": "string",
      "icon": "string"
    }
  ],
  "footer": {
    "text": "string"
  }
}
```

---

## 📜 Behavioral Rules

| Rule | Description |
|------|-------------|
| No external services | All data is local; no API keys required |
| JSON is the source of truth | Content changes go in `data/`, not in templates |
| Flask only serves locally | Target: `http://localhost:5000` |

---

## 🔌 Integrations

| Service | Purpose | Key Status |
|---------|---------|------------|
| None    | —       | —          |

---

## 🏛️ Architectural Invariants

1. **Data-First:** No tool is coded until the JSON schema is confirmed in this file.
2. **Deterministic Tools:** All `tools/` scripts are atomic, testable, and side-effect-free (except their declared output).
3. **Self-Annealing:** Every error encountered MUST result in an update to the relevant `architecture/` SOP.
4. **Payload Rule:** A project is only "Complete" when the payload reaches its final cloud destination.
5. **`.env` is sacred:** No secrets are hardcoded in any script.

---

## 🛠️ Maintenance Log

| Date | Change | Author |
|------|--------|--------|
| 2026-03-10 | Constitution initialized (Protocol 0) | System Pilot |
