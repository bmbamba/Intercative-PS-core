# sop_interactive.py
import datetime
import difflib
import html
import re
import streamlit as st
import streamlit.components.v1 as components
import utils
import db
from config import DATA_DIR

LIGHT_THEME = """
:root {
    --primary: #00A859; 
    --primary-hover: #008F4C; 
    --primary-dark: #006B39; 
    --primary-light: #4DD58A;
    --btn-primary: #007A45;
    --btn-primary-hover: #006B39;
    --accent-text: #007A45;
    
    --bg-main: #F2F3F5; 
    --bg-subtle: #E3E5E8; 
    --bg-card: #FFFFFF; 
    --bg-sidebar: #E3E5E8;
    --bg-sidebar-active: #007A45; 
    --bg-sidebar-hover: #D4D7DC; 
    
    --text-main: #313338; 
    --text-muted: #5C5E66; 
    --text-bright: #1E1F22; 
    --text-on-primary: #FFFFFF;
    
    --border: #D4D7DC; 
    --border-dark: #B5BAC1; 
    --shadow: 0 1px 3px rgba(0,0,0,0.05);
    --radius: 8px;
    
    --table-header: #E3E5E8; 
    --table-row-alt: #F7F8F9; 
    --table-text: #313338;

    --code-bg: #F6F8FA;
    --code-text: #1F2328;
    --code-border: #D0D7DE;
    color-scheme: light;
}
"""

DARK_THEME = """
:root {
    --primary: #2EBD6B; 
    --primary-hover: #249C57; 
    --primary-dark: #1A6B3A; 
    --primary-light: #57D98B;
    --btn-primary: #178046;
    --btn-primary-hover: #126B39;
    --accent-text: #2EBD6B;
    
    --bg-main: #1E1F22; 
    --bg-subtle: #2B2D31; 
    --bg-card: #2B2D31; 
    --bg-sidebar: #1A1B1E;
    --bg-sidebar-active: #1A6B3A; 
    --bg-sidebar-hover: #35373C; 
    
    --text-main: #DBDEE1; 
    --text-muted: #949BA4; 
    --text-bright: #F2F3F5; 
    --text-on-primary: #FFFFFF;
    
    --border: #3F4147; 
    --border-dark: #4E5058; 
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
    --radius: 8px;
    
    --table-header: #313338; 
    --table-row-alt: #2B2D31; 
    --table-text: #DBDEE1;

    --code-bg: #16171A;
    --code-text: #E6E8EB;
    --code-border: #3F4147;
    color-scheme: dark;
}
"""

BASE_CSS = """
<style>
/* ============ GLOBAL ============ */
.stApp, [data-testid="stAppViewContainer"], .main, section.main { background-color: var(--bg-main) !important; }
h1, h2, h3, h4, h5, h6 { color: var(--text-bright) !important; font-weight: 600 !important; }
p, span, label, li, .stMarkdown { color: var(--text-main) !important; }
[data-testid="stCaptionContainer"], small, .stCaption { color: var(--text-muted) !important; }
html, body, [class*="css"] { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important; }
.block-container { padding-top: 2rem !important; padding-bottom: 4rem !important; max-width: 1100px !important; }

/* ============ HEADER & TOOLBAR ============ */
header[data-testid="stHeader"] { background: transparent !important; z-index: 999998 !important; }
/* Hide only the unwanted toolbar items. Do NOT hide [data-testid="stToolbar"] itself:
   in newer Streamlit the "expand sidebar" button lives inside it. */
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
[data-testid="stDeployButton"], [data-testid="stStatusWidget"], #MainMenu {
    display: none !important; visibility: hidden !important;
}
[data-testid="stToolbar"] { background: transparent !important; }

/* Button that re-opens a collapsed sidebar (selector differs between Streamlit versions) */
[data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {
    display: flex !important; visibility: visible !important; opacity: 1 !important;
    background-color: var(--btn-primary) !important; color: var(--text-on-primary) !important;
    border-radius: var(--radius) !important; margin: 8px !important; padding: 6px 8px !important;
    border: 2px solid var(--primary-light) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}
[data-testid="collapsedControl"] svg, [data-testid="stSidebarCollapsedControl"] svg, [data-testid="stExpandSidebarButton"] svg {
    fill: var(--text-on-primary) !important; width: 24px !important; height: 24px !important;
}
[data-testid="stExpandSidebarButton"] span, [data-testid="stExpandSidebarButton"] p { color: var(--text-on-primary) !important; }

/* Collapse button inside the sidebar: always visible (Streamlit only shows it on hover) */
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapseButton"] button { opacity: 1 !important; visibility: visible !important; }
[data-testid="stSidebarCollapseButton"] span, [data-testid="stSidebarCollapseButton"] svg { color: var(--text-main) !important; fill: var(--text-main) !important; }

/* ============ HEADINGS & CARDS ============ */
h1 { font-size: 2.2rem !important; margin-bottom: 1rem !important; }
h2 { font-size: 1.5rem !important; margin-top: 1.2rem !important; padding-bottom: 0.5rem !important; border-bottom: 1px solid var(--border) !important; }
h3 { font-size: 1.2rem !important; margin-top: 1rem !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--bg-card) !important; border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important; box-shadow: var(--shadow) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div > div { padding: 1rem !important; }

/* ============ BUTTONS ============ */
.stButton > button { font-weight: 500 !important; border-radius: var(--radius) !important; transition: all 0.2s !important; }
.stButton > button[kind="primary"] { background-color: var(--btn-primary) !important; color: var(--text-on-primary) !important; border: none !important; }
.stButton > button[kind="primary"]:hover { background-color: var(--btn-primary-hover) !important; }
.stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p,
[data-testid="stFormSubmitButton"] > button[kind="primary"] p { color: var(--text-on-primary) !important; }
.stButton > button[kind="secondary"] { background-color: var(--bg-card) !important; color: var(--text-main) !important; border: 1px solid var(--border-dark) !important; }
.stButton > button[kind="secondary"]:hover { border-color: var(--primary) !important; color: var(--accent-text) !important; }

/* ============ SIDEBAR ============ */
[data-testid="stSidebar"] { background-color: var(--bg-sidebar) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: var(--text-main) !important; }

[data-testid="stSidebar"] div[data-testid="stButton"] {
    width: 100% !important; display: block !important; text-align: left !important; padding: 0 !important; margin: 0 0 2px 0 !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    width: 100% !important; display: flex !important; flex-direction: row !important; justify-content: flex-start !important;
    align-items: center !important; padding: 8px 12px !important; margin: 0 !important; border-radius: var(--radius) !important;
    border: 1px solid transparent !important; background-color: transparent !important; color: var(--text-main) !important;
    font-size: 0.95rem !important; text-align: left !important; box-shadow: none !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button div,
[data-testid="stSidebar"] div[data-testid="stButton"] > button p,
[data-testid="stSidebar"] div[data-testid="stButton"] > button span {
    display: block !important; text-align: left !important; width: 100% !important; margin: 0 !important; padding: 0 !important;
    white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover { background-color: var(--bg-sidebar-hover) !important; }
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
    background-color: var(--bg-sidebar-active) !important; color: var(--text-on-primary) !important;
    font-weight: 600 !important; border-left: 4px solid var(--primary-light) !important; 
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] p { color: var(--text-on-primary) !important; }

/* ============ TABLES (Markdown Based) ============ */
.stMarkdown table {
    border-collapse: collapse !important; width: 100% !important;
    border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
    overflow: hidden !important; background-color: var(--bg-card) !important;
    margin-bottom: 1.5rem !important;
}
.stMarkdown table th {
    background-color: var(--table-header) !important; color: var(--table-text) !important;
    font-weight: 600 !important; border: 1px solid var(--border) !important; padding: 10px 14px !important;
    text-align: left !important;
}
.stMarkdown table td {
    background-color: var(--bg-card) !important; color: var(--table-text) !important;
    border: 1px solid var(--border) !important; padding: 10px 14px !important;
}
.stMarkdown table tr:nth-child(even) td { background-color: var(--table-row-alt) !important; }

/* ============ DIALOGS & POPOVERS ============ */
[data-testid="stDialog"] {
    background-color: var(--bg-main) !important;
    border: 1px solid var(--border-dark) !important;
}
[data-testid="stDialog"] h2 { color: var(--text-bright) !important; }
[data-testid="stDialog"] label,
[data-testid="stDialog"] p,
[data-testid="stDialog"] span {
    color: var(--text-main) !important;
}

/* Fix inputs inside Dialogs */
[data-testid="stDialog"] .stTextInput input, 
[data-testid="stDialog"] .stTextArea textarea,
[data-testid="stDialog"] .stNumberInput input {
    background-color: var(--bg-card) !important;
    color: var(--text-main) !important;
    border: 1px solid var(--border-dark) !important;
}

/* Fix the popover menu (the three dots menu) */
[data-testid="stPopoverBody"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] span {
    color: var(--text-main) !important;
}
[data-testid="stPopoverBody"] button {
    background-color: transparent !important;
    color: var(--text-main) !important;
    border: 1px solid var(--border-dark) !important;
}
[data-testid="stPopoverBody"] button:hover {
    border-color: var(--primary) !important;
    color: var(--accent-text) !important;
}

/* ============ CHECKBOXES ============ */
[data-testid="stCheckbox"] label div[data-baseweb="checkbox"] div {
    background-color: var(--bg-card) !important; border: 1px solid var(--border-dark) !important;
}
[data-testid="stCheckbox"] label div[data-baseweb="checkbox"] [aria-checked="true"] {
    background-color: var(--btn-primary) !important; border-color: var(--btn-primary) !important;
}
[data-testid="stCheckbox"] svg { fill: var(--text-on-primary) !important; }

/* ============ MINIMALIST PROGRESS BAR ============ */
[data-testid="stProgress"] > div > div > div > div { 
    background-color: var(--primary) !important; 
}
[data-testid="stProgress"] > div > div > div { 
    background-color: var(--border) !important; 
}
[data-testid="stProgress"] p {
    color: var(--text-muted) !important;
    font-size: 0.85rem !important;
}

/* ============ MINIMALIST ALERTS (Callouts) ============ */
[data-testid="stAlert"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-left: 4px solid var(--primary) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
}
/* Override Streamlit's default harsh info/warning colors */
[data-testid="stAlert"] [data-testid="stAlertContentInfo"],
[data-testid="stAlert"] [data-testid="stAlertContentWarning"],
[data-testid="stAlert"] [data-testid="stAlertContentSuccess"],
[data-testid="stAlert"] [data-testid="stAlertContentError"] {
    background-color: transparent !important;
}
[data-testid="stAlert"] p { color: var(--text-main) !important; }
[data-testid="stAlert"] svg { fill: var(--text-main) !important; }

/* ============ INPUTS & SELECTBOXES ============ */
.stTextInput input, .stTextArea textarea { 
    background-color: var(--bg-card) !important; 
    border: 1px solid var(--border-dark) !important; 
    color: var(--text-main) !important; 
}
/* Fix the selectbox to match the theme */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-dark) !important;
    color: var(--text-main) !important;
}
[data-testid="stSelectbox"] svg { fill: var(--text-main) !important; }
/* Dropdown menu */
[data-baseweb="popover"] ul {
    background-color: var(--bg-card) !important;
}
[data-baseweb="popover"] li {
    color: var(--text-main) !important;
}
[data-baseweb="popover"] li:hover {
    background-color: var(--btn-primary) !important;
    color: var(--text-on-primary) !important;
}

/* ============ EXPANDERS & CODE ============ */
[data-testid="stExpander"] { background-color: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }
/* Code blocks: explicit colours so they never depend on the viewer's browser/OS theme */
.stCode, [data-testid="stCode"] { border-radius: var(--radius) !important; border: 1px solid var(--code-border) !important; background-color: var(--code-bg) !important; }
[data-testid="stCode"] > *, [data-testid="stCode"] pre, [data-testid="stCode"] code { background-color: var(--code-bg) !important; }
[data-testid="stCode"] pre, [data-testid="stCode"] code, [data-testid="stCode"] code span, [data-testid="stCode"] pre span {
    color: var(--code-text) !important; font-size: 0.95rem !important; line-height: 1.6 !important;
}
[data-testid="stCode"] button { background-color: transparent !important; color: var(--text-muted) !important; border: none !important; }
[data-testid="stCode"] button svg { color: var(--text-muted) !important; fill: var(--text-muted) !important; }
[data-testid="stCode"] button:hover svg { color: var(--accent-text) !important; fill: var(--accent-text) !important; }

/* ============ DOWNLOAD & FORM BUTTONS (not covered by .stButton) ============ */
.stDownloadButton > button, [data-testid="stFormSubmitButton"] > button { font-weight: 500 !important; border-radius: var(--radius) !important; transition: all 0.2s !important; }
.stDownloadButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] { background-color: var(--btn-primary) !important; color: var(--text-on-primary) !important; border: none !important; }
.stDownloadButton > button[kind="secondary"], [data-testid="stFormSubmitButton"] > button[kind="secondary"] { background-color: var(--bg-card) !important; color: var(--text-main) !important; border: 1px solid var(--border-dark) !important; }
.stDownloadButton > button[kind="secondary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="secondary"]:hover { border-color: var(--primary) !important; color: var(--accent-text) !important; }
[data-testid="stForm"] { background-color: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }

/* ============ DIALOG SURFACE, NUMBER INPUT, SELECT TEXT, PLACEHOLDERS ============ */
div[role="dialog"] { background-color: var(--bg-main) !important; }
[data-testid="stNumberInput"] input { background-color: var(--bg-card) !important; color: var(--text-main) !important; border: 1px solid var(--border-dark) !important; }
[data-testid="stNumberInput"] button { background-color: var(--bg-subtle) !important; color: var(--text-main) !important; border: 1px solid var(--border-dark) !important; }
[data-testid="stNumberInput"] button svg { fill: var(--text-main) !important; }
[data-baseweb="select"] div, [data-baseweb="select"] span { color: var(--text-main) !important; }
input::placeholder, textarea::placeholder { color: var(--text-muted) !important; opacity: 1 !important; }

/* ============ PROGRESS BAR + EXPANDER HEADERS (native surfaces follow the OS theme otherwise) ============ */
[data-testid="stProgress"] [data-testid="stProgressBarTrack"] { background-color: var(--border) !important; }
[data-testid="stProgress"] [data-testid="stProgressBarTrack"] > div { background-color: var(--primary) !important; }
[data-testid="stExpander"] details, [data-testid="stExpander"] summary { background-color: var(--bg-card) !important; color: var(--text-main) !important; }
[data-testid="stExpander"] summary:hover { background-color: var(--bg-subtle) !important; }
[data-testid="stExpander"] summary svg { color: var(--text-main) !important; fill: var(--text-main) !important; }

/* ============ PHONES ============ */
@media (max-width: 640px) {
    .block-container { padding: 1rem 0.75rem 3rem !important; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div > div { padding: 0.75rem !important; }
    .stMarkdown table { display: block; overflow-x: auto; }
}
</style>
"""

def inject_theme():
    dark_mode = st.session_state.get("dark_mode", False)
    theme_vars = DARK_THEME if dark_mode else LIGHT_THEME
    st.markdown(f"<style>{theme_vars}</style>\n{BASE_CSS}", unsafe_allow_html=True)

def get_context():
    return {"imsi": st.session_state.get("ctx_imsi", ""), "msisdn": st.session_state.get("ctx_msisdn", ""), "apn": st.session_state.get("ctx_apn", ""), "node": st.session_state.get("ctx_node", "")}

def load_paths(): return utils.load_json(DATA_DIR / "learning_paths.json", {"paths": []}).get("paths", [])
def load_scenarios(): return utils.load_json(DATA_DIR / "scenarios.json", {"scenarios": []}).get("scenarios", [])
def load_responses(): return utils.load_json(DATA_DIR / "command_responses.json", {"responses": {}}).get("responses", {})

def module_is_complete(m, states, visited, completed=None):
    completed = completed or set()
    has_checklist = False
    for b in m.get("blocks", []):
        if b.get("type") == "checklist":
            has_checklist = True
            cid = b.get("id", "default")
            items = b.get("items", [])
            done = sum(1 for x in states.get(cid, [])[:len(items)] if x)
            if done < len(items): return False
    if has_checklist: return True
    return m.get("id") in completed

def module_checklist_counts(m, states):
    done = total = 0
    for b in m.get("blocks", []):
        if b.get("type") == "checklist":
            cid = b.get("id", "default")
            items = b.get("items", [])
            total += len(items)
            done += sum(1 for x in states.get(cid, [])[:len(items)] if x)
    return done, total

def path_progress(path, modules_by_id, states, visited, completed=None):
    done = total = 0
    for mid in path.get("modules", []):
        m = modules_by_id.get(mid)
        if not m: continue
        total += 1
        if module_is_complete(m, states, visited, completed): done += 1
    pct = int(100 * done / total) if total else 0
    return done, total, pct

def go_to_module(target):
    if target in st.session_state.get("MODULE_BY_ID", {}):
        st.session_state["current_module"] = target
        st.session_state["page"] = "Modules"
        st.session_state["search"] = ""
        st.session_state["active_scenario"] = None
        st.session_state["scroll_to_top"] = True
        st.rerun()
    else:
        st.toast(f"Module '{target}' not found", icon="⚠️")

def session_log_md(operator):
    entries = db.read_session_log(operator)
    lines = [f"# Session Log — {operator}", f"Generated: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    for e in entries:
        tag = f" ({e.get('node', '')})" if e.get("node") else ""
        if e.get("k") == "note": lines.append(f"- **{e.get('t')}** NOTE: {e.get('title')}")
        else:
            lines.append(f"### {e.get('t')} — {e.get('title')}{tag}")
            if e.get("text"):
                lines.append("```mml"); lines.append(e["text"]); lines.append("```")
            lines.append("")
    return "\n".join(lines)

def troubleshooting_lines(operator):
    out = []
    for e in db.read_session_log(operator):
        stamp = e.get("t", "")[11:16]
        if e.get("k") == "note": out.append(f"- {stamp} NOTE: {e.get('title','')}")
        else:
            node = f" [{e.get('node','')}]" if e.get("node") else ""
            out.append(f"- {stamp}{node} {e.get('title','')}")
    return "\n".join(out)

def render_flow_player(block, key_prefix):
    steps = block.get("steps", [])
    if not steps: st.info("This flow has no steps defined."); return

    title = block.get("title", "")
    if title: st.markdown(f"### {title}")

    state_key = f"{key_prefix}_flow_idx"
    st.session_state.setdefault(state_key, 0)
    idx = min(st.session_state[state_key], len(steps) - 1)
    st.session_state[state_key] = idx
    step, total = steps[idx], len(steps)

    st.progress((idx + 1) / total, text=f"Step {idx + 1} of {total}")
    with st.container(border=True):
        actor, target = step.get("actor", ""), step.get("target", "")
        if actor or target: st.caption(f"**{actor}** → **{target}**")
        st.markdown(f"#### {step.get('message', '')}")
        if step.get("description"): st.write(step["description"])
        if step.get("command"): st.code(step["command"], language="text")
        if step.get("note"): st.info(step["note"])

    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    with c1:
        if st.button("← Back", key=f"{key_prefix}_flow_back", disabled=(idx == 0), use_container_width=True):
            st.session_state[state_key] = idx - 1; st.rerun()
    with c2:
        if st.button("Next →", key=f"{key_prefix}_flow_next", disabled=(idx >= total - 1), type="primary", use_container_width=True):
            st.session_state[state_key] = idx + 1; st.rerun()
    with c3:
        if st.button("⟲ Reset", key=f"{key_prefix}_flow_reset", use_container_width=True):
            st.session_state[state_key] = 0; st.rerun()
    with c4:
        opts = [f"{i + 1}. {s.get('message', '')[:40]}" for i, s in enumerate(steps)]
        jump_key = f"{key_prefix}_flow_jump"
        def _on_jump():
            st.session_state[state_key] = opts.index(st.session_state[jump_key])
        st.session_state[jump_key] = opts[idx]  # keep the dropdown in sync with Back/Next/Reset
        st.selectbox("Jump to step", opts, key=jump_key, on_change=_on_jump, label_visibility="collapsed")

def _render_mermaid(code, text_color, dark, height=520):
    """st.markdown shows a mermaid fence as plain code, so render it with Mermaid.js in an iframe.
    If the CDN cannot be reached (offline server) the diagram source is shown instead."""
    code = "\n".join(line.strip() for line in code.strip().splitlines())
    safe = html.escape(code)  # escaped so <br/> in labels survive as text for Mermaid
    page = f"""
    <body style="margin:0;background:transparent;color:{text_color};font-family:Segoe UI,Roboto,Arial,sans-serif;">
    <div class="mermaid" id="g">{safe}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
    <script>
      if (window.mermaid) {{
        mermaid.initialize({{startOnLoad: true, securityLevel: "strict", theme: "base",
                            themeVariables: {{lineColor: "{'#949BA4' if dark else '#5C5E66'}", fontFamily: "Segoe UI, Roboto, Arial"}}}});
      }} else {{
        document.getElementById("g").innerHTML = "<small>Diagram library not reachable. Diagram source:</small><pre>{safe}</pre>";
      }}
    </script></body>"""
    components.html(page, height=height, scrolling=True)

def render_topology_map(block, key_prefix):
    nodes = block.get("nodes", [])
    if not nodes: return
    title = block.get("title", "")
    if title: st.markdown(f"### {title}")

    dark = st.session_state.get("dark_mode", False)
    bg_color = "#2B2D31" if dark else "#FFFFFF"
    text_color = "#DBDEE1" if dark else "#313338"
    sub_color = "#1A1B1E" if dark else "#F2F3F5"
    primary = "#2EBD6B" if dark else "#00A859"

    mermaid_code = f"""
    graph TD
        classDef core fill:{bg_color},stroke:{primary},stroke-width:2px,color:{text_color};
        classDef edge fill:{sub_color},stroke:#888,stroke-width:1px,color:{text_color};
        RAN[eNodeB / BSC / RNC<br/>Radio Access] --> USN
        USN[USN<br/>MME / SGSN] --> HSS[HSS<br/>Subscriber DB]
        USN --> DRA[DRA<br/>Diameter Router]
        USN --> UGW[UGW<br/>SGW / PGW]
        UGW --> UPCF[UPCF<br/>Policy PCRF]
        UGW --> CBS[CBS<br/>Online Charging]
        UGW --> CG[CG<br/>Charging Gateway]
        UGW --> FW[FW<br/>Firewall]
        DRA --> UPCF
        DRA --> CBS
        FW --> Internet((Internet))
        class USN,UGW,HSS,DRA,UPCF,CBS,CG core;
        class FW edge;
        class RAN edge;
    """
    _render_mermaid(mermaid_code, text_color, dark)
    st.markdown("---")
    st.caption("Select a node below to view its full operational context:")

    groups = {}
    for n in nodes: groups.setdefault(n.get("group", "Other"), []).append(n)
    selected_key = f"{key_prefix}_node_selected"

    for group_name, group_nodes in groups.items():
        st.caption(group_name.upper())
        cols = st.columns(min(len(group_nodes), 4))
        for i, n in enumerate(group_nodes):
            with cols[i % 4]:
                selected = st.session_state.get(selected_key) == n["id"]
                if st.button(n.get("label", n["id"]), key=f"{key_prefix}_node_{n['id']}", type="primary" if selected else "secondary", use_container_width=True):
                    st.session_state[selected_key] = n["id"]; st.rerun()
        st.markdown("")

    selected_id = st.session_state.get(selected_key)
    if selected_id:
        selected = next((n for n in nodes if n["id"] == selected_id), None)
        if selected:
            with st.container(border=True):
                st.markdown(f"#### {selected.get('label','')} — {selected.get('role','')}")
                st.write(selected.get("description", ""))
                if selected.get("interfaces"): st.caption("Interfaces: " + " · ".join(f"`{i}`" for i in selected["interfaces"]))

# --- scenario callbacks (a click does one clean rerun) ---
def _sc_open(sid, op, status):
    if status == "not_started": db.save_scenario_progress(op, sid, "in_progress", 0)
    elif status == "complete": db.save_scenario_progress(op, sid, "complete", 0)  # review from the first step
    st.session_state["active_scenario"] = sid

def _sc_close(): st.session_state["active_scenario"] = None
def _sc_pick(pk, i): st.session_state[pk] = i
def _sc_retry(pk): st.session_state.pop(pk, None)

def _sc_advance(pk, op, sid, idx, last, was_complete):
    st.session_state.pop(pk, None)
    if last:
        db.save_scenario_progress(op, sid, "complete", idx)
        st.session_state["active_scenario"] = None
    else:
        db.save_scenario_progress(op, sid, "complete" if was_complete else "in_progress", idx + 1)

def page_scenarios():
    st.markdown("## Practice scenarios")
    st.caption("Pick a choice, see the outcome, then continue. Nothing here touches the live network.")
    scenarios = load_scenarios()
    if not scenarios: st.info("No scenarios defined."); return

    op = st.session_state.get("operator") or "guest"
    for sc in scenarios:
        sid = sc["id"]
        progress = db.get_scenario_progress(op, sid)
        status = progress.get("status", "not_started")
        total = len(sc.get("steps", []))
        state_text = {"complete": "Complete", "in_progress": f"In progress · step {progress.get('step', 0) + 1} of {total}"}.get(status, "")
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{sc.get('title', '')}**")
                st.caption(sc.get("description", ""))
                if state_text: st.caption(state_text)
            with c2:
                label = {"not_started": "Start", "in_progress": "Resume"}.get(status, "Review")
                st.button(label, key=f"sc_{sid}", use_container_width=True, type="secondary" if status == "complete" else "primary",
                          on_click=_sc_open, args=(sid, op, status))

def render_active_scenario():
    scenarios = load_scenarios()
    sid = st.session_state.get("active_scenario")
    sc = next((s for s in scenarios if s["id"] == sid), None)
    if not sc:
        st.session_state["active_scenario"] = None
        st.rerun()
        return

    op = st.session_state.get("operator") or "guest"
    progress = db.get_scenario_progress(op, sid)
    steps = sc.get("steps", [])
    st.button("← All scenarios", key="sc_exit", on_click=_sc_close)
    if not steps: st.warning("This scenario has no steps."); return

    idx = min(progress.get("step", 0), len(steps) - 1)
    step = steps[idx]
    last = idx == len(steps) - 1
    was_complete = progress.get("status") == "complete"
    pk = f"sc_{sid}_{idx}_picked"
    choices = step.get("choices", [])
    picked = st.session_state.get(pk)

    st.markdown(f"### {sc.get('title', '')}")
    with st.container(border=True):
        st.caption(f"STEP {idx + 1} OF {len(steps)}")
        st.write(step.get("situation", ""))

    advance = dict(key=f"sc_{sid}_{idx}_next", use_container_width=True, type="primary", on_click=_sc_advance, args=(pk, op, sid, idx, last, was_complete))
    next_label = "Finish scenario" if last else "Next step →"

    if not choices:  # an information-only step
        st.button(next_label, **advance)
        return

    st.markdown("**What do you do?**")
    for i, ch in enumerate(choices):
        st.button(ch.get("text", ""), key=f"sc_{sid}_{idx}_choice_{i}", use_container_width=True,
                  type="primary" if picked == i else "secondary", on_click=_sc_pick, args=(pk, i))

    if picked is not None and picked < len(choices):
        choice = choices[picked]
        correct = choice.get("correct", False)
        feedback = choice.get("feedback")
        if not feedback or str(feedback).strip() == "None":
            feedback = "Correct." if correct else "Not the best next step."
        with st.container(border=True):
            (st.success if correct else st.error)(feedback)
            if choice.get("explain"): st.caption(choice["explain"])
        c1, c2 = st.columns(2)
        with c1: st.button("Try another choice", key=f"sc_{sid}_{idx}_retry", use_container_width=True, on_click=_sc_retry, args=(pk,))
        with c2: st.button(next_label, **advance)

def _term_run():
    cmd = (st.session_state.get("terminal_input") or "").strip()
    if cmd:
        _execute_mock(cmd.upper(), load_responses())
        del st.session_state["terminal_history"][:-30]
    st.session_state["terminal_input"] = ""  # clear the box so the next command can be typed straight away

def _term_clear(): st.session_state["terminal_history"] = []

def page_terminal():
    st.markdown("## Practice terminal")
    st.caption("Type an MML command and press Enter. Outputs are mock; nothing here touches the live network.")
    st.session_state.setdefault("terminal_history", [])
    st.text_input("MML command", placeholder="e.g.  DSP SMCTXT;", key="terminal_input", on_change=_term_run, label_visibility="collapsed")
    known = list(load_responses())
    if known: st.caption("Commands it understands: " + ", ".join(f"`{k}`" for k in known[:10]) + (" ..." if len(known) > 10 else ""))
    else: st.info("No mock responses defined.")
    history = st.session_state["terminal_history"]
    if history: st.button("Clear", key="term_clear", on_click=_term_clear)
    else: st.caption("Command history appears here.")
    for entry in reversed(history):
        st.markdown(f"`> {entry['cmd']}`")
        if entry.get("found"): st.code(entry["output"], language="text")
        else:
            hint = (" Did you mean " + " or ".join(f"`{x}`" for x in entry.get("suggest", [])) + "?") if entry.get("suggest") else ""
            st.warning(f"No mock response for `{entry['cmd']}`." + hint)
    if st.session_state.get("edit_mode"): _response_editor()

_SAMPLE_VALUES = {"imsi": "650010114416123", "msisdn": "265888073002"}
_STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

def _personalise(output):
    """Use the engineer's Subscriber Context in the sample output, and stamp the header with the current time."""
    ctx = get_context()
    for key, sample in _SAMPLE_VALUES.items():
        if (ctx.get(key) or "").strip(): output = output.replace(sample, ctx[key].strip())
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join(_STAMP_RE.sub(now, line, count=1) if line.startswith("+++") else line for line in output.split("\n"))

def _execute_mock(cmd, responses):
    normalized = cmd.rstrip(";").strip()
    keyed = [(k.upper().rstrip(";").strip(), v) for k, v in responses.items()]
    hit = next((v for k, v in keyed if k == normalized), None)
    if hit is None:  # otherwise the longest command the input starts with (so "DSP AB" beats "DSP A")
        hit = next((v for k, v in sorted(keyed, key=lambda kv: -len(kv[0])) if normalized.startswith(k)), None)
    entry = {"cmd": cmd, "found": hit is not None, "output": _personalise(hit) if hit is not None else None}
    if hit is None: entry["suggest"] = difflib.get_close_matches(normalized, [k for k, _ in keyed], n=2, cutoff=0.6)
    st.session_state["terminal_history"].append(entry)

def save_response(key, output, path=None):
    path = path or DATA_DIR / "command_responses.json"
    data = utils.load_json(path, {"responses": {}})
    data.setdefault("responses", {})[key.strip().upper().rstrip(";").strip()] = output
    utils.save_json(path, data)

def delete_response(key, path=None):
    path = path or DATA_DIR / "command_responses.json"
    data = utils.load_json(path, {"responses": {}})
    data.setdefault("responses", {}).pop(key, None)
    utils.save_json(path, data)

def _save_response_cb(choice):
    key = st.session_state.get("term_edit_key", "") if choice == "New command" else choice
    save_response(key, st.session_state.get(f"term_edit_out_{choice}", ""))
    if choice == "New command":
        st.session_state["term_edit_key"] = ""
        st.session_state["term_edit_out_New command"] = ""
    st.toast("Response saved")

def _delete_response_cb(choice):
    delete_response(choice)
    st.session_state["term_edit_choice"] = "New command"
    st.toast("Response deleted")

def _response_editor():
    responses = load_responses()
    with st.expander("Add or edit a mock response"):
        choice = st.selectbox("Command", ["New command", *responses], key="term_edit_choice")
        new = choice == "New command"
        key = st.text_input("Command text", key="term_edit_key", placeholder="e.g. LST APN") if new else choice
        output = st.text_area("Output shown to the engineer", value="" if new else responses[choice], height=220, key=f"term_edit_out_{choice}")
        c1, c2 = st.columns(2)
        with c1:
            st.button("Save response", key="term_edit_save", use_container_width=True, disabled=not ((key or "").strip() and output.strip()),
                      on_click=_save_response_cb, args=(choice,))
        with c2:
            if not new: st.button("Delete", key="term_edit_delete", use_container_width=True, on_click=_delete_response_cb, args=(choice,))
