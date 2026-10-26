# db.py
import sqlite3
import json
import datetime
import streamlit as st
from config import DB_PATH, BACKUP_DIR, MASK_SUBSCRIBER_IN_LOGS
import utils

def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")  # readers no longer block the writer when several people use it
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_data (operator TEXT, key TEXT, value TEXT, PRIMARY KEY (operator, key))''')
        c.execute('''CREATE TABLE IF NOT EXISTS checklists (operator TEXT, checklist_id TEXT, state TEXT, PRIMARY KEY (operator, checklist_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS session_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, operator TEXT, time TEXT, kind TEXT, title TEXT, text TEXT, node TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS ts_progress (operator TEXT, problem_id TEXT, step_idx INTEGER, PRIMARY KEY (operator, problem_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, operator TEXT, module_id TEXT, text TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS visited (operator TEXT, module_id TEXT, PRIMARY KEY (operator, module_id))''')
        conn.commit()

init_db()

def backup_db(keep=7):
    """One copy of the database per day in backups/, newest `keep` kept. Cheap to call on every run."""
    try:
        target = BACKUP_DIR / f"sop_app_{datetime.date.today():%Y%m%d}.db"
        if target.exists(): return
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        src, dst = sqlite3.connect(DB_PATH, timeout=10), sqlite3.connect(target)
        with dst: src.backup(dst)
        src.close(); dst.close()
        for old in sorted(BACKUP_DIR.glob("sop_app_*.db"))[:-keep]: old.unlink(missing_ok=True)
    except Exception:
        pass

# --- USER DATA ---
@st.cache_data(ttl=60)
def get_user_data(operator, key, default):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM user_data WHERE operator=? AND key=?", (operator, key))
        row = c.fetchone()
        return json.loads(row[0]) if row else default

def set_user_data(operator, key, value):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO user_data (operator, key, value) VALUES (?, ?, ?)", (operator, key, json.dumps(value)))
            conn.commit()
        get_user_data.clear()
    except sqlite3.Error as e:
        st.error(f"Database error saving user data: {e}")

# --- VISITED ---
@st.cache_data(ttl=60)
def load_visited(operator):
    if not operator: return set()
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("SELECT module_id FROM visited WHERE operator=?", (operator,))
            return {row[0] for row in c.fetchall()}
    except sqlite3.Error: return set()

def mark_visited(operator, module_id):
    if not operator: return
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO visited (operator, module_id) VALUES (?, ?)", (operator, module_id))
            conn.commit()
        load_visited.clear()
    except sqlite3.Error: pass

# --- CHECKLISTS ---
@st.cache_data(ttl=60)
def get_checklists(operator):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("SELECT checklist_id, state FROM checklists WHERE operator=?", (operator,))
            return {row[0]: json.loads(row[1]) for row in c.fetchall()}
    except sqlite3.Error: return {}

def save_checklist(operator, checklist_id, state):
    if not operator: return
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO checklists (operator, checklist_id, state) VALUES (?, ?, ?)", (operator, checklist_id, json.dumps(state)))
            conn.commit()
        get_checklists.clear()
    except sqlite3.Error as e:
        st.error(f"Database error saving checklist: {e}")

# --- COMPLETED MODULES ---
# Not cached itself: wraps get_user_data, which is cached and cleared on every save.
def get_completed_modules(operator):
    if not operator: return set()
    val = get_user_data(operator, "completed_modules", [])
    return set(val)

def save_completed_modules(operator, ids):
    set_user_data(operator, "completed_modules", list(ids))

# --- SCENARIO PROGRESS ---
def get_scenario_progress(operator, sid):
    return get_user_data(operator, f"scenario_{sid}", {"status": "not_started", "step": 0})

def save_scenario_progress(operator, sid, status, step):
    set_user_data(operator, f"scenario_{sid}", {"status": status, "step": step})

# --- TROUBLESHOOTING PROGRESS ---
@st.cache_data(ttl=60)
def get_ts_progress(operator):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT problem_id, step_idx FROM ts_progress WHERE operator=?", (operator,))
        return {row[0]: row[1] for row in c.fetchall()}

def save_ts_progress(operator, problem_id, step_idx):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO ts_progress (operator, problem_id, step_idx) VALUES (?, ?, ?)", (operator, problem_id, step_idx))
            conn.commit()
        get_ts_progress.clear()
    except sqlite3.Error as e:
        st.error(f"Database error saving TS progress: {e}")

# --- FEEDBACK ("Report a problem" on a module) ---
def add_feedback(operator, module_id, text):
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("INSERT INTO feedback (time, operator, module_id, text) VALUES (?, ?, ?, ?)", (now, operator or "guest", module_id, text))
            conn.commit()
        read_feedback.clear()
    except sqlite3.Error as e:
        st.error(f"Database error saving feedback: {e}")

@st.cache_data(ttl=10)
def read_feedback(limit=200):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        rows = conn.execute("SELECT time, operator, module_id, text FROM feedback ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"t": r[0], "operator": r[1], "module_id": r[2], "text": r[3]} for r in rows]

# --- SESSION LOGS ---
def append_session_log(operator, kind, title, text="", node=""):
    now = datetime.datetime.now().isoformat(timespec="seconds")
    if MASK_SUBSCRIBER_IN_LOGS:
        title, text, node = utils.mask_subscriber(title), utils.mask_subscriber(text), utils.mask_subscriber(node)
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO session_logs (operator, time, kind, title, text, node) VALUES (?, ?, ?, ?, ?, ?)", (operator, now, kind, title, text, node))
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database error writing log: {e}")

@st.cache_data(ttl=10)
def read_session_log(operator, limit=500):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT time, kind, title, text, node FROM session_logs WHERE operator=? ORDER BY id DESC LIMIT ?", (operator, limit))
        rows = c.fetchall()
        return [{"t": r[0], "k": r[1], "title": r[2], "text": r[3], "node": r[4], "operator": operator} for r in reversed(rows)]

@st.cache_data(ttl=10)
def read_team_activity(limit=500):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT operator, time, kind, title, text, node FROM session_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return [{"operator": r[0], "t": r[1], "k": r[2], "title": r[3], "text": r[4], "node": r[5]} for r in rows]


def reset_user_progress(operator):
    if not operator: return
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM checklists WHERE operator=?", (operator,))
            c.execute("DELETE FROM visited WHERE operator=?", (operator,))
            c.execute("DELETE FROM user_data WHERE operator=? AND (key='completed_modules' OR substr(key,1,9)='scenario_')", (operator,))
            c.execute("DELETE FROM ts_progress WHERE operator=?", (operator,))
            conn.commit()
        # Clear all caches so the UI updates instantly
        get_checklists.clear()
        load_visited.clear()
        get_user_data.clear()
        get_ts_progress.clear()
        st.toast("Progress reset successfully!", icon="✅")
    except sqlite3.Error as e:
        st.error(f"Database error resetting progress: {e}")