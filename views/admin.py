# views/admin.py
import datetime
import streamlit as st
import config
import db
import utils
import sop_interactive as si

@st.cache_data(ttl=5)
def build_search_index(modules):
    index = []
    for m in modules:
        for i, b in enumerate(m.get("blocks", [])):
            flat = utils.flatten_block(b)
            index.append((m, i, flat, b.get("type", "")))
    return index

def page_search(MODULES, cb_open_module):
    q = st.session_state["search"].strip()
    if not q: st.info("Type in the search box."); return
    st.title(f'Search: "{q}"')
    needle = q.lower()
    
    search_index = build_search_index(MODULES)
    results = [(m, i, flat, btype) for (m, i, flat, btype) in search_index if needle in flat.lower()]
    
    st.caption(f"{len(results)} match(es)")
    if not results: st.info("No matches found."); return
    for m, block_idx, flat, block_type in results[:60]:
        with st.expander(f"{m.get('icon','')} {m['title']} · block {block_idx+1} · {block_type}"):
            snippet = utils.extract_snippet(flat, needle, 400)
            st.code(snippet, language="text")
            st.button("Open module", key=f"open_{m['id']}_{block_idx}", on_click=cb_open_module, args=(m["id"],))

def page_templates(get_context):
    st.title("Command templates")
    tpls = utils.load_templates()
    if not tpls: st.info("No templates yet. Save one from any command block using the button."); return
    ctx = get_context()
    for tpl in tpls:
        title = tpl.get("title", "Untitled")
        with st.expander(f"{title} ({tpl.get('category','Custom')})"):
            raw = tpl.get("command", "")
            substituted = utils.substitute_placeholders(raw, ctx)
            if substituted != raw: st.caption("Placeholders filled from your Subscriber Context")
            st.code(substituted, language=tpl.get("language", "mml"))
            if tpl.get("notes"): st.caption(f"{tpl['notes']}")
            if st.session_state.get("edit_mode") and st.button("Delete", key=f"del_tpl_{tpl['id']}"): utils.save_templates([t for t in tpls if t["id"] != tpl["id"]]); st.rerun()

@st.dialog("Error code", width="large")
def dlg_error_code(index=None):
    entries = utils.load_error_codes()
    editing = index is not None and 0 <= index < len(entries)
    entry = entries[index] if editing else {}
    code = st.text_input("Code", value=entry.get("code", ""))
    category = st.text_input("Category", value=entry.get("category", "Custom"))
    meaning = st.text_input("Meaning", value=entry.get("meaning", ""))
    action = st.text_area("Action", value=entry.get("action", ""), height=100)
    if st.button("Save", type="primary", use_container_width=True):
        new = {"code": code.strip(), "category": category.strip() or "Custom", "meaning": meaning.strip() or "—", "action": action.strip() or "—"}
        if editing: entries[index] = new
        else: entries.append(new)
        utils.save_error_codes(entries); st.rerun()

def page_error_codes(embedded=False):
    if not embedded: st.title("Error codes")
    entries = utils.load_error_codes()
    q = st.text_input("Search error codes", key="ec_filter", placeholder="Search by code, meaning or action", label_visibility="collapsed").strip().lower()
    shown = [e for e in entries if not q or q in " ".join(str(e.get(k, "")) for k in ("code", "category", "meaning", "action")).lower()]
    if not shown:
        st.info("No matching error codes.")
    else:
        rows = ["| Code | Meaning | Action | Type |", "|---|---|---|---|"]
        rows += [f"| **{_md_cell(e.get('code', ''), 30)}** | {_md_cell(e.get('meaning', ''), 500)} | {_md_cell(e.get('action', ''), 500)} | {_md_cell(e.get('category', ''), 30)} |" for e in shown]
        st.markdown("\n".join(rows))
    if st.session_state.get("edit_mode"):  # edit tools only in Admin Edit Mode
        labels = [f"{e.get('code', '')} · {str(e.get('meaning', ''))[:40]}" for e in entries]
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            if st.button("Add code"): dlg_error_code(index=None)
        with c2: pick = st.selectbox("Edit code", labels, index=None, placeholder="Edit a code…", label_visibility="collapsed")
        with c3:
            if st.button("Edit", disabled=pick is None) and pick is not None: dlg_error_code(index=labels.index(pick))

@st.dialog("Troubleshooting problem", width="large")
def dlg_troubleshooting(pid=None):
    problems = utils.load_troubleshooting()
    editing = pid is not None
    problem = next((p for p in problems if p["id"] == pid), {}) if editing else {}
    title = st.text_input("Title", value=problem.get("title", ""))
    category = st.text_input("Category", value=problem.get("category", "General"))
    description = st.text_area("Description", value=problem.get("description", ""), height=80)
    st.caption("Steps — one per line: `Title | Description | Command | Expected`")
    steps_str = st.text_area("Steps", height=250, value="\n".join(" | ".join([s.get("title", ""), s.get("description", ""), s.get("command", ""), s.get("expected", "")]) for s in problem.get("steps", [])))
    if st.button("Save", type="primary", use_container_width=True):
        if not title.strip(): st.error("Title is required")
        else:
            steps = []
            for line in steps_str.splitlines():
                line = line.strip()
                if not line: continue
                parts = [p.strip() for p in line.split("|")]
                while len(parts) < 4: parts.append("")
                step = {"title": parts[0] or "Step"}
                if parts[1]: step["description"] = parts[1]
                if parts[2]: step["command"] = parts[2]
                if parts[3]: step["expected"] = parts[3]
                steps.append(step)
            new_p = {"id": pid or f"ts_{int(datetime.datetime.now().timestamp()*1000)}", "title": title.strip(), "category": category.strip() or "General", "description": description.strip(), "steps": steps}
            if editing:
                for i, p in enumerate(problems):
                    if p["id"] == pid: problems[i] = new_p; break
            else: problems.append(new_p)
            utils.save_troubleshooting(problems); st.rerun()

@st.dialog("Delete problem")
def dlg_delete_problem(pid):
    problems = utils.load_troubleshooting()
    p = next((p for p in problems if p["id"] == pid), None)
    if p:
        st.warning(f"Delete '{p.get('title','')}'?"); st.caption("This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Delete", type="primary", use_container_width=True): 
                utils.save_troubleshooting([x for x in problems if x["id"] != pid]); 
                st.session_state["ts_selected_problem"] = None
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True): st.rerun()

# --- troubleshooting flow navigation (callbacks, so a click does one clean rerun) ---
def _ts_go(state_key, path_key, nxt):
    st.session_state.setdefault(path_key, []).append(st.session_state[state_key])
    st.session_state[state_key] = nxt

def _ts_back(state_key, path_key):
    path = st.session_state.get(path_key) or []
    if path: st.session_state[state_key] = path.pop()

def _ts_restart(state_key, path_key):
    st.session_state[state_key] = 0
    st.session_state[path_key] = []

def page_troubleshooting(embedded=False):
    if not embedded: st.title("Troubleshooting")
    editing = st.session_state.get("edit_mode")

    problems = utils.load_troubleshooting()
    if not problems:
        st.info("No troubleshooting flows yet.")
        if editing and st.button("Create first problem", type="primary"): dlg_troubleshooting(pid=None)
        return

    # --- Pick a problem (a dropdown only when there is a choice) ---
    if len(problems) == 1:
        problem = problems[0]
        c1, c2 = st.columns([5, 1]) if editing else (st.container(), None)
        with c1: st.markdown(f"**{problem['title']}**")
    else:
        c1, c2 = st.columns([5, 1]) if editing else (st.container(), None)
        with c1:
            selected_title = st.selectbox("Select problem", [p["title"] for p in problems], label_visibility="collapsed")
        problem = next(p for p in problems if p["title"] == selected_title)
    if c2 is not None:  # edit tools only in Admin Edit Mode
        with c2:
            with st.popover("⋮", use_container_width=True):
                if st.button("New problem", use_container_width=True): dlg_troubleshooting(pid=None)
                if st.button("Edit", use_container_width=True): dlg_troubleshooting(pid=problem["id"])
                if st.button("Delete", use_container_width=True): dlg_delete_problem(problem["id"])
    if problem.get("description"): st.caption(problem["description"])

    steps = problem.get("steps", [])
    if not steps:
        st.warning("This problem has no steps yet.")
        return

    # --- State: current step + the path taken so far (so Back returns to where you came from) ---
    pid = problem["id"]
    op = st.session_state.get("operator") or "guest"
    state_key, path_key = f"ts_step_{pid}", f"ts_path_{pid}"
    progress = db.get_ts_progress(op)
    if state_key not in st.session_state: st.session_state[state_key] = progress.get(pid, 0)
    st.session_state.setdefault(path_key, [])
    idx = min(max(st.session_state[state_key], 0), len(steps) - 1)
    st.session_state[state_key] = idx
    if progress.get(pid) != idx: db.save_ts_progress(op, pid, idx)
    path = st.session_state[path_key]
    step = steps[idx]

    # --- The current step: one card ---
    with st.container(border=True):
        st.caption(f"STEP {len(path) + 1}")
        st.markdown(f"#### {step.get('title', '')}")
        if step.get("description"): st.write(step["description"])
        if step.get("command"):
            code = utils.substitute_placeholders(step["command"], si.get_context())
            if utils.is_change_command(code): st.warning("This command CHANGES configuration.")
            st.code(code, language=step.get("language", "mml"))
            if st.button("Log command", key=f"ts_log_{pid}_{idx}"):
                db.append_session_log(op, "cmd", step.get("title", f"Step {idx+1}"), code, si.get_context().get("node", ""))
                st.toast("Logged")
        if step.get("expected") and str(step["expected"]).strip() != "None":
            st.markdown(f"**Expect:** {step['expected']}")
        if step.get("note") and str(step["note"]).strip() != "None":
            st.warning(step["note"])

    # --- What next ---
    branches = step.get("branches", [])
    if branches:
        for i, br in enumerate(branches):
            target = min(max(int(br.get("next", idx + 1)), 0), len(steps) - 1)
            st.button(br.get("label", "Continue"), key=f"br_{pid}_{idx}_{i}", use_container_width=True,
                      on_click=_ts_go, args=(state_key, path_key, target))
    elif idx < len(steps) - 1:
        st.button("Next →", key=f"ts_next_{pid}_{idx}", type="primary", use_container_width=True,
                  on_click=_ts_go, args=(state_key, path_key, idx + 1))
    else:
        st.caption("End of this flow.")

    b1, b2, _ = st.columns([1, 1, 3])
    with b1: st.button("← Back", key=f"ts_back_{pid}", disabled=not path, use_container_width=True, on_click=_ts_back, args=(state_key, path_key))
    with b2: st.button("Start over", key=f"ts_reset_{pid}", disabled=(idx == 0 and not path), use_container_width=True, on_click=_ts_restart, args=(state_key, path_key))

def _md_cell(v, limit=80):
    s = " ".join(str(v or "").split())          # collapse newlines/whitespace
    s = s.replace("|", "\\|").replace("`", "'")  # keep the table intact
    return (s[:limit] + "…") if len(s) > limit else s

def page_feedback(module_by_id):
    st.title("Feedback")
    st.caption("Problems readers reported on modules, newest first.")
    rows = db.read_feedback()
    if not rows: st.info("Nothing reported yet."); return
    table = ["| Time | Who | Module | Report |", "|---|---|---|---|"]
    for r in rows:
        title = module_by_id.get(r["module_id"], {}).get("title", r["module_id"])
        table.append(f"| {_md_cell(r['t'], 20)} | {_md_cell(r['operator'], 30)} | {_md_cell(title, 50)} | {_md_cell(r['text'], 400)} |")
    st.markdown("\n".join(table))

def page_team_activity(embedded=False):
    if not embedded: st.title("Team activity")
    entries = db.read_team_activity(limit=500)
    if not entries: st.info("No activity yet."); return
    rows = ["| Time | Operator | Node | Kind | Title | Detail |", "|---|---|---|---|---|---|"]
    for e in entries[:200]:
        rows.append("| " + " | ".join(_md_cell(e.get(k, ""), lim) for k, lim in (("t", 25), ("operator", 30), ("node", 30), ("k", 20), ("title", 60), ("text", 80))) + " |")
    st.markdown("\n".join(rows))

def page_session_log():
    st.title("Session log")
    op = st.session_state["operator"]
    if not op: st.warning("Set your operator name first."); return
    entries = db.read_session_log(op, limit=500)
    if entries:
        md = si.session_log_md(op)
        st.download_button("Export .md", data=md, file_name=f"session_log_{utils.safe_name(op)}.md", mime="text/markdown")
    for e in reversed(entries[-50:]):
        with st.container(border=True):
            st.markdown(f"`{e.get('t','')}` · **{e.get('k','')}**")
            st.markdown(f"**{e.get('title','')}**")
            if e.get("text"): st.code(e["text"])

def page_ticket_builder(get_context):
    st.title("Huawei support request")
    op = st.session_state["operator"]
    ctx = get_context()
    with st.form("ticket"):
        problem = st.text_area("Problem description", height=100)
        node = st.text_input("Affected node / site", value=ctx.get("node", ""))
        when = st.text_input("Time of occurrence", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        done = st.text_area("Troubleshooting done", value=si.troubleshooting_lines(op), height=130)
        mask = st.checkbox("Mask IMSI / MSISDN", value=True)
        submitted = st.form_submit_button("Generate ticket text", type="primary")
    if submitted:
        parts = ["HUAWEI SUPPORT REQUEST — PS CORE", f"Prepared: {datetime.datetime.now():%Y-%m-%d %H:%M}", "", "PROBLEM DESCRIPTION", problem or "-", "", f"AFFECTED NODE / SITE: {node or '-'}", f"TIME OF OCCURRENCE: {when or '-'}", "", "TROUBLESHOOTING ALREADY PERFORMED", done or "-"]
        text = "\n".join(parts)
        if mask:
            for k in ("imsi", "msisdn"):
                v = ctx.get(k, "")
                if v: text = text.replace(v, v[:5] + "x" * (len(v) - 8) + v[-3:])
        st.session_state["ticket_text"] = text
    if (st.session_state.get("ticket_text") and str(st.session_state["ticket_text"]).strip() != "None"):
        st.success("Ticket ready — download PDF below.")
        st.code(st.session_state["ticket_text"], language="text")
        pdf_bytes = utils.generate_pdf(st.session_state["ticket_text"])
        if pdf_bytes:
            st.download_button("Download PDF", data=pdf_bytes, file_name=f"Huawei_SR_{datetime.datetime.now():%Y%m%d_%H%M}.pdf", mime="application/pdf", type="primary")
        if st.button("Clear ticket"): st.session_state["ticket_text"] = None; st.rerun()

def page_screenshot_library(embedded=False):
    if not embedded: st.title("Screenshot Library")
    exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    files = sorted((f for f in utils.get_screenshot_files() if f.suffix.lower() in exts), key=lambda f: f.name.lower())
    if not files: st.info("No screenshots found."); return
    q = st.text_input("Filter", key="shot_filter", placeholder=f"Filter {len(files)} screenshots by name", label_visibility="collapsed").strip().lower()
    shown = [f for f in files if q in f.name.lower()]
    if not shown: st.info("No match."); return
    if len(shown) == 1:  # narrowed down to one: show it full size
        st.image(utils.get_display_image(shown[0]) or str(shown[0]), caption=shown[0].name, use_container_width=True)
        return
    limit = 12
    st.caption(f"Showing {min(limit, len(shown))} of {len(shown)}. Type in the box to narrow down.")
    cols = st.columns(3)
    for i, f in enumerate(shown[:limit]):
        with cols[i % 3]:
            st.image(utils.get_display_image(f, config.THUMB_WIDTH) or str(f), caption=f.name, use_container_width=True)
