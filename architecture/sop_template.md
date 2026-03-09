# SOP Template: [Tool Name]
> Copy this file and rename it to match the tool (e.g., `fetch_data_sop.md`)

---

## 1. Goal
> What does this tool accomplish in one sentence?

## 2. Input
```json
// Paste the Input schema from claude.md here
```

## 3. Output
```json
// Paste the Output schema from claude.md here
```

## 4. Steps
1. Load environment variables via `dotenv`
2. [Step 2]
3. [Step 3]
4. Write intermediate result to `.tmp/[filename].json`
5. Return/deliver final payload

## 5. Edge Cases
| Scenario | Handling |
|----------|----------|
| API timeout | Retry up to 3 times with exponential backoff |
| Empty response | Log a warning and exit with code 1 |
| Missing env var | `require_env()` raises `EnvironmentError` with clear message |
| [TBD]    | [TBD]    |

## 6. Error History
> Append errors here as they are encountered (Self-Annealing log)

| Date | Error | Root Cause | Fix Applied |
|------|-------|------------|-------------|
| —    | —     | —          | —           |
