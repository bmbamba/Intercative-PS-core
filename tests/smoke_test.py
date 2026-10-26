r"""Run before (re)starting the server:   python tests\smoke_test.py
Tests the SOP in SOP_HOME (default: this folder). Uses a throw-away database, so it never touches real
progress or logs. Checks that depend on content (flows, scenarios, quizzes...) are skipped when that content is absent."""
import json, logging, os, pathlib, re, sys, tempfile

logging.disable(logging.WARNING)  # Streamlit logs harmless warnings in test mode
ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["PS_SOP_DB"] = str(_tmp / "test.db")
os.environ["PS_SOP_BACKUPS"] = str(_tmp / "backups")
os.environ.pop("PS_SOP_ADMIN_PASSWORD", None)
os.environ["STREAMLIT_LOGGER_LEVEL"] = "error"

from streamlit.testing.v1 import AppTest
import config, db, utils
import sop_interactive as si

failures = []
def check(name, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + name + (f"  ({detail})" if detail and not ok else ""))
    if not ok: failures.append(name)
def skip(name): print(f"  skip  {name} (no such content in this SOP)")

def new_app(**state):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["operator"] = "smoketest"
    for k, v in state.items(): at.session_state[k] = v
    at.run(); return at

def errors(at): return [e.value for e in at.exception]
def click(at, pred):
    btn = next((b for b in at.button if pred(b)), None)
    if btn is None: return False
    btn.click(); at.run(); return True

print(f"Testing: {config.BRANDING['title']}   ({config.CONTENT_DIR})")
modules = json.loads(config.MODULES_PATH.read_text(encoding="utf-8"))["modules"]
ids = [m["id"] for m in modules]

print("Pages and modules")
for dark in (False, True):
    at = new_app(dark_mode=dark)
    check(f"first load ({'dark' if dark else 'light'})", not errors(at), errors(at))
    for p in config.PAGES:
        at.session_state["page"] = p; at.session_state["active_scenario"] = None; at.run()
        check(f"page {p} ({'dark' if dark else 'light'})", not errors(at), errors(at))
at = new_app()
for m in modules:
    at.session_state["page"] = "Modules"; at.session_state["current_module"] = m["id"]; at.run()
    check(f"module {m['id']}", not errors(at), errors(at))

print("Admin Edit Mode (edit menus must not clash with each other)")
at = new_app(edit_mode=True)
for p in config.PAGES:
    at.session_state["page"] = p; at.session_state["active_scenario"] = None; at.run()
    check(f"edit mode: page {p}", not errors(at), errors(at))
for m in modules:
    at.session_state["page"] = "Modules"; at.session_state["current_module"] = m["id"]; at.run()
    check(f"edit mode: module {m['id']}", not errors(at), errors(at))

print("Branding and hidden pages")
at = new_app()
labels = [b.label for b in at.sidebar.button]
hidden = set(config.BRANDING.get("hide_pages", [])) - {"Home", "Modules"}
check("hidden pages are not in the sidebar", not (hidden & set(labels)), sorted(hidden & set(labels)))
check("visible pages are in the sidebar", all(p in labels for p in config.NAV_PRIMARY + config.NAV_TOOLS), labels[:12])
if hidden:
    at.query_params["page"] = sorted(hidden)[0]; at.session_state["_url_loaded"] = False; at.run()
    check("a hidden page cannot be opened by URL", at.session_state["page"] != sorted(hidden)[0])

print("Troubleshooting flow: follow the first option until it ends")
if "Troubleshooting" in config.PAGES and utils.load_troubleshooting():
    at = new_app(page="Troubleshooting"); moves = 0
    while moves < 30 and click(at, lambda b: b.key and (b.key.startswith("br_") or b.key.startswith("ts_next_"))): moves += 1
    check("flow runs to an end without errors", not errors(at) and moves > 0, errors(at))
else: skip("troubleshooting flow")

print("Scenarios: first scenario, first choice each step")
if "Scenarios" in config.PAGES and si.load_scenarios():
    at = new_app(page="Scenarios")
    check("open scenario", click(at, lambda b: b.label in ("Start", "Resume", "Review")) and not errors(at), errors(at))
    for _ in range(20):
        if not at.session_state["active_scenario"]: break
        click(at, lambda b: b.key and "_choice_0" in b.key)
        click(at, lambda b: b.key and b.key.endswith("_next"))
    check("scenario finishes", not at.session_state["active_scenario"] and not errors(at), errors(at))
else: skip("scenarios")

print("Checklist saves")
cm = next((m for m in modules if any(b.get("type") == "checklist" for b in m["blocks"])), None)
if cm:
    at = new_app(page="Modules", current_module=cm["id"])
    box = next((c for c in at.checkbox if c.key.startswith("chk_")), None)
    if box: box.check(); at.run(); db.get_checklists.clear()
    check("tick is stored", bool(box) and any(any(v) for v in db.get_checklists("smoketest").values()))
else: skip("checklist")

print("Quizzes")
items, errs = utils.parse_quiz("Q one?\n- a\n* b\n> because\n\nQ two?\n* x\n- y")
check("quiz text is parsed", len(items) == 2 and items[0]["answer"] == 1 and items[0]["explain"] == "because" and not errs, errs)
check("quiz needs a question and options", bool(utils.parse_quiz("No options here")[1]))
check("quiz needs exactly one correct option", bool(utils.parse_quiz("Q?\n- a\n- b")[1]) and bool(utils.parse_quiz("Q?\n* a\n* b")[1]))
check("quiz survives a round trip through the editor text", utils.parse_quiz(utils.quiz_to_text(items))[0] == items)
qm = next((m for m in modules if any(b.get("type") == "quiz" for b in m["blocks"])), None)
if qm:
    at = new_app(page="Modules", current_module=qm["id"])
    for _ in range(40):
        if not click(at, lambda b: b.key and b.key.startswith("quiz_") and b.key.endswith("_o0") and not b.disabled): break
    check("quiz can be answered and shows a score", any(m.value.startswith("**Score:") for m in at.markdown) and not errors(at), errors(at))
    check("quiz can be restarted", click(at, lambda b: b.key and b.key.startswith("quiz_retry_")) and not any(m.value.startswith("**Score:") for m in at.markdown))
else: skip("quiz")

print("Feedback")
db.add_feedback("smoketest", ids[0], "Step 3 is unclear"); db.read_feedback.clear()
check("feedback is stored", any(r["text"] == "Step 3 is unclear" for r in db.read_feedback()))
at = new_app(page="Modules", current_module=ids[0])
try:
    at.text_area(key=f"fb_text_{ids[0]}").input("From the popover").run(); click(at, lambda b: b.key == f"fb_send_{ids[0]}"); db.read_feedback.clear()
    check("Report a problem box saves a report", any(r["text"] == "From the popover" for r in db.read_feedback()) and not errors(at), errors(at))
except Exception as e: check("Report a problem box saves a report", False, e)
if "Feedback" in config.PAGES:
    at = new_app(page="Feedback")
    check("feedback page lists reports", any("Step 3 is unclear" in m.value for m in at.markdown) and not errors(at), errors(at))

print("Log masking, backups, deep links")
db.append_session_log("smoketest", "cmd", "t", "LST OPTGPRS: IMSI=650010114416123", "n"); db.read_session_log.clear()
check("session log stores masked IMSI", "650010114416123" not in db.read_session_log("smoketest")[-1]["text"])
check("IMSI + MSISDN masked", utils.mask_subscriber("650010114416123 265888073002") == "65001xxxxxxx123 26588xxxx002")
db.backup_db(); check("daily database backup written", any(config.BACKUP_DIR.glob("sop_app_*.db")))
utils.save_json(config.DATA_DIR / "_t.json", {"a": 1}); utils.save_json(config.DATA_DIR / "_t.json", {"a": 2})
check("JSON saves leave a timestamped backup", any(config.BACKUP_DIR.glob("_t_*.json"))); (config.DATA_DIR / "_t.json").unlink()
at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60); at.query_params["module"] = ids[-1]; at.run()
check("?module=<id> opens that module", at.session_state["page"] == "Modules" and at.session_state["current_module"] == ids[-1] and not errors(at), errors(at))

print("Practice terminal")
resp = si.load_responses()
if "Practice Terminal" in config.PAGES and resp:
    first = next(iter(resp))
    at = new_app(page="Practice Terminal"); at.text_input(key="terminal_input").input(first.lower() + ";").run()
    check("terminal runs a command on Enter and clears the box", len(at.session_state["terminal_history"]) == 1 and at.session_state["terminal_input"] == "" and not errors(at), errors(at))
    at = new_app(page="Practice Terminal"); at.text_input(key="terminal_input").input(first[:-1]).run()
    check("unknown command gets a suggestion", any("Did you mean" in w.value for w in at.warning) and not errors(at), errors(at))
    with_imsi = next((k for k, v in resp.items() if "650010114416123" in v), None)
    if with_imsi:
        at = new_app(page="Practice Terminal", ctx_imsi="650019999999999"); at.text_input(key="terminal_input").input(with_imsi).run()
        out = " ".join(c.value for c in at.code)
        check("output uses the Subscriber Context IMSI", "650019999999999" in out and "650010114416123" not in out, out[:80])
    def _prefix():
        import streamlit as st, sop_interactive as s
        st.session_state["terminal_history"] = []
        s._execute_mock("DSP ABC", {"DSP A": "short", "DSP AB": "long"})
        st.session_state["picked"] = st.session_state["terminal_history"][0]["output"]
    check("longest matching command wins", AppTest.from_function(_prefix).run().session_state["picked"] == "long")
    _r = _tmp / "responses.json"
    si.save_response("lst apn;", "APN LIST", _r); si.save_response("DSP X", "X", _r); si.delete_response("DSP X", _r)
    check("admin can add and delete a mock response", utils.load_json(_r, {})["responses"] == {"LST APN": "APN LIST"})
else: skip("practice terminal")

print("Commands page")
if "Commands" in config.PAGES:
    at = new_app(page="Commands")
    total = int(re.search(r"of (\d+) commands", next(c.value for c in at.caption if "commands" in c.value)).group(1))
    check("commands page loads", not errors(at), errors(at))
    if total > 1:
        at.text_input(key="cmd_filter").input("zzzz-nothing").run()
        check("commands filter", any(c.value.startswith("0 of") for c in at.caption) and not errors(at))
        at = new_app(page="Commands"); at.toggle(key="cmd_read_only").set_value(True).run()
        shown = int(re.search(r"(\d+) of", next(c.value for c in at.caption if " of " in c.value and "commands" in c.value)).group(1))
        if any(utils.is_change_command(r["code"]) for r in __import__("views.commands", fromlist=["x"]).collect_all_commands(modules)):
            check("read-only toggle hides change commands", 0 < shown < total and not errors(at), (shown, total))

print("Contrast (WCAG AA, 4.5:1) for buttons and text in both themes")
def _theme(n): return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", getattr(si, n)))
def _lum(h):
    ch = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]; f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(ch[0]) + 0.7152 * f(ch[1]) + 0.0722 * f(ch[2])
def _cr(a, b): hi, lo = sorted((_lum(a), _lum(b)), reverse=True); return (hi + 0.05) / (lo + 0.05)
for n in ("LIGHT_THEME", "DARK_THEME"):
    v = _theme(n)
    for fg, bg in (("text-main", "bg-main"), ("text-main", "bg-card"), ("text-muted", "bg-card"), ("text-on-primary", "btn-primary"),
                   ("text-on-primary", "btn-primary-hover"), ("text-on-primary", "bg-sidebar-active"), ("accent-text", "bg-card"),
                   ("accent-text", "bg-main"), ("code-text", "code-bg")):
        check(f"{n[:5].lower()}: {fg} on {bg}", _cr(v[fg], v[bg]) >= 4.5, round(_cr(v[fg], v[bg]), 2))

print("Content")
check("module ids unique", len(ids) == len(set(ids)))
paths = utils.load_json(config.DATA_DIR / "learning_paths.json", {"paths": []})["paths"]
check("learning paths point at real modules", all(mid in ids for p in paths for mid in p.get("modules", [])))
for p in utils.load_troubleshooting():
    n = len(p.get("steps", []))
    bad = [b.get("next") for s in p.get("steps", []) for b in s.get("branches", []) if not isinstance(b.get("next"), int) or not 0 <= b["next"] < n]
    check(f"troubleshooting '{p['id']}' branches all land on a step", not bad, bad)
missing = sorted({(b.get("file") or b.get("match")) for m in modules for b in m["blocks"] if b.get("type") == "image" and not utils.find_screenshot(b.get("file") or b.get("match"))})
print("  ok    every referenced screenshot exists" if not missing else f"  warn  {len(missing)} referenced screenshot(s) not found: " + ", ".join(missing[:6]))

print("House rules")
src = {p: p.read_text(encoding="utf-8") for p in list(ROOT.glob("*.py")) + list((ROOT / "views").glob("*.py")) + list((ROOT / "tools").glob("*.py"))}
check("no st.dataframe", not any(re.search(r"st\.dataframe\(", t) for t in src.values()))
check("no st.radio", not any(re.search(r"st\.radio\(", t) for t in src.values()))
check("scroll-to-top script still in app.py", "forceScrollToTop" in src[ROOT / "app.py"])

print("\n" + ("ALL CHECKS PASSED" if not failures else f"{len(failures)} CHECK(S) FAILED: " + "; ".join(failures)))
sys.exit(1 if failures else 0)
