# utils.py
import datetime
import io
import json
import re
import shutil
import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from config import DATA_DIR, MODULES_PATH, PLACEHOLDER_KEYS, SCREENSHOTS_DIR, IMAGE_MAX_WIDTH, BACKUP_DIR

_PAT2KEY = {p: k for k, pats in PLACEHOLDER_KEYS.items() for p in pats}
_PAT_RE = re.compile("|".join(re.escape(p) for p in sorted(_PAT2KEY, key=len, reverse=True)))
_XX_RE = re.compile(r"[\w.]*xx[\w.]*", re.IGNORECASE)
CHANGE_RE = re.compile(r"^\s*(ADD|MOD|RMV|SET|ACT|DEA|LCK|ULK|RST|CLR)\b", re.MULTILINE)

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s or "operator")[:40] or "operator"

def substitute_placeholders(text, context):
    if not text or not context: return text
    def repl(m):
        value = (context.get(_PAT2KEY[m.group(0)]) or "").strip()
        return value or m.group(0)
    return _PAT_RE.sub(repl, text)

def find_unfilled(text):
    found = set(_PAT_RE.findall(text or ""))
    found.update(m for m in _XX_RE.findall(text or "") if m)
    return sorted(found)

def is_change_command(text):
    return bool(CHANGE_RE.search(text or ""))

def load_json(path, default):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except Exception: return default
    return default

def backup_file(path, keep=10):
    """Copy `path` into backups/ with a timestamp and keep only the newest `keep` copies."""
    try:
        if not path.exists(): return
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, BACKUP_DIR / f"{path.stem}_{stamp}{path.suffix}")
        for old in sorted(BACKUP_DIR.glob(f"{path.stem}_*{path.suffix}"))[:-keep]: old.unlink(missing_ok=True)
    except Exception:
        pass  # a failed backup must never block a save

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_file(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)

@st.cache_data(ttl=5)
def load_modules():
    if not MODULES_PATH.exists(): return []
    try:
        with open(MODULES_PATH, encoding="utf-8") as f: return json.load(f).get("modules", [])
    except Exception as e:
        st.error(f"Could not load modules.json: {e}")
        return []

def save_modules(modules):
    backup_file(MODULES_PATH)
    tmp = MODULES_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f: json.dump({"modules": modules}, f, indent=2, ensure_ascii=False)
    tmp.replace(MODULES_PATH)
    load_modules.clear()

@st.cache_data(ttl=60)
def get_screenshot_files():
    if not SCREENSHOTS_DIR.exists(): return []
    return [f for f in SCREENSHOTS_DIR.iterdir() if f.is_file()]

def find_screenshot(name):
    if not name: return None
    name = name.lower().strip()
    files = get_screenshot_files()
    for f in files:
        if f.name.lower() == name or f.stem.lower() == name: return f
    for f in files:
        if name in f.stem.lower() or f.name.lower().startswith(name): return f
    return None

@st.cache_data(max_entries=150, show_spinner=False)
def _image_bytes(path_str, mtime, max_w):
    from PIL import Image
    p = path_str
    if p.lower().endswith(".gif"):
        with open(p, "rb") as f: return f.read()
    with Image.open(p) as im:
        if im.width <= max_w:
            with open(p, "rb") as f: return f.read()
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
        return buf.getvalue()

def get_display_image(path, max_w=None):
    """Scaled-down copy of a screenshot (cached). Returns None if it cannot be read."""
    try: return _image_bytes(str(path), path.stat().st_mtime, max_w or IMAGE_MAX_WIDTH)
    except Exception: return None

def flatten_block(b):
    parts = [str(b.get("type", ""))]
    for key in ("title", "text", "code", "notes", "caption", "label", "description", "expected", "on_failure"):
        v = b.get(key)
        if v: parts.append(str(v))
    for item in b.get("items", []):
        if isinstance(item, str): parts.append(item)
        elif isinstance(item, dict):
            for v in item.values():
                if isinstance(v, str) and v: parts.append(v)
    return "\n".join(parts)

def extract_snippet(text, needle, length=300):
    idx = text.lower().find(needle.lower())
    if idx == -1: return text[:length]
    half = length // 2
    start = max(0, idx - half)
    end = min(len(text), idx + half)
    snippet = text[start:end]
    if start > 0: snippet = "…" + snippet
    if end < len(text): snippet = snippet + "…"
    return snippet

def generate_pdf(text):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=11)
        nl = dict(new_x=XPos.LMARGIN, new_y=YPos.NEXT)  # reset cursor to left margin after each block
        for line in text.split("\n"):
            safe_line = line.translate(_PDF_MAP).encode("latin-1", "replace").decode("latin-1")
            if line.isupper() or line.startswith("HUAWEI"):
                pdf.set_font("helvetica", "B", 11)
                pdf.multi_cell(0, 8, safe_line, **nl)
                pdf.set_font("helvetica", size=11)
            else:
                pdf.multi_cell(0, 6, safe_line, **nl)
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None

_PDF_MAP = str.maketrans({"\u2014": "-", "\u2013": "-", "\u2192": "->", "\u2190": "<-", "\u2713": "v", "\u2018": "'", "\u2019": "'",
                          "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u2026": "...", "\u00a0": " "})
_IMSI_RE = re.compile(r"\b\d{15}\b")
_MSISDN_RE = re.compile(r"\b265\d{9}\b")

def _mask_digits(m):
    v = m.group(0)
    return v[:5] + "x" * (len(v) - 8) + v[-3:]

def mask_subscriber(text):
    """65001xxxxxxxx123 style masking for IMSI (15 digits) and MSISDN (265 + 9 digits)."""
    return _MSISDN_RE.sub(_mask_digits, _IMSI_RE.sub(_mask_digits, text or ""))

def module_to_text(m):
    """Plain-text version of a module, for the PDF / text download."""
    out = [str(m.get("title", "")).upper(), ""]
    if m.get("subtitle"): out += [str(m["subtitle"]), ""]
    for b in m.get("blocks", []):
        t = b.get("type")
        if t == "heading": out += ["", str(b.get("text", "")).upper(), ""]
        elif t == "paragraph": out += [str(b.get("text", "")), ""]
        elif t == "callout": out += [f"{b.get('title', '')} {b.get('text', '')}".strip(), ""]
        elif t == "command":
            if b.get("title"): out.append(str(b["title"]))
            out += ["    " + line for line in str(b.get("code", "")).splitlines()]
            if b.get("notes"): out.append("Note: " + str(b["notes"]))
            if b.get("on_failure"): out.append("If it fails: " + str(b["on_failure"]))
            out.append("")
        elif t == "checklist":
            if b.get("title"): out.append(str(b["title"]))
            out += ["[ ] " + str(i) for i in b.get("items", [])] + [""]
        elif t == "table":
            out.append(" | ".join(str(h) for h in b.get("headers", [])))
            out += [" | ".join(str(c) for c in row) for row in b.get("rows", [])] + [""]
        elif t == "quiz":
            out.append(str(b.get("title") or "Quick check"))
            out += [f"{n}. {it.get('question', '')}" for n, it in enumerate(b.get("items", []), 1)] + [""]
        elif t == "steps":
            for it in b.get("items", []):
                out.append(" - ".join(str(v) for v in it.values() if isinstance(v, str) and v) if isinstance(it, dict) else str(it))
            out.append("")
    return "\n".join(out)

@st.cache_data(show_spinner=False, max_entries=40)
def module_pdf(m):
    return generate_pdf(module_to_text(m))

def parse_quiz(text):
    """Quiz written as plain text -> (items, errors).
    One question per paragraph. Correct option starts with *, other options with -, explanation with >."""
    items, errors = [], []
    for n, blk in enumerate([b for b in re.split(r"\n\s*\n", (text or "").strip()) if b.strip()], 1):
        q, opts, correct, expl = "", [], [], []
        for line in blk.splitlines():
            line = line.strip()
            if not line: continue
            if line[0] == "*": correct.append(len(opts)); opts.append(line[1:].strip())
            elif line[0] == "-": opts.append(line[1:].strip())
            elif line[0] == ">": expl.append(line[1:].strip())
            else: q = (q + " " + line).strip()
        if not q: errors.append(f"Question {n}: no question text.")
        elif len(opts) < 2: errors.append(f"Question {n}: needs at least two options (lines starting with - or *).")
        elif len(correct) != 1: errors.append(f"Question {n}: mark exactly one correct option with *.")
        else: items.append({"question": q, "options": opts, "answer": correct[0], "explain": " ".join(expl)})
    return items, errors

def quiz_to_text(items):
    out = []
    for it in items or []:
        lines = [str(it.get("question", ""))]
        lines += [("* " if i == it.get("answer") else "- ") + str(o) for i, o in enumerate(it.get("options", []))]
        if it.get("explain"): lines.append("> " + str(it["explain"]))
        out.append("\n".join(lines))
    return "\n\n".join(out)

def load_templates(): return load_json(DATA_DIR / "templates.json", {"templates": []})["templates"]
def save_templates(tpls): save_json(DATA_DIR / "templates.json", {"templates": tpls})
def load_error_codes(): return load_json(DATA_DIR / "error_codes.json", {"entries": []})["entries"]
def save_error_codes(entries): save_json(DATA_DIR / "error_codes.json", {"entries": entries})
def load_troubleshooting(): return load_json(DATA_DIR / "troubleshooting.json", {"problems": []})["problems"]
def save_troubleshooting(problems): save_json(DATA_DIR / "troubleshooting.json", {"problems": problems})