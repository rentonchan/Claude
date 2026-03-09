# Claude Automation Project

> Built with the **B.L.A.S.T.** protocol (Blueprint → Link → Architect → Stylize → Trigger)
> and the **A.N.T.** 3-layer architecture (Architecture / Navigation / Tools)

---

## 📂 Project Structure

```
├── claude.md              # Project Constitution (schemas, rules, invariants)
├── task_plan.md           # Phase checklist
├── findings.md            # Research log & constraints
├── progress.md            # Session-by-session execution log
├── .env                   # API secrets (NOT committed to git)
├── requirements.txt       # Python dependencies
│
├── architecture/          # Layer 1: SOPs (Markdown "how-to" for each tool)
│   ├── README.md
│   └── sop_template.md    # Template for new SOPs
│
├── tools/                 # Layer 3: Deterministic Python scripts
│   ├── README.md
│   └── utils.py           # Shared utilities (logging, env, JSON, paths)
│
└── .tmp/                  # Ephemeral workbench (gitignored)
```

---

## 🚀 Setup

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env .env.local   # Fill in your API keys
```

## ✅ Verify Utilities

```bash
python tools/utils.py
```

---

## 📖 Protocol

See `claude.md` for the full project constitution, data schemas, and behavioral rules.
