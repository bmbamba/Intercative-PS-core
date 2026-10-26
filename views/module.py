# views/module.py
import json
import time
import datetime
import streamlit as st
import sop_interactive as si
import config
import db
import utils

# =========================================================
# DIALOGS
# =========================================================
@st.dialog("Edit block", width="large")
def dlg_edit_block(module_id, block_idx, module_data):
    block = module_data["blocks"][block_idx]
    btype = block.get("type", "paragraph")
    st.caption(f"Block {block_idx+1} of {len(module_data['blocks'])} · type: **{btype}**")
    new_block = dict(block)  # keep any fields this dialog does not edit (e.g. image "match")
    new_block["type"] = btype
    can_save = True
    
    if btype == "paragraph": 
        new_block["text"] = st.text_area("Text", value=block.get("text",""), height=200)
    elif btype == "heading":
        new_block["level"] = st.selectbox("Level", [2, 3], index=0 if block.get("level",2)==2 else 1)
        new_block["text"] = st.text_input("Heading text", value=block.get("text",""))
    elif btype == "callout":
        variants = ["info", "warning", "danger", "success"]
        new_block["variant"] = st.selectbox("Variant", variants, index=variants.index(block.get("variant")) if block.get("variant") in variants else 0)
        new_block["title"] = st.text_input("Title", value=block.get("title",""))
        new_block["text"] = st.text_area("Body", value=block.get("text",""), height=150)
    elif btype == "command":
        new_block["title"] = st.text_input("Title", value=block.get("title",""))
        new_block["language"] = st.text_input("Language", value=block.get("language","mml"))
        new_block["code"] = st.text_area("Code", value=block.get("code",""), height=180)
        new_block["notes"] = st.text_input("Notes", value=block.get("notes",""))
        new_block["on_failure"] = st.text_area("On failure", value=block.get("on_failure",""), height=80)
    elif btype == "image":
        new_block["file"] = st.text_input("Filename in screenshots/", value=block.get("file",""), help="e.g. topology.png")
        new_block["caption"] = st.text_input("Caption", value=block.get("caption",""))
        new_block["width"] = st.number_input("Width", value=int(block.get("width", 1000)))
    elif btype == "table":
        headers = ",".join(block.get("headers", []))
        new_block["headers"] = [h.strip() for h in st.text_input("Headers (comma separated)", value=headers).split(",") if h.strip()]
        rows = "\n".join([" | ".join(r) for r in block.get("rows", [])])
        rows_str = st.text_area("Rows (one per line, pipe separated)", value=rows, height=150)
        new_block["rows"] = [[c.strip() for c in line.split("|")] for line in rows_str.splitlines() if line.strip()]
    elif btype == "checklist":
        new_block["id"] = st.text_input("Checklist ID", value=block.get("id","default"))
        new_block["title"] = st.text_input("Title", value=block.get("title",""))
        items = "\n".join(block.get("items", []))
        items_str = st.text_area("Items (one per line)", value=items, height=150)
        new_block["items"] = [i.strip() for i in items_str.splitlines() if i.strip()]
    elif btype == "link":
        new_block["target"] = st.text_input("Target module ID", value=block.get("target",""))
        new_block["label"] = st.text_input("Button Label", value=block.get("label",""))
    elif btype == "quiz":
        new_block["title"] = st.text_input("Title", value=block.get("title", ""))
        items, errs = utils.parse_quiz(st.text_area("Questions", value=utils.quiz_to_text(block.get("items", [])), height=300, help=QUIZ_HELP))
        for e in errs: st.error(e)
        new_block["items"] = items
        can_save = bool(items) and not errs
    elif btype != "divider":
        # steps, flow_player, topology_map and the embedded manager blocks have no form here.
        # Edit them as raw JSON so Save never wipes their content.
        st.info("This block type has no form. Edit its JSON directly.")
        raw = st.text_area("Block JSON", value=json.dumps(block, indent=2, ensure_ascii=False), height=350)
        try:
            new_block = json.loads(raw)
            if not isinstance(new_block, dict) or "type" not in new_block: raise ValueError('JSON must be an object with a "type" field')
        except (json.JSONDecodeError, ValueError) as e:
            can_save = False
            st.error(f"Invalid JSON: {e}")

    if st.button("Save", type="primary", use_container_width=True, disabled=not can_save):
        modules = utils.load_modules()
        for m in modules:
            if m["id"] == module_id: m["blocks"][block_idx] = new_block; break
        utils.save_modules(modules); st.rerun()

@st.dialog("Add block", width="large")
def dlg_add_block(module_id):
    btype = st.selectbox("Block type", ["paragraph", "heading", "callout", "command", "image", "table", "checklist", "quiz", "link", "divider"])
    new_block = {"type": btype}
    can_add = True
    if btype == "paragraph": new_block["text"] = st.text_area("Text", height=160)
    elif btype == "heading": new_block["level"] = st.selectbox("Level", [2, 3]); new_block["text"] = st.text_input("Heading text")
    elif btype == "callout": new_block["variant"] = st.selectbox("Variant", ["info","warning","danger","success"]); new_block["title"] = st.text_input("Title"); new_block["text"] = st.text_area("Body", height=120)
    elif btype == "command": new_block["title"] = st.text_input("Title"); new_block["language"] = st.text_input("Language", value="mml"); new_block["code"] = st.text_area("Code", height=140); new_block["notes"] = st.text_input("Notes")
    elif btype == "image": new_block["file"] = st.text_input("Filename", help="e.g. topology.png"); new_block["caption"] = st.text_input("Caption"); new_block["width"] = 1000
    elif btype == "table": 
        new_block["headers"] = [h.strip() for h in st.text_input("Headers (comma separated)").split(",") if h.strip()]
        rows_str = st.text_area("Rows (pipe separated)", height=100)
        new_block["rows"] = [[c.strip() for c in line.split("|")] for line in rows_str.splitlines() if line.strip()]
    elif btype == "checklist":
        new_block["id"] = st.text_input("Checklist ID", value=f"chk_{int(time.time())}")
        new_block["title"] = st.text_input("Title")
        items_str = st.text_area("Items (one per line)", height=100)
        new_block["items"] = [i.strip() for i in items_str.splitlines() if i.strip()]
    elif btype == "quiz":
        new_block["title"] = st.text_input("Title", value="Quick check")
        items, errs = utils.parse_quiz(st.text_area("Questions", height=260, help=QUIZ_HELP, placeholder="Which port does the service use?\n- 80\n* 443\n- 8080\n> HTTPS uses 443."))
        for e in errs: st.error(e)
        new_block["items"] = items
        can_add = bool(items) and not errs
    elif btype == "link": new_block["target"] = st.text_input("Target ID"); new_block["label"] = st.text_input("Label")

    if st.button("Add block", type="primary", use_container_width=True, disabled=not can_add):
        modules = utils.load_modules()
        for m in modules:
            if m["id"] == module_id: m.setdefault("blocks", []).append(new_block); break
        utils.save_modules(modules); st.rerun()

@st.dialog("Copy commands", width="large")
def dlg_copy_all(module_id, cmds, context):
    st.write(f"About to copy **{len(cmds)}** command(s).")
    if st.button("Copy all", type="primary", use_container_width=True):
        lines = [f"# {module_id}: all commands", ""]
        for title, code in cmds:
            if title: lines.append(f"# {title}")
            lines.append(utils.substitute_placeholders(code, context)); lines.append("")
        st.session_state["copy_all_result"] = "\n".join(lines)
        st.session_state["copy_all_module"] = module_id
        st.rerun()

# =========================================================
# BLOCK MENU & RENDERERS
# =========================================================
def render_block_menu(module_id, idx, block, module_data):
    with st.popover("⋮", help="Block options"):
        if st.button("Edit", key=f"bn_edit_{module_id}_{idx}", use_container_width=True): 
            dlg_edit_block(module_id, idx, module_data)
        if st.button("Move up", key=f"bn_up_{module_id}_{idx}", use_container_width=True, disabled=(idx == 0)):
            modules = utils.load_modules()
            for m in modules:
                if m["id"] == module_id: m["blocks"][idx], m["blocks"][idx-1] = m["blocks"][idx-1], m["blocks"][idx]; break
            utils.save_modules(modules); st.rerun()
        if st.button("Move down", key=f"bn_down_{module_id}_{idx}", use_container_width=True, disabled=(idx >= len(module_data["blocks"]) - 1)):
            modules = utils.load_modules()
            for m in modules:
                if m["id"] == module_id: m["blocks"][idx], m["blocks"][idx+1] = m["blocks"][idx+1], m["blocks"][idx]; break
            utils.save_modules(modules); st.rerun()
        if st.button("Duplicate", key=f"bn_dup_{module_id}_{idx}", use_container_width=True):
            import copy
            modules = utils.load_modules()
            for m in modules:
                if m["id"] == module_id: m["blocks"].insert(idx + 1, copy.deepcopy(m["blocks"][idx])); break
            utils.save_modules(modules); st.rerun()
        if st.button("Delete", key=f"bn_del_{module_id}_{idx}", use_container_width=True):
            modules = utils.load_modules()
            for m in modules:
                if m["id"] == module_id: m["blocks"].pop(idx); break
            utils.save_modules(modules); st.rerun()

QUIZ_HELP = "One question per paragraph (leave a blank line between questions). Start the correct option with *, the others with -. An optional line starting with > is the explanation."

def _quiz_pick(pk, i): st.session_state[pk] = i

def _quiz_reset(key_prefix, n):
    for qi in range(n): st.session_state.pop(f"quiz_{key_prefix}_{qi}", None)

@st.fragment
def render_quiz(b, key_prefix):
    """Self-check for readers. Answers live in the session only; nothing is stored."""
    items = b.get("items", [])
    if not items: return
    with st.container(border=True):
        st.markdown(f"**{b.get('title') or 'Quick check'}**")
        answered = correct = 0
        for qi, it in enumerate(items):
            pk = f"quiz_{key_prefix}_{qi}"
            picked = st.session_state.get(pk)
            st.markdown(f"{qi + 1}. {it.get('question', '')}")
            for oi, opt in enumerate(it.get("options", [])):
                st.button(opt, key=f"{pk}_o{oi}", use_container_width=True, disabled=picked is not None,
                          type="primary" if picked == oi else "secondary", on_click=_quiz_pick, args=(pk, oi))
            if picked is not None:
                ok = picked == it.get("answer")
                answered += 1; correct += ok
                if ok: st.success("Correct.")
                else: st.error(f"Not quite. The answer is: {it['options'][it['answer']]}")
                if it.get("explain"): st.caption(it["explain"])
        if answered == len(items):
            st.markdown(f"**Score: {correct} of {len(items)}**")
            st.button("Try again", key=f"quiz_retry_{key_prefix}", on_click=_quiz_reset, args=(key_prefix, len(items)))

def _send_feedback(module_id):
    key = f"fb_text_{module_id}"
    text = (st.session_state.get(key) or "").strip()
    if text:
        db.add_feedback(st.session_state.get("operator") or "guest", module_id, text)
        st.session_state[key] = ""
        st.toast("Thanks, sent to the maintainers.")

@st.fragment
def render_checklist(b, operator):
    """A fragment: ticking a box reruns only this checklist, not the whole page and sidebar."""
    cid, title, items = b.get("id", "default"), b.get("title", ""), b.get("items", [])
    if not items: return
    op_key = utils.safe_name(operator)
    states = db.get_checklists(operator)
    current = (list(states.get(cid, [])) + [False] * len(items))[:len(items)]
    with st.container(border=True):
        if title: st.markdown(f"**{title}**")
        new_states = [st.checkbox(item, value=current[i], key=f"chk_{op_key}_{cid}_{i}") for i, item in enumerate(items)]
        done = sum(new_states)
        st.progress(done / len(items), text=f"{done} / {len(items)} complete")
        if not operator: st.caption("Enter your name in the sidebar to save progress.")
        if new_states != current:
            db.save_checklist(operator, cid, new_states)
            if all(new_states) != all(current): st.rerun()  # full rerun only so the sidebar tick updates

def _cell(v):
    # keep "|" and line breaks inside a cell from breaking the Markdown table
    return str(v).replace("|", "\\|").replace("\n", " ")

def render_block(b, context, operator, key_prefix):
    t = b.get("type")
    if t == "heading": 
        if b.get("text") and str(b["text"]).strip() != "None": st.markdown(f"{'#' * min(b.get('level',2), 6)} {b['text']}")
    elif t == "paragraph": 
        if b.get("text") and str(b["text"]).strip() != "None": st.markdown(b["text"])
    elif t == "callout":
        if not b.get("text") or str(b["text"]).strip() == "None": return
        msg = f"**{b.get('title','')}**\n\n{b['text']}" if b.get("title") else b["text"]
        {"warning": st.warning, "danger": st.error, "success": st.success}.get(b.get("variant", "info"), st.info)(msg)
    elif t == "command":
        title, code, notes, on_failure = b.get("title", ""), utils.substitute_placeholders(b.get("code", ""), context), b.get("notes", ""), b.get("on_failure", "")
        with st.container(border=True):
            if title: st.markdown(f"**{title}**")
            if utils.is_change_command(code): st.warning("This command CHANGES configuration. Confirm the change ticket is approved.")
            st.code(code, language=b.get("language", "mml"))
            unfilled = utils.find_unfilled(code)
            if unfilled: st.caption(f"Unfilled placeholders: {', '.join(unfilled)}")
            if notes: st.caption(f"{notes}")
            if on_failure: st.info(f"If this fails: {on_failure}")
            c1, c2, _ = st.columns([1, 1.5, 3.5])
            with c1:
                if st.button("Log", key=f"{key_prefix}_log", use_container_width=True):
                    db.append_session_log(operator, "cmd", title or code.strip().splitlines()[0][:60], code, context.get("node", ""))
                    st.toast("Logged")
            with c2:
                if st.session_state.get("edit_mode") and st.button("Save template", key=f"{key_prefix}_tpl", use_container_width=True):
                    tpls = utils.load_templates()
                    tpls.append({"id": f"tpl_{int(time.time()*1000)}", "title": title or "Untitled", "category": "Custom", "language": b.get("language", "mml"), "command": b.get("code", ""), "notes": notes, "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
                    utils.save_templates(tpls); st.toast("Template saved")
    elif t == "table":
        headers, rows = b.get("headers", []), b.get("rows", [])
        if not headers and not rows: return
        # Markdown table, not st.dataframe (dataframes break the dark-mode CSS)
        md = ""
        if headers:
            md += "| " + " | ".join(_cell(h) for h in headers) + " |\n"
            md += "|" + "|".join(["---"] * len(headers)) + "|\n"
        for row in rows:
            md += "| " + " | ".join(_cell(c) for c in row) + " |\n"
        st.markdown(md)
    elif t == "checklist": render_checklist(b, operator)
    elif t == "steps":
        for i, step in enumerate(b.get("items", []), start=1):
            with st.expander(f"**Step {i}.** {step.get('title','')}", expanded=(i == 1)):
                if step.get("description"): st.write(step["description"])
                if step.get("command"):
                    code = utils.substitute_placeholders(step["command"], context)
                    if utils.is_change_command(code): st.warning("This command CHANGES configuration.")
                    st.code(code, language=step.get("language", "mml"))
                    if st.button("Log", key=f"{key_prefix}_step_{i}_log"):
                        db.append_session_log(operator, "cmd", step.get("title", f"Step {i}"), code, context.get("node", "")); st.toast("Logged")
                if step.get("expected") and str(step["expected"]).strip() != "None": st.success(f"Expected: {step['expected']}")
                if step.get("note") and str(step["note"]).strip() != "None": st.warning(f"{step['note']}")
                if step.get("on_failure"): st.info(f"If this fails: {step['on_failure']}")
    elif t == "image":
        filename = b.get("file") or b.get("match") or ""
        path = utils.find_screenshot(filename)
        caption = b.get("caption", "")
        if path and path.exists():
            img = utils.get_display_image(path) or str(path)
            try:
                if config.COLLAPSE_SCREENSHOTS:
                    with st.expander(f"Screenshot: {caption or path.stem}"): st.image(img, use_container_width=True)
                else: st.image(img, caption=caption, use_container_width=True)
            except Exception: st.caption(f"Image could not render: {filename}")
        else: st.warning(f"Image not found: **{filename}**.")
    elif t == "quiz": render_quiz(b, key_prefix)
    elif t == "link":
        target, label = b.get("target", ""), b.get("label", "")
        if label and str(label).strip() != "None":
            st.button(f"→ {label}", key=f"{key_prefix}_link", use_container_width=True, on_click=si.go_to_module, args=(target,))
    elif t == "divider": st.divider()
    elif t == "error_lookup": from views.admin import page_error_codes; page_error_codes(embedded=True)
    elif t == "troubleshooting_manager": from views.admin import page_troubleshooting; page_troubleshooting(embedded=True)
    elif t == "screenshot_library": from views.admin import page_screenshot_library; page_screenshot_library(embedded=True)
    elif t == "team_activity": from views.admin import page_team_activity; page_team_activity(embedded=True)
    elif t == "flow_player": si.render_flow_player(b, key_prefix)
    elif t == "topology_map": si.render_topology_map(b, key_prefix)
    else: st.caption(f"(Unsupported block: {t})")

def collect_commands(m):
    out = []
    for b in m.get("blocks", []):
        if b.get("type") == "command" and b.get("code"): out.append((b.get("title", "Command"), b["code"]))
        elif b.get("type") == "steps":
            for s in b.get("items", []):
                if s.get("command"): out.append((s.get("title", "Step"), s["command"]))
    return out

# =========================================================
# MAIN MODULE RENDERER
# =========================================================
def render_module(MODULE_BY_ID, cb_open_module, get_context):
    m = MODULE_BY_ID.get(st.session_state["current_module"])
    if not m:
        st.error("Module not found.")
        return
            
    op = st.session_state["operator"]
    if op and m["id"] not in db.load_visited(op): db.mark_visited(op, m["id"])  # write once, not on every rerun

    st.caption(m.get("category", "").upper())
    st.title(f"{m.get('icon','')} {m['title']}")
    if m.get("subtitle"): st.markdown(f"**{m['subtitle']}**")
    meta = [f"Owner: {m['owner']}" if m.get("owner") else "", f"Reviewed: {m['reviewed']}" if m.get("reviewed") else ""]
    if any(meta): st.caption("  ·  ".join(x for x in meta if x))  # optional fields in modules.json
    cmds, context = collect_commands(m), get_context()

    if cmds:
        c1, _ = st.columns([2, 5])
        with c1:
            if st.button(f"Copy all {len(cmds)} commands", key=f"copyall_{m['id']}", type="primary", use_container_width=True):
                dlg_copy_all(m["id"], cmds, context)

        if (st.session_state.get("copy_all_module") == m["id"] and isinstance(st.session_state.get("copy_all_result"), str) and st.session_state["copy_all_result"].strip() not in ("", "None")):
            st.success("Commands ready. Select all and copy:")
            st.code(st.session_state["copy_all_result"], language="mml")
            if st.button("Done", key=f"copyall_done_{m['id']}"):
                st.session_state["copy_all_result"] = None
                st.session_state["copy_all_module"] = None
                st.rerun()

    st.markdown("---") 

    for i, b in enumerate(m.get("blocks", [])):
        if st.session_state.get("edit_mode"):
            col_content, col_menu = st.columns([20, 1])
            with col_menu: render_block_menu(m["id"], i, b, m)
            with col_content: render_block(b, context, op, f"{m['id']}_{i}")
        else:
            render_block(b, context, op, f"{m['id']}_{i}")

    if st.session_state.get("edit_mode"):
        st.markdown("---")
        if st.button("Add block to this module", use_container_width=True): dlg_add_block(m["id"])

    d1, d2, _ = st.columns([1, 1, 3])
    with d1, st.popover("Download"):
        st.download_button("PDF", data=utils.module_pdf(m) or b"", file_name=f"{utils.safe_name(m['id'])}.pdf", mime="application/pdf", key=f"dl_pdf_{m['id']}", use_container_width=True)
        st.download_button("Text", data=utils.module_to_text(m), file_name=f"{utils.safe_name(m['id'])}.txt", mime="text/plain", key=f"dl_txt_{m['id']}", use_container_width=True)

    with d2, st.popover("Report a problem"):
        st.text_area("What is unclear or wrong in this module?", key=f"fb_text_{m['id']}", height=100, label_visibility="collapsed", placeholder="What is unclear or wrong in this module?")
        st.button("Send", key=f"fb_send_{m['id']}", use_container_width=True, on_click=_send_feedback, args=(m["id"],))

    # Completion logic
    has_checklist = any(b.get("type") == "checklist" for b in m.get("blocks", []))
    if not has_checklist and op:
        st.markdown("---")
        completed = db.get_completed_modules(op)
        if m["id"] in completed:
            c1, c2 = st.columns([4, 1])
            with c1: st.success("You've marked this module as complete.")
            with c2:
                if st.button("Unmark", key=f"unmark_{m['id']}", use_container_width=True):
                    db.save_completed_modules(op, completed - {m["id"]})
                    st.rerun()
        else:
            st.info("This module has no checklist. Mark it complete when you've finished reading.")
            if st.button("Mark as complete", key=f"mark_{m['id']}", type="primary"):
                db.save_completed_modules(op, completed | {m["id"]})
                st.rerun()

    # Up Next Router
    paths = si.load_paths()
    next_mid = None
    for p in paths:
        mids = p.get("modules", [])
        if m["id"] in mids:
            idx = mids.index(m["id"])
            if idx < len(mids) - 1:
                next_mid = mids[idx + 1]
                break
    if next_mid and next_mid in MODULE_BY_ID:
        nxt = MODULE_BY_ID[next_mid]
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("### Up Next in your Path")
        st.button(f"Next Topic → {nxt.get('icon','')} {nxt.get('title') or 'Next Module'}", type="primary", use_container_width=True, on_click=cb_open_module, args=(next_mid,))