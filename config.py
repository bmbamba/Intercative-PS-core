# config.py
import os
from pathlib import Path

import json

APP_DIR = Path(__file__).parent
# Each SOP keeps its content (modules.json, data/, screenshots/, branding.json, backups/) in its own folder.
# Set SOP_HOME to run a different SOP on the same code. Default: this folder.
CONTENT_DIR = Path(os.environ.get("SOP_HOME", str(APP_DIR))).resolve()
DATA_DIR = CONTENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = CONTENT_DIR / "screenshots"
MODULES_PATH = CONTENT_DIR / "modules.json"
DB_PATH = Path(os.environ.get("PS_SOP_DB", str(DATA_DIR / "sop_app.db")))
BACKUP_DIR = Path(os.environ.get("PS_SOP_BACKUPS", str(CONTENT_DIR / "backups")))

# Name, welcome line and hidden pages for this SOP. Override in <content folder>/branding.json.
BRANDING = {
    "title": "PS Core SOP",
    "tagline": "TNM · Huawei USN / UGW / HSS",
    "welcome": "TNM Packet-Switched Core: procedures, checks and troubleshooting for Huawei USN / UGW / HSS.",
    "icon": "🚀",
    "hide_pages": [],       # e.g. ["Practice Terminal", "Ticket Builder"]
    "show_context": True,   # the Subscriber context box (IMSI / MSISDN / APN / Node)
}
try:
    BRANDING.update(json.loads((CONTENT_DIR / "branding.json").read_text(encoding="utf-8")))
except Exception:
    pass

# Application routes. "Home" and "Modules" can never be hidden.
_HIDDEN = {p for p in BRANDING.get("hide_pages", []) if p not in ("Home", "Modules")}
PAGES = [p for p in [
    "Home", "Scenarios", "Practice Terminal", "Commands", "Modules", "Templates",
    "Error Codes", "Troubleshooting", "Team Activity", "Session Log", "Ticket Builder", "Feedback",
] if p not in _HIDDEN]

# Default Session State
DEFAULT_STATE = {
    "operator": "", "current_module": "start-here", "page": "Home",
    "search": "", "ctx_imsi": "", "ctx_msisdn": "", "ctx_apn": "", "ctx_node": "",
    "copy_all_result": None, "copy_all_module": None, "ticket_text": None,
    "active_scenario": None, "edit_mode": False, "scroll_to_top": False,
}

# Text Replacement Constants
PLACEHOLDER_KEYS = {
    "imsi":   ["650010114416xx", "6500101xxxx", "650011012367249", "6500101114416xx"],
    "msisdn": ["265888073002", "2658873002", "26588xxxx", "26588807300x"],
    "apn":    ["apnX", "apnx", "apnspx"],
    "node":   ["LLG vUSN", "LMB vUSN", "LLG vCGW", "LMB vDGW"],
}

# Sidebar layout: PRIMARY pages are always visible, TOOLS sit in a collapsed group.
# ("Modules" is reached from the module list, so it is not a nav button.)
NAV_PRIMARY = [p for p in ["Home", "Commands", "Scenarios", "Practice Terminal"] if p not in _HIDDEN]
NAV_TOOLS = [p for p in ["Templates", "Error Codes", "Troubleshooting", "Ticket Builder", "Session Log", "Team Activity", "Feedback"] if p not in _HIDDEN]

# Screenshots: shrink what is sent to the browser, and keep module pages short.
IMAGE_MAX_WIDTH = 1200          # px, larger screenshots are scaled down (cached)
THUMB_WIDTH = 400               # px, Screenshot Library thumbnails
COLLAPSE_SCREENSHOTS = True     # False = show every screenshot inline

# Mask IMSI / MSISDN when commands are written to the session log (the log is shared via Team Activity).
# Set to False if engineers need the full numbers in saved logs.
MASK_SUBSCRIBER_IN_LOGS = True

# Optional roster. Leave empty for a free-text name box; list names to get a dropdown instead
# (avoids typos and look-alike names in Team Activity). Example: ["Bonaventure", "Chisomo"]
OPERATORS = []
