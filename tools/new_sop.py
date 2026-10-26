r"""Create a new SOP that runs on this code base.

    python tools\new_sop.py "Finance SOP" --port 8502
    python tools\new_sop.py "Field Operations SOP" --folder D:\SOPs\field --port 8503 --tagline "Blantyre depot"

It makes a content folder (modules.json, data, screenshots, branding.json) plus run_sop.bat and test_sop.bat.
Each SOP has its own progress, logs and backups. The code is shared, so a fix here reaches every SOP."""
import argparse
import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent


def starter_modules():
    return {"modules": [
        {"id": "start-here", "category": "Getting Started", "title": "Start here",
         "subtitle": "What this SOP is and how to use it", "icon": "",
         "blocks": [
             {"type": "paragraph", "text": "Replace this text with one or two sentences on what this SOP covers and who it is for."},
             {"type": "callout", "variant": "info", "title": "How to use it",
              "text": "Pick a module from the sidebar. Use the search box to find a step. Tick the checklists as you go; your progress is saved under your name."},
             {"type": "checklist", "id": "first-day", "title": "Your first day",
              "items": ["Enter your name in the sidebar", "Read the module called How to write a procedure",
                        "Open the Commands page and look around", "Tell your supervisor you have finished"]},
         ]},
        {"id": "how-to-write", "category": "Getting Started", "title": "How to write a procedure",
         "subtitle": "A model module that shows each kind of block. Delete it when you no longer need it.", "icon": "",
         "blocks": [
             {"type": "heading", "level": 2, "text": "Editing this SOP"},
             {"type": "paragraph", "text": "Open Settings in the sidebar and switch on Admin edit mode. Every block then gets a menu to edit, move or delete it, and each module gets an Add block button."},
             {"type": "callout", "variant": "warning", "title": "Warn before the risky step",
              "text": "Put a warning before any step that can cause damage or cannot be undone."},
             {"type": "heading", "level": 2, "text": "A step with a command"},
             {"type": "command", "title": "Example command", "language": "text", "code": "example-command --option value",
              "notes": "Say what the reader should see afterwards."},
             {"type": "table", "headers": ["Term", "Meaning"],
              "rows": [["SOP", "Standard operating procedure"], ["Module", "One topic in this SOP"]]},
             {"type": "checklist", "id": "how-to-write-check", "title": "Before you publish",
              "items": ["Each step says what to do and what you should see", "Warnings come before the risky step", "Someone else has followed it once"]},
             {"type": "quiz", "title": "Quick check", "items": [
                 {"question": "What should every step in a procedure tell the reader?",
                  "options": ["Only what to do", "What to do and what they should see afterwards", "Who wrote it"], "answer": 1,
                  "explain": "Seeing the expected result tells the reader they are on track."}]},
         ]},
    ]}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "sop"


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_bat(path, lines):
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")


def main():
    ap = argparse.ArgumentParser(description="Create a new SOP folder.")
    ap.add_argument("title", help='Name shown in the app, e.g. "Finance SOP"')
    ap.add_argument("--folder", help="Where to create it (default: a sops folder next to this app)")
    ap.add_argument("--port", type=int, default=8502, help="Port this SOP will run on (default 8502)")
    ap.add_argument("--tagline", default="", help="Short line under the title")
    ap.add_argument("--icon", default="📘", help="Browser tab icon")
    args = ap.parse_args()

    slug = slugify(args.title)
    folder = Path(args.folder) if args.folder else APP_DIR.parent / "sops" / slug
    folder = folder.resolve()
    if (folder / "modules.json").exists():
        sys.exit(f"{folder} already has a modules.json. Nothing was changed.")

    (folder / "data").mkdir(parents=True, exist_ok=True)
    (folder / "screenshots").mkdir(exist_ok=True)
    write_json(folder / "modules.json", starter_modules())
    write_json(folder / "branding.json", {
        "title": args.title, "tagline": args.tagline, "icon": args.icon,
        "welcome": f"Procedures and checklists for {args.title}.",
        "hide_pages": ["Practice Terminal", "Ticket Builder", "Templates", "Error Codes", "Scenarios"],
        "show_context": False})
    write_json(folder / "data" / "learning_paths.json", {"paths": [
        {"id": "getting-started", "title": "Getting started", "description": "Follow these in order.",
         "estimated_minutes": 15, "modules": ["start-here", "how-to-write"]}]})
    for name, empty in (("error_codes", {"entries": []}), ("troubleshooting", {"problems": []}), ("templates", {"templates": []}),
                        ("scenarios", {"scenarios": []}), ("command_responses", {"responses": {}})):
        write_json(folder / "data" / f"{name}.json", empty)

    app = str(APP_DIR)
    write_bat(folder / "run_sop.bat", [
        "@echo off", f'set "SOP_HOME={folder}"', f'cd /d "{app}"',
        "if exist venv\\Scripts\\activate.bat call venv\\Scripts\\activate.bat",
        "rem Optional: lock Admin Edit Mode with a password (remove rem and set your own)",
        "rem set PS_SOP_ADMIN_PASSWORD=choose-a-password",
        f"streamlit run app.py --server.address 0.0.0.0 --server.port {args.port} --server.headless true", "pause"])
    write_bat(folder / "test_sop.bat", [
        "@echo off", f'set "SOP_HOME={folder}"', f'cd /d "{app}"',
        "if exist venv\\Scripts\\activate.bat call venv\\Scripts\\activate.bat",
        "python tests\\smoke_test.py", "pause"])

    print(f"Created {folder}")
    print(f"  1. Double-click {folder / 'run_sop.bat'}  (opens on port {args.port})")
    print("  2. Switch on Admin edit mode in Settings and replace the starter text")
    print("  3. To show a page again, remove it from hide_pages in branding.json")


if __name__ == "__main__":
    main()
