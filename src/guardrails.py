from typing import Dict, Any, Optional, List

import pygetwindow as gw

from config import ALLOWLIST_APPS, DANGEROUS_KEYWORDS, ENFORCE_ALLOWLIST


SENSITIVE_KEYWORDS = [
    "password",
    "passwd",
    "token",
    "apikey",
    "api key",
    "secret",
]


def active_window_title() -> str:
    try:
        win = gw.getActiveWindow()
        return win.title if win and win.title else ""
    except Exception:
        return ""


def is_allowed_window(allowlist: Optional[List[str]] = None) -> bool:
    if not ENFORCE_ALLOWLIST:
        return True
    title = active_window_title().lower()
    if not title:
        return False
    apps = allowlist if allowlist is not None else ALLOWLIST_APPS
    return any(a.lower() in title for a in apps)


def is_allowed_app(app_name: str, allowlist: Optional[List[str]] = None) -> bool:
    if not ENFORCE_ALLOWLIST:
        return True
    app = app_name.lower()
    apps = allowlist if allowlist is not None else ALLOWLIST_APPS
    return any(a.lower() in app for a in apps)


def danger_reason(action: Dict[str, Any]) -> Optional[str]:
    act = action.get("action", "")
    args = action.get("args", {})

    if act == "open_app":
        app = str(args.get("app", "")).lower()
        for k in DANGEROUS_KEYWORDS:
            if k in app:
                return f"Opening dangerous app: {app}"

    if act == "type":
        text = str(args.get("text", "")).lower()
        for k in SENSITIVE_KEYWORDS:
            if k in text:
                return "Typing sensitive data"

    if act == "hotkey":
        keys = [str(k).lower() for k in args.get("keys", [])]
        if "alt" in keys and "f4" in keys:
            return "Alt+F4 closes apps"

    return None


def needs_active_window(action: Dict[str, Any]) -> bool:
    act = action.get("action", "")
    return act in ["click", "type", "hotkey", "sleep", "scroll", "locate_text", "locate_image"]
