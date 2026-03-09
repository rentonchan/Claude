# tools/ — Layer 3: Deterministic Python Engines

This directory contains atomic, testable Python scripts. Each script is:
- **Atomic** — does one thing and does it well
- **Deterministic** — same input always produces same output
- **Testable** — can be run standalone with `python tools/tool_name.py`
- **Secret-free** — all credentials come from `.env` via `python-dotenv`

## Conventions

- All scripts load environment variables using `dotenv`:
  ```python
  from dotenv import load_dotenv
  load_dotenv()
  ```
- All temporary/intermediate output goes to `.tmp/`
- Scripts exit with code `0` on success, non-zero on failure
- Each script has a corresponding SOP in `architecture/`

---

> Tools are built during Phase 3: Architect, after Phase 2: Link verifies all connections.
