#!/bin/bash
# Renton's Morning Automation — runs daily at 7:03am HKT via crontab
# Logs to logs/ directory

DIR="/Users/rentonchan/Documents/Claude/Ali abdaal claude code youtube"
PYTHON="$DIR/.venv/bin/python"
LOG="$DIR/logs"
DATE=$(date '+%Y-%m-%d %H:%M HKT')

echo "===== Morning run: $DATE =====" >> "$LOG/morning.log"

echo "[1/4] Daily Brief..." >> "$LOG/morning.log"
"$PYTHON" "$DIR/tools/daily_brief.py" >> "$LOG/morning.log" 2>&1

echo "[2/4] Weekly View (Calendar + Tasks)..." >> "$LOG/morning.log"
"$PYTHON" "$DIR/tools/update_weekly_view.py" >> "$LOG/morning.log" 2>&1

echo "[3/4] News Radar..." >> "$LOG/morning.log"
"$PYTHON" "$DIR/tools/fetch_news.py" >> "$LOG/morning.log" 2>&1

echo "[4/4] Email Digest..." >> "$LOG/morning.log"
"$PYTHON" "$DIR/tools/fetch_email_actions.py" >> "$LOG/morning.log" 2>&1

echo "[5/5] Archive old briefs..." >> "$LOG/morning.log"
"$PYTHON" "$DIR/tools/archive_old_briefs.py" >> "$LOG/morning.log" 2>&1

echo "===== Done =====" >> "$LOG/morning.log"
