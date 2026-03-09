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
