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

SYSTEM_PROMPT = """You are Renton Chan's personal work assistant based in Hong Kong.
You have full access to his meeting notes from his enterprise IT sales role.
Answer questions about his meetings, colleagues, deals, action items, and work context.
Be concise and specific. Reference meeting dates and people when relevant."""

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
    """Return cached notes, refresh if older than 6 hours."""
    if not _cache["notes"] or time.time() - _cache["updated"] > 21600:
        print("Refreshing meeting notes from Notion...")
        notes = fetch_notes_from_notion()
        if notes:
            _cache["notes"]   = notes
            _cache["updated"] = time.time()
            print(f"  Loaded {len(notes):,} chars of meeting notes")
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
    client   = genai.Client(api_key=GEMINI_KEY)
    prompt   = f"{SYSTEM_PROMPT}\n\nMeeting notes:\n{notes}\n\nQuestion: {question}"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Work Chat — Renton</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:#f0f2f5;height:100dvh;display:flex;flex-direction:column}
  header{background:#1a1a2e;color:#fff;padding:14px 20px;
         display:flex;align-items:center;gap:12px;flex-shrink:0}
  header h1{font-size:17px;font-weight:600}
  header p{font-size:12px;opacity:.55;margin-top:2px}
  #chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px}
  .msg{max-width:82%;padding:12px 15px;border-radius:14px;line-height:1.6;font-size:15px;white-space:pre-wrap}
  .user{align-self:flex-end;background:#1a1a2e;color:#fff;border-bottom-right-radius:4px}
  .ai{align-self:flex-start;background:#fff;color:#1a1a2e;border-bottom-left-radius:4px;
      box-shadow:0 1px 3px rgba(0,0,0,.08)}
  .ai .lbl{font-size:11px;color:#888;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
  .error{background:#fff3cd;color:#856404}
  .thinking{opacity:.45;font-style:italic}
  .chips{padding:0 20px 10px;display:flex;gap:8px;flex-wrap:wrap;flex-shrink:0}
  .chip{background:#fff;border:1px solid #ddd;border-radius:20px;padding:6px 14px;
        font-size:13px;cursor:pointer;color:#444;transition:all .15s}
  .chip:hover{border-color:#1a1a2e;color:#1a1a2e}
  footer{background:#fff;padding:12px 16px;border-top:1px solid #e5e5e5;
         display:flex;gap:10px;flex-shrink:0}
  footer input{flex:1;padding:11px 16px;border:1.5px solid #ddd;border-radius:24px;
               font-size:15px;outline:none;background:#f8f8f8}
  footer input:focus{border-color:#1a1a2e;background:#fff}
  footer button{background:#1a1a2e;color:#fff;border:none;border-radius:24px;
                padding:11px 22px;font-size:15px;cursor:pointer;font-weight:500}
  footer button:active{opacity:.85}
  @media(max-width:600px){.msg{max-width:95%}}
</style>
</head>
<body>
<header>
  <div style="font-size:24px">🏢</div>
  <div>
    <h1>Work Chat</h1>
    <p>Renton's meeting knowledge · updated daily from Notion</p>
  </div>
</header>

<div id="chat">
  <div class="msg ai">
    <div class="lbl">Assistant</div>Hi Renton! Ask me anything about your meetings, deals, colleagues, or action items.
  </div>
</div>

<div class="chips" id="chips">
  <div class="chip" onclick="ask(this.innerText)">What meetings did I have this week?</div>
  <div class="chip" onclick="ask(this.innerText)">Which action items are still open?</div>
  <div class="chip" onclick="ask(this.innerText)">Summarise meetings with Arvind</div>
  <div class="chip" onclick="ask(this.innerText)">What deals are in progress?</div>
  <div class="chip" onclick="ask(this.innerText)">Who have I met most recently?</div>
</div>

<footer>
  <input id="q" placeholder="Ask about your work meetings..."
         onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}">
  <button onclick="send()">Send</button>
</footer>

<script>
const chat=document.getElementById('chat');
const chips=document.getElementById('chips');
function ask(t){document.getElementById('q').value=t;send()}
function send(){
  const q=document.getElementById('q');
  const question=q.value.trim();
  if(!question)return;
  q.value='';
  chips.style.display='none';
  addMsg(question,'user');
  const t=addMsg('Thinking…','ai thinking');
  fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question})})
  .then(r=>r.json()).then(d=>{
    t.remove();
    const m=document.createElement('div');
    m.className='msg ai'+(d.type==='error'?' error':'');
    m.innerHTML='<div class="lbl">'+(d.model||'Assistant')+'</div>'+
      d.answer.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
    chat.appendChild(m);chat.scrollTop=chat.scrollHeight;
  });
}
function addMsg(text,cls){
  const m=document.createElement('div');
  m.className='msg '+cls;
  m.textContent=text;
  chat.appendChild(m);chat.scrollTop=chat.scrollHeight;
  return m;
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
