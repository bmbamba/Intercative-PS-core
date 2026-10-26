# views/commands.py
import streamlit as st
import utils


def collect_all_commands(modules):
    """Every command block (and step command) in the SOP, duplicates removed."""
    seen, rows = set(), []
    for m in modules:
        for b in m.get("blocks", []):
            found = []
            if b.get("type") == "command" and b.get("code"):
                found.append((b.get("title") or "Command", b["code"]))
            elif b.get("type") == "steps":
                found += [(s.get("title") or "Step", s["command"]) for s in b.get("items", []) if isinstance(s, dict) and s.get("command")]
            for title, code in found:
                if code.strip() in seen: continue
                seen.add(code.strip())
                rows.append({"module": m.get("title", ""), "title": title, "code": code})
    return rows


def page_commands(modules, get_context):
    st.title("Commands")
    st.caption("Every command in the SOP in one place. Placeholders fill in from Subscriber context.")
    rows = collect_all_commands(modules)
    c1, c2 = st.columns([4, 1])
    with c1:
        q = st.text_input("Filter commands", key="cmd_filter", placeholder="Filter by name, command or module", label_visibility="collapsed").strip().lower()
    with c2:
        read_only = st.toggle("Read-only", key="cmd_read_only", help="Hide commands that change configuration.")
    ctx = get_context()
    shown = []
    for r in rows:
        code = utils.substitute_placeholders(r["code"], ctx)
        if read_only and utils.is_change_command(code): continue
        if q and q not in f"{r['title']} {code} {r['module']}".lower(): continue
        shown.append((r, code))
    st.caption(f"{len(shown)} of {len(rows)} commands")
    for r, code in shown:
        st.markdown(f"**{r['title']}**")
        st.caption(r["module"] + ("  ·  changes configuration" if utils.is_change_command(code) else ""))
        st.code(code, language="mml")
