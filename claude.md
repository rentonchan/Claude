# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repo uses the **B.L.A.S.T. protocol** (Blueprint → Link → Architect → Stylize → Trigger) and **A.N.T. 3-layer architecture** (Architecture / Navigation / Tools) to build deterministic Python automation tools.

The top-level repo is a **framework scaffold**. `Project 1/` is a concrete implementation (local Flask website served at `http://localhost:5000`).

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Verify shared utilities (self-test with JSON round-trip)
python tools/utils.py

# Run Project 1 (Flask local site — once implemented)
cd "Project 1"
pip install -r requirements.txt
python app.py   # serves at http://localhost:5000
```

## Architecture

### A.N.T. Layers

| Layer | Directory | Purpose |
|-------|-----------|---------|
| 1 — Architecture | `architecture/` | Markdown SOPs — one per tool, describing goal/input/output/steps/edge cases/error history |
| 2 — Navigation | *(future)* | Orchestration layer, not yet implemented |
| 3 — Tools | `tools/` | Atomic Python scripts; deterministic, standalone-runnable |

### Key Files

- **`claude.md`** (this file) — Project Constitution. Defines schemas, integrations, and behavioral rules. Treat as LAW; only update when schemas change.
- **`tools/utils.py`** — Shared utilities: logging (`blast` logger), `require_env()`, `save_json()` / `load_json()` (writes to `.tmp/`), `now_iso()`, `tmp_path()`.
- **`.tmp/`** — Ephemeral workbench for intermediate JSON files and logs (gitignored).

### Invariants

1. **Data-First:** Confirm the JSON schema in this file before writing any tool.
2. **SOP before code:** When logic changes, update `architecture/<tool>_sop.md` first, then the script.
3. **Self-Annealing:** Every error must result in an update to the relevant SOP (`architecture/`).
4. **Deterministic tools:** Same input → same output; scripts exit `0` on success, non-zero on failure.
5. **`.env` is sacred:** All credentials via `python-dotenv`; `require_env(key)` raises clearly if missing.

### B.L.A.S.T. Phases

1. **Blueprint** — Scaffold structure, define schemas in `claude.md`
2. **Link** — Populate `.env`, verify external connectivity
3. **Architect** — Write SOPs in `architecture/`, implement `tools/` scripts
4. **Stylize** — Format outputs, build UI if needed
5. **Trigger** — Deploy to production, set up automation

Each `Project N/` subdirectory follows the same structure and has its own `claude.md` constitution.

---

# Project Constitution
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

## 📐 Data Schema

> **Status: UNDEFINED** — Schema will be defined once Discovery Questions are answered.

### Input Payload
```json
// TBD after Discovery
```

### Output Payload
```json
// TBD after Discovery
```

---

## 📜 Behavioral Rules

> **Status: UNDEFINED** — Rules will be populated after Discovery.

| Rule | Description |
|------|-------------|
| TBD  | TBD         |

---

## 🔌 Integrations

> **Status: UNDEFINED** — Integrations will be listed after Discovery.

| Service | Purpose | Key Status |
|---------|---------|------------|
| TBD     | TBD     | TBD        |

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
