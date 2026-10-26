# app.py
import hmac
import os
import streamlit as st
import streamlit.components.v1 as components

import compat  # noqa: F401  (patches st.* for newer Streamlit; must load before the views run)

import config
import db
import utils
import sop_interactive as si
from views.home import render_home
from views.module import render_module
from views import admin, commands

st.set_page_config(
    page_title=config.BRANDING["title"],
    page_icon=config.BRANDING["icon"],
    layout="wide",
    initial_sidebar_state="auto",  # open on desktop, closed on phones
)

if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False
for k, v in config.DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v

si.inject_theme()
db.backup_db()

MODULES = utils.load_modules()
MODULE_BY_ID = {m["id"]: m for m in MODULES}
if not MODULES:
    st.error(f"No modules found. Expected a modules.json in {config.CONTENT_DIR}. Create a new SOP with: python tools/new_sop.py")
    st.stop()
if st.session_state["current_module"] not in MODULE_BY_ID:
    st.session_state["current_module"] = MODULES[0]["id"]
st.session_state["MODULE_BY_ID"] = MODULE_BY_ID

# Deep links: ?module=<id> or ?page=<name> opens that view on first load
if not st.session_state.get("_url_loaded"):
    st.session_state["_url_loaded"] = True
    _qm, _qp = st.query_params.get("module"), st.query_params.get("page")
    if _qm in MODULE_BY_ID:
        st.session_state["current_module"], st.session_state["page"] = _qm, "Modules"
    elif _qp in config.PAGES:
        st.session_state["page"] = _qp

# =========================================================
# DIALOGS & CALLBACKS
# =========================================================
@st.dialog("Reset Progress")
def dlg_reset_progress():
    st.warning("Are you sure you want to reset all your progress? This will uncheck all checklists, reset your scenarios, and clear your read history.")
    st.caption("Your session logs (commands you've logged) will NOT be deleted.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, reset everything", type="primary", use_container_width=True):
            db.reset_user_progress(st.session_state.get("operator", ""))
            # Widgets keep their own copy of progress in session_state and would write it straight back to the DB
            for k in list(st.session_state.keys()):
                if k.startswith(("chk_", "ts_step_", "ts_path_")) or k.endswith(("_flow_idx", "_flow_jump", "_picked")):
                    del st.session_state[k]
            st.session_state["current_module"] = MODULES[0]["id"]
            st.session_state["active_scenario"] = None
            st.session_state["scroll_to_top"] = True
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

def _admin_password():
    """Set PS_SOP_ADMIN_PASSWORD (or admin_password in .streamlit/secrets.toml) to lock Admin Edit Mode."""
    pw = os.environ.get("PS_SOP_ADMIN_PASSWORD", "")
    if not pw:
        try: pw = str(st.secrets.get("admin_password", ""))
        except Exception: pw = ""
    return pw

def _check_admin():
    entered = st.session_state.get("admin_pw_input", "")
    ok = hmac.compare_digest(entered.encode(), _admin_password().encode())
    st.session_state["edit_mode"] = ok
    st.session_state["admin_bad"] = bool(entered) and not ok
    st.session_state["admin_pw_input"] = ""

def _exit_admin(): st.session_state["edit_mode"] = False

def admin_mode_control():
    if not _admin_password():  # no password configured: plain toggle (anyone can edit)
        st.toggle("Admin edit mode", key="edit_mode", help="Shows the ⋮ edit menus on blocks.")
    elif st.session_state.get("edit_mode"):
        st.button("Exit admin edit mode", key="exit_admin", use_container_width=True, on_click=_exit_admin)
    else:
        st.text_input("Admin password", type="password", key="admin_pw_input", placeholder="Admin password to edit",
                      label_visibility="collapsed", on_change=_check_admin)
        if st.session_state.get("admin_bad"): st.caption("Wrong password.")

def cb_nav_page(page_name):
    st.session_state["page"] = page_name
    st.session_state["active_scenario"] = None
    st.session_state["search"] = ""
    st.session_state["scroll_to_top"] = True

def cb_open_module(mid):
    op = st.session_state.get("operator", "")
    if op: db.mark_visited(op, mid)
    st.session_state["current_module"] = mid
    st.session_state["page"] = "Modules"
    st.session_state["search"] = ""
    st.session_state["active_scenario"] = None
    st.session_state["copy_all_result"] = None
    st.session_state["copy_all_module"] = None
    st.session_state["scroll_to_top"] = True

def cb_clear_search(): 
    st.session_state["search"] = ""

def cb_clear_context():
    for k in ("ctx_imsi", "ctx_msisdn", "ctx_apn", "ctx_node"): 
        st.session_state[k] = ""

# =========================================================
# SIDEBAR
# =========================================================
def nav_button(p):
    is_active = (st.session_state["page"] == p) and not st.session_state.get("active_scenario")
    st.button(p, key=f"nav_pg_{p}", use_container_width=True, type="primary" if is_active else "secondary", on_click=cb_nav_page, args=(p,))

def render_sidebar():
    page = st.session_state["page"]
    op = st.session_state.get("operator", "")
    searching = bool(st.session_state.get("search"))
    with st.sidebar:
        st.markdown(f"## {config.BRANDING['title']}")
        if config.BRANDING.get("tagline"): st.caption(config.BRANDING["tagline"])
        if config.OPERATORS:
            st.selectbox("Your name", ["", *config.OPERATORS], key="operator", format_func=lambda n: n or "Select your name", label_visibility="collapsed")
        else:
            st.text_input("Your name", key="operator", placeholder="Your name", label_visibility="collapsed")
        st.text_input("Search", key="search", placeholder="Search modules…", label_visibility="collapsed")
        if searching:
            st.button("Clear search", key="clear_search", use_container_width=True, on_click=cb_clear_search)

        st.divider()
        for p in config.NAV_PRIMARY: nav_button(p)
        if config.NAV_TOOLS:
            with st.expander("Tools", expanded=(page in config.NAV_TOOLS)):
                for p in config.NAV_TOOLS: nav_button(p)

        st.divider()
        states = db.get_checklists(op)
        completed = db.get_completed_modules(op)
        current_mid = st.session_state["current_module"] if (page == "Modules" and not searching and not st.session_state.get("active_scenario")) else None
        by_cat = {}
        for m in MODULES: by_cat.setdefault(m.get("category", "Other"), []).append(m)
        for cat, mods in by_cat.items():
            with st.expander(cat, expanded=any(m["id"] == current_mid for m in mods)):
                for m in mods:
                    d, t = si.module_checklist_counts(m, states)
                    done = (t > 0 and d == t) or (t == 0 and m["id"] in completed)
                    st.button(f"{m['title']}{' ✓' if done else ''}", key=f"nav_{m['id']}", use_container_width=True,
                              type="primary" if m["id"] == current_mid else "secondary", on_click=cb_open_module, args=(m["id"],))

        st.divider()
        if config.BRANDING.get("show_context", True):
            with st.expander("Subscriber context"):
                st.text_input("IMSI", key="ctx_imsi", placeholder="650010114416xx")
                st.text_input("MSISDN", key="ctx_msisdn", placeholder="265888073002")
                st.text_input("APN", key="ctx_apn", placeholder="apnX")
                st.text_input("Node", key="ctx_node", placeholder="LLG vUSN")
                st.button("Clear context", key="clear_ctx", use_container_width=True, on_click=cb_clear_context)
        with st.expander("Settings"):
            st.toggle("Dark mode", key="dark_mode")
            admin_mode_control()
            if st.button("Reset my progress", use_container_width=True, type="secondary"):
                dlg_reset_progress()

# =========================================================
# ROUTER
# =========================================================
render_sidebar()
page = st.session_state["page"]

# Anchor that the scroll-to-top script jumps to
st.markdown('<div id="page-top-anchor"></div>', unsafe_allow_html=True)

if st.session_state.get("active_scenario"): 
    si.render_active_scenario()
elif st.session_state.get("search"): 
    admin.page_search(MODULES, cb_open_module)
elif page == "Modules": 
    render_module(MODULE_BY_ID, cb_open_module, si.get_context)
elif page == "Home": 
    render_home(MODULE_BY_ID, cb_open_module)
elif page == "Scenarios": 
    si.page_scenarios()
elif page == "Practice Terminal": 
    si.page_terminal()
elif page == "Commands": 
    commands.page_commands(MODULES, si.get_context)
elif page == "Templates": 
    admin.page_templates(si.get_context)
elif page == "Error Codes": 
    admin.page_error_codes()
elif page == "Troubleshooting": 
    admin.page_troubleshooting()
elif page == "Team Activity": 
    admin.page_team_activity()
elif page == "Session Log": 
    admin.page_session_log()
elif page == "Ticket Builder": 
    admin.page_ticket_builder(si.get_context)
elif page == "Feedback": 
    admin.page_feedback(MODULE_BY_ID)

# Keep the address bar in step with the view so it can be shared as a link
_url = {"module": st.session_state["current_module"]} if st.session_state["page"] == "Modules" else {"page": st.session_state["page"]}
if dict(st.query_params) != _url: st.query_params.from_dict(_url)

# --- Scroll to top after navigation (retries for 1.5 s so late-loading images cannot push the page back down) ---
if st.session_state.get("scroll_to_top"):
    st.session_state["scroll_to_top"] = False
    components.html(
        """
        <script>
            function forceScrollToTop() {
                const doc = window.parent.document;
                
                // 1. Scroll the specific anchor we just added
                const anchor = doc.getElementById('page-top-anchor');
                if (anchor) {
                    anchor.scrollIntoView({ behavior: 'instant', block: 'start' });
                }
                
                // 2. Force all known Streamlit scroll containers to top
                const containers = [
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('.main'),
                    doc.querySelector('section.main')
                ];
                containers.forEach(c => {
                    if (c) {
                        c.scrollTop = 0;
                        c.scrollTo(0, 0);
                    }
                });
                
                // 3. Force window to top
                window.parent.scrollTo(0, 0);
            }
            
            // Run immediately
            forceScrollToTop();
            
            // Keep forcing it for 1.5 seconds to catch image loading
            let attempts = 0;
            const interval = setInterval(() => {
                forceScrollToTop();
                attempts++;
                if (attempts > 15) clearInterval(interval); 
            }, 100);
        </script>
        """,
        height=0,
    )