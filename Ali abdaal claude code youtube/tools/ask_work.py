#!/usr/bin/env python3
"""
Query your work meeting knowledge base using Claude or Gemini.
Usage: python tools/ask_work.py "What were the action items from my meetings with Arvind?"
       python tools/ask_work.py   (interactive mode)
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY")
NOTES_FILE    = os.path.join(os.path.dirname(__file__), "..", "knowledge", "meeting_notes.md")
FILE_ID_PATH  = os.path.join(os.path.dirname(__file__), "..", "knowledge", ".file_id")

SYSTEM_PROMPT = """You are Renton Chan's personal work assistant. You have access to his meeting notes
from his role in enterprise IT sales in Hong Kong. Answer questions about his meetings,
colleagues, deals, action items, and work context clearly and concisely.
If you can't find specific information in the notes, say so honestly."""


def load_notes() -> tuple[str, str | None]:
    """Returns (notes_text, file_id_if_available)."""
    notes = ""
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, encoding="utf-8") as f:
            notes = f.read()

    file_id = None
    if os.path.exists(FILE_ID_PATH):
        with open(FILE_ID_PATH) as f:
            file_id = f.read().strip()

    return notes, file_id


def ask_claude(question: str, notes: str, file_id: str | None) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Use Files API if we have a file_id, otherwise inline the text
    if file_id:
        content = [
            {"type": "document", "source": {"type": "file", "file_id": file_id}},
            {"type": "text", "text": question},
        ]
        response = client.beta.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            betas=["files-api-2025-04-14"],
        )
    else:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"{notes}\n\n---\n\n{question}"}],
        )
    return response.content[0].text


def ask_gemini(question: str, notes: str) -> str:
    from google import genai
    client   = genai.Client(api_key=GEMINI_KEY)
    prompt   = f"{SYSTEM_PROMPT}\n\nMeeting notes:\n{notes}\n\n---\n\nQuestion: {question}"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text


def answer(question: str) -> str:
    notes, file_id = load_notes()
    if not notes:
        return "No meeting notes found. Run: python tools/sync_meeting_knowledge.py"

    if ANTHROPIC_KEY:
        try:
            return ask_claude(question, notes, file_id)
        except Exception as e:
            err = str(e).lower()
            if any(w in err for w in ["credit", "authentication", "invalid x-api-key", "401", "400"]):
                print("  (Claude unavailable — trying Gemini)")
            else:
                raise

    if GEMINI_KEY:
        try:
            return ask_gemini(question, notes)
        except Exception as e:
            print(f"  (Gemini unavailable: {type(e).__name__})")

    # Final fallback: return the raw notes so the user can paste into claude.ai
    snippet = "\n".join(notes.split("\n")[:60])
    return (
        "⚠️  No AI API has credits/quota right now.\n\n"
        "You can paste your meeting notes directly into claude.ai:\n"
        f"  File location: knowledge/meeting_notes.md\n\n"
        f"--- First 60 lines of your notes ---\n{snippet}"
    )


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(answer(question))
    else:
        print("Work Meeting Assistant — type your question (Ctrl+C to exit)\n")
        while True:
            try:
                question = input("You: ").strip()
                if not question:
                    continue
                print(f"\nClaude: {answer(question)}\n")
            except (KeyboardInterrupt, EOFError):
                print("\nBye!")
                break


if __name__ == "__main__":
    main()
