# views/home.py
import streamlit as st
import config
import sop_interactive as si
import db

def render_home(modules_by_id, open_module_cb):
    operator = st.session_state.get("operator", "").strip()
    st.markdown(f"## Welcome, {operator}" if operator else f"## {config.BRANDING['title']}")
    if config.BRANDING.get("welcome"): st.caption(config.BRANDING["welcome"])

    paths = si.load_paths() or [{"title": "All modules", "modules": list(modules_by_id)}]  # no learning path defined: list everything

    states = db.get_checklists(operator)
    visited = db.load_visited(operator)
    completed = db.get_completed_modules(operator)

    primary = paths[0]
    mids = [m for m in primary.get("modules", []) if modules_by_id.get(m)]
    done, total, pct = si.path_progress(primary, modules_by_id, states, visited, completed)
    next_mid = next((mid for mid in mids if not si.module_is_complete(modules_by_id[mid], states, visited, completed)), None)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"**{primary.get('title', 'Learning path')}**")
        st.caption(f"{done} of {total} complete")
        st.progress(pct / 100)
    with c2:
        if next_mid:
            st.button(f"Continue: {modules_by_id[next_mid].get('title')}", type="primary", use_container_width=True, on_click=open_module_cb, args=(next_mid,))
        elif pct == 100:
            st.success("Path complete")

    if primary.get("description"): st.caption(primary["description"])

    for n, mid in enumerate(mids, 1):
        m = modules_by_id[mid]
        d, t = si.module_checklist_counts(m, states)
        complete = si.module_is_complete(m, states, visited, completed)
        status = "Complete" if complete else (f"{d} of {t} done" if t > 0 and d > 0 else ("Opened" if mid in visited else "Not started"))
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"**{n}. {m['title']}**")
            st.caption(status + (f" · {m['subtitle']}" if m.get("subtitle") else ""))
        with c2:
            st.button("Open", key=f"step_{mid}", use_container_width=True, type="secondary", on_click=open_module_cb, args=(mid,))
