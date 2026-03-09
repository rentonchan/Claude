# architecture/ — Layer 1: Standard Operating Procedures (SOPs)

This directory contains Markdown SOPs for every tool in the `tools/` layer.

## Golden Rule
> If logic changes, **update the SOP first**, then update the code.

## SOP File Naming Convention
Each SOP should mirror its corresponding tool:

| Tool | SOP |
|------|-----|
| `tools/tool_name.py` | `architecture/tool_name_sop.md` |

## SOP Template

Each SOP must include:
1. **Goal** — What does this tool do?
2. **Input** — What data does it receive? (reference schema in `claude.md`)
3. **Output** — What data does it return/write?
4. **Steps** — Step-by-step logic
5. **Edge Cases** — Known failure modes and how to handle them
6. **Error History** — Append errors encountered and fixes applied (Self-Annealing)

---

> SOPs are populated during Phase 3: Architect
