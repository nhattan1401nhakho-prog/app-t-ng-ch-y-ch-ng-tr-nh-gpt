import subprocess
import time
from typing import Dict, Any, Tuple, Callable, Optional, List

import pyautogui

from config import DEFAULT_PAUSE, FAILSAFE, LOCATE_TIMEOUT, LOCATE_INTERVAL
from guardrails import is_allowed_window, is_allowed_app, active_window_title
from vision import locate_text, locate_image

pyautogui.FAILSAFE = FAILSAFE
pyautogui.PAUSE = DEFAULT_PAUSE


def _start_app(app: str) -> None:
    subprocess.Popen(["cmd", "/c", "start", "", app], shell=False)


def _retry_until(
    fn: Callable[[], Optional[Tuple[int, int]]],
    timeout_s: float,
    interval_s: float,
    retries: int,
) -> Tuple[Optional[Tuple[int, int]], str]:
    if timeout_s > 0:
        end = time.time() + timeout_s
        while time.time() < end:
            pos = fn()
            if pos:
                return pos, ""
            time.sleep(interval_s)
        return None, f"not found within {timeout_s:.1f}s"

    attempts = max(0, retries)
    for i in range(attempts + 1):
        pos = fn()
        if pos:
            return pos, ""
        if i < attempts:
            time.sleep(interval_s)
    return None, f"not found after {attempts + 1} attempts"


def execute_action(action: Dict[str, Any], allowlist: List[str]) -> Tuple[bool, str]:
    act = action.get("action", "")
    args = action.get("args", {})

    if act == "open_app":
        app = str(args.get("app", "")).strip()
        if not app:
            return False, "missing app"
        if not is_allowed_app(app, allowlist=allowlist):
            return False, f"app not in allowlist: {app}"
        _start_app(app)
        return True, ""

    if act in ["click", "type", "hotkey", "sleep", "scroll", "locate_text", "locate_image"]:
        if not is_allowed_window(allowlist=allowlist):
            title = active_window_title()
            return False, f"active window not in allowlist: {title or 'unknown'}"

    if act == "click":
        x = int(args.get("x", 0))
        y = int(args.get("y", 0))
        pyautogui.click(x, y)
        return True, ""

    if act == "type":
        text = str(args.get("text", ""))
        pyautogui.write(text, interval=0.01)
        return True, ""

    if act == "hotkey":
        keys = [str(k).lower() for k in args.get("keys", [])]
        if keys:
            pyautogui.hotkey(*keys)
        return True, ""

    if act == "sleep":
        seconds = float(args.get("seconds", 0))
        time.sleep(seconds)
        return True, ""

    if act == "scroll":
        amount = int(args.get("amount", 0))
        pyautogui.scroll(amount)
        return True, ""

    if act == "locate_text":
        query = str(args.get("text", ""))
        timeout_s = float(args.get("timeout", LOCATE_TIMEOUT))
        interval_s = float(args.get("interval", LOCATE_INTERVAL))
        retries = int(args.get("retries", 0))
        pos, reason = _retry_until(lambda: locate_text(query), timeout_s, interval_s, retries)
        if not pos:
            return False, f"text not found: {query} ({reason})"
        if args.get("click", True):
            pyautogui.click(*pos)
        else:
            pyautogui.moveTo(*pos)
        return True, ""

    if act == "locate_image":
        path = str(args.get("path", ""))
        timeout_s = float(args.get("timeout", LOCATE_TIMEOUT))
        interval_s = float(args.get("interval", LOCATE_INTERVAL))
        retries = int(args.get("retries", 0))
        pos, reason = _retry_until(lambda: locate_image(path), timeout_s, interval_s, retries)
        if not pos:
            return False, f"image not found: {path} ({reason})"
        if args.get("click", True):
            pyautogui.click(*pos)
        else:
            pyautogui.moveTo(*pos)
        return True, ""

    return False, f"unknown action: {act}"
