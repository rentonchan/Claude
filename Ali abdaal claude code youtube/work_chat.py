#!/usr/bin/env python3
"""
Renton's Work Chat — cloud-deployable web interface.
Fetches meeting notes from Notion directly on startup and caches them.
Queries Claude or Gemini for answers.

Run locally: python work_chat.py  →  http://localhost:5001
Deploy:      Railway / Render (set env vars — no file dependencies)
"""

import os
import time
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN  = os.environ.get("NOTION_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY")
MEETING_DB_ID = "34d7181b-0f40-8191-8e63-e880c90e8556"
PORT          = int(os.environ.get("PORT", 5001))
NOTES_FILE    = os.path.join(os.path.dirname(__file__), "knowledge", "meeting_notes.md")

SYSTEM_PROMPT = """You are Renton Chan's personal work assistant based in Hong Kong.
You have full access to his meeting notes from his enterprise IT sales role.
Answer questions thoroughly and in detail — include all relevant action items,
discussion points, decisions, and context from the notes.
Reference meeting dates and people when relevant. Do not truncate your answers."""

app = Flask(__name__)

# In-memory cache: refreshed at startup and every 6 hours
_cache = {"notes": "", "updated": 0}


def fetch_notes_from_notion() -> str:
    """Pull all meeting notes from Notion and compile to text."""
    if not NOTION_TOKEN:
        return ""
    try:
        from notion_client import Client
        notion   = Client(auth=NOTION_TOKEN)
        meetings = []
        cursor   = None
        while True:
            kwargs = {
                "database_id": MEETING_DB_ID,
                "sorts": [{"property": "Date", "direction": "descending"}],
                "page_size": 100,
            }
            if cursor:
                kwargs["start_cursor"] = cursor
            result = notion.databases.query(**kwargs)
            meetings.extend(result.get("results", []))
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")

        lines = [
            "# Renton's Work Meeting Notes",
            f"_(fetched live from Notion — {len(meetings)} meetings)_\n",
        ]
        for p in meetings:
            props     = p["properties"]
            raw_title = "".join([t.get("plain_text", "") for t in props.get("Title", {}).get("title", [])])
            if raw_title.startswith("📋 TEMPLATE"):
                continue
            date_val  = (props.get("Date", {}).get("date") or {}).get("start", "")
            date_str  = date_val[:10] if date_val else "unknown"
            mtype     = (props.get("Type", {}).get("select") or {}).get("name", "")
            attendees = [a["name"] for a in props.get("Attendees", {}).get("multi_select", [])]
            summary   = "".join([t.get("plain_text", "") for t in props.get("Summary", {}).get("rich_text", [])])
            done      = props.get("Action Items Done", {}).get("checkbox", False)

            # Get transcription title
            trans_title = ""
            try:
                blocks = notion.blocks.children.list(block_id=p["id"], page_size=3)
                for b in blocks.get("results", []):
                    if b.get("type") == "transcription":
                        rich = b.get("transcription", {}).get("title", [])
                        trans_title = " ".join([t.get("plain_text", "") for t in rich]).strip()
                        break
            except Exception:
                pass

            title = trans_title or raw_title
            meta  = []
            if mtype:     meta.append(f"Type: {mtype}")
            if attendees: meta.append(f"Attendees: {', '.join(attendees)}")
            meta.append(f"Actions done: {'Yes' if done else 'No'}")

            lines.append(f"### {date_str} — {title}")
            lines.append("  |  ".join(meta))
            if summary:
                lines.append(f"Summary: {summary}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        print(f"Notion fetch error: {e}")
        return ""


def get_notes() -> str:
    """Return full meeting notes. Reads from file (rich content), falls back to Notion."""
    if not _cache["notes"] or time.time() - _cache["updated"] > 21600:
        # Prefer the pre-built file which has full transcript content
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, encoding="utf-8") as f:
                notes = f.read()
            print(f"  Loaded from file: {len(notes):,} chars")
        else:
            print("  File not found, fetching from Notion...")
            notes = fetch_notes_from_notion()

        if notes:
            _cache["notes"]   = notes
            _cache["updated"] = time.time()
    return _cache["notes"]


def ask_claude(question: str, notes: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    r = client.messages.create(
        model="claude-haiku-4-5", max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"{notes}\n\n---\n\n{question}"}],
    )
    return r.content[0].text


def ask_gemini(question: str, notes: str) -> str:
    from google import genai
    from google.genai import types
    client   = genai.Client(api_key=GEMINI_KEY)
    prompt   = f"{SYSTEM_PROMPT}\n\nMeeting notes:\n{notes}\n\nQuestion: {question}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=4000),
    )
    return response.text


def get_answer(question: str) -> tuple[str, str]:
    notes = get_notes()
    if not notes:
        return "⚠️ Could not load meeting notes from Notion. Check NOTION_TOKEN.", "error"

    if ANTHROPIC_KEY:
        try:
            return ask_claude(question, notes), "claude"
        except Exception as e:
            err = str(e).lower()
            if not any(w in err for w in ["credit", "auth", "401", "400"]):
                raise
            print(f"Claude unavailable: {err[:60]}")

    if GEMINI_KEY:
        try:
            return ask_gemini(question, notes), "gemini"
        except Exception as e:
            print(f"Gemini unavailable: {e}")

    return "⚠️ No AI credits available. Add credits to Anthropic (console.anthropic.com/billing) or enable Gemini billing.", "error"


# ── Web UI ────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Work Chat</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  html { height: 100%; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f0f2f5;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  /* ── Header ── */
  header {
    background: #1a1a2e;
    color: #fff;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }
  header h1  { font-size: 17px; font-weight: 600; }
  header p   { font-size: 12px; opacity: 0.5; margin-top: 2px; }

  /* ── Chat area ── */
  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .bubble-wrap { display: flex; flex-direction: column; }
  .bubble-wrap.user { align-items: flex-end; }
  .bubble-wrap.ai   { align-items: flex-start; }

  .lbl {
    font-size: 10px;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
    padding: 0 4px;
  }

  .msg {
    max-width: min(80%, 560px);
    padding: 12px 16px;
    border-radius: 18px;
    line-height: 1.6;
    font-size: 15px;
    word-break: break-word;
  }
  .bubble-wrap.user .msg {
    background: #1a1a2e;
    color: #fff;
    border-bottom-right-radius: 4px;
  }
  .bubble-wrap.ai .msg {
    background: #fff;
    color: #111;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .bubble-wrap.ai .msg.error { background: #fff3cd; color: #856404; }
  .bubble-wrap.ai .msg.thinking { background: #f5f5f5; color: #888; font-style: italic; }

  /* Markdown inside AI messages */
  .msg p   { margin-bottom: 8px; }
  .msg p:last-child { margin-bottom: 0; }
  .msg ul, .msg ol { padding-left: 20px; margin-bottom: 8px; }
  .msg li  { margin-bottom: 4px; }
  .msg strong { font-weight: 600; }
  .msg em { font-style: italic; }
  .msg code { background: #f0f0f0; padding: 1px 5px; border-radius: 4px; font-size: 13px; }

  /* ── Suggestion chips ── */
  .chips {
    padding: 0 16px 12px;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    flex-shrink: 0;
    scrollbar-width: none;
  }
  .chips::-webkit-scrollbar { display: none; }
  .chip {
    white-space: nowrap;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 20px;
    padding: 7px 15px;
    font-size: 13px;
    cursor: pointer;
    color: #444;
    flex-shrink: 0;
    transition: border-color 0.15s, color 0.15s;
  }
  .chip:hover  { border-color: #1a1a2e; color: #1a1a2e; }
  .chip:active { background: #f5f5f5; }

  /* ── Footer input ── */
  footer {
    background: #fff;
    border-top: 1px solid #e8e8e8;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  footer input {
    flex: 1;
    padding: 11px 18px;
    border: 1.5px solid #e0e0e0;
    border-radius: 24px;
    font-size: 15px;
    outline: none;
    background: #f8f8f8;
    transition: border-color 0.15s, background 0.15s;
  }
  footer input:focus { border-color: #1a1a2e; background: #fff; }
  footer button {
    background: #1a1a2e;
    color: #fff;
    border: none;
    border-radius: 50%;
    width: 44px;
    height: 44px;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: opacity 0.15s;
  }
  footer button:hover  { opacity: 0.85; }
  footer button:active { opacity: 0.7; }

  /* ── Wide screen ── */
  @media (min-width: 700px) {
    #chat   { padding: 24px calc(50% - 330px); }
    footer  { padding: 14px calc(50% - 330px); }
    .chips  { padding: 0 calc(50% - 330px) 12px; }
  }
</style>
</head>
<body>

<header>
  <span style="font-size:24px">🏢</span>
  <div>
    <h1>Work Chat</h1>
    <p>Renton's meeting knowledge · updated daily from Notion</p>
  </div>
</header>

<div id="chat">
  <div class="bubble-wrap ai">
    <div class="lbl">Assistant</div>
    <div class="msg">Hi Renton! Ask me anything about your meetings, deals, colleagues, or action items.</div>
  </div>
</div>

<div class="chips" id="chips">
  <div class="chip" onclick="ask(this.innerText)">This week's meetings</div>
  <div class="chip" onclick="ask(this.innerText)">Open action items</div>
  <div class="chip" onclick="ask(this.innerText)">Meetings with Arvind</div>
  <div class="chip" onclick="ask(this.innerText)">Deals in progress</div>
  <div class="chip" onclick="ask(this.innerText)">Most recent meetings</div>
  <div class="chip" onclick="ask(this.innerText)">Key decisions made</div>
</div>

<footer>
  <input id="q" placeholder="Ask about your work meetings…" autocomplete="off"
         onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}">
  <button onclick="send()" aria-label="Send">&#10148;</button>
</footer>

<script>
const chat  = document.getElementById('chat');
const chips = document.getElementById('chips');

marked.setOptions({ breaks: true, gfm: true });

function ask(text) {
  document.getElementById('q').value = text;
  send();
}

function send() {
  const q        = document.getElementById('q');
  const question = q.value.trim();
  if (!question) return;
  q.value = '';
  chips.style.display = 'none';

  addBubble(question, 'user');
  const thinking = addBubble('Thinking…', 'ai', 'thinking');

  fetch('/ask', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ question }),
  })
  .then(r => r.json())
  .then(d => {
    thinking.remove();
    const wrap = document.createElement('div');
    wrap.className = 'bubble-wrap ai';
    const lbl = document.createElement('div');
    lbl.className = 'lbl';
    lbl.textContent = d.model || 'Assistant';
    const msg = document.createElement('div');
    msg.className = 'msg' + (d.type === 'error' ? ' error' : '');
    msg.innerHTML = marked.parse(d.answer || '');
    wrap.appendChild(lbl);
    wrap.appendChild(msg);
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  });
}

function addBubble(text, side, extraClass) {
  const wrap = document.createElement('div');
  wrap.className = 'bubble-wrap ' + side;
  if (side === 'ai') {
    const lbl = document.createElement('div');
    lbl.className = 'lbl';
    lbl.textContent = 'Assistant';
    wrap.appendChild(lbl);
  }
  const msg = document.createElement('div');
  msg.className = 'msg' + (extraClass ? ' ' + extraClass : '');
  msg.textContent = text;
  wrap.appendChild(msg);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return wrap;
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/ask", methods=["POST"])
def ask_route():
    question = (request.json or {}).get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please ask a question.", "type": "error"})
    answer, source = get_answer(question)
    label = {"claude": "Claude Haiku", "gemini": "Gemini Flash", "error": "⚠️ Error"}.get(source, source)
    return jsonify({"answer": answer, "model": label, "type": source})


@app.route("/refresh", methods=["POST"])
def refresh():
    _cache["updated"] = 0
    get_notes()
    return jsonify({"ok": True, "chars": len(_cache["notes"])})


if __name__ == "__main__":
    print(f"Work Chat starting on http://localhost:{PORT}")
    get_notes()  # pre-load on startup
    app.run(host="0.0.0.0", port=PORT, debug=False)
