import json
import re
from typing import List, Dict, Any


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _parse_json(text: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        if isinstance(data.get("actions"), list):
            return data["actions"]
        return [data]
    if isinstance(data, list):
        return data
    return []


def _parse_line(line: str) -> Dict[str, Any]:
    line = line.strip()
    if not line:
        return {}

    line = re.sub(r"^[-*]\s+", "", line)

    m = re.match(r"^(open|open_app)\s+(.+)$", line, re.I)
    if m:
        return {"action": "open_app", "args": {"app": m.group(2).strip()}}

    m = re.match(r"^click\s+(\d+)\s*[ ,]\s*(\d+)$", line, re.I)
    if m:
        return {"action": "click", "args": {"x": int(m.group(1)), "y": int(m.group(2))}}

    m = re.match(r"^type\s*[:=]?\s+(.+)$", line, re.I)
    if m:
        return {"action": "type", "args": {"text": m.group(1)}}

    m = re.match(r"^(hotkey|press|keys)\s+(.+)$", line, re.I)
    if m:
        keys = [k.strip().upper() for k in re.split(r"\+|\s+", m.group(2)) if k.strip()]
        return {"action": "hotkey", "args": {"keys": keys}}

    m = re.match(r"^(sleep|wait)\s+([0-9]*\.?[0-9]+)$", line, re.I)
    if m:
        return {"action": "sleep", "args": {"seconds": float(m.group(2))}}

    m = re.match(r"^scroll\s+(-?\d+)$", line, re.I)
    if m:
        return {"action": "scroll", "args": {"amount": int(m.group(1))}}

    m = re.match(r"^(locate_text|find_text)\s+(.+)$", line, re.I)
    if m:
        return {"action": "locate_text", "args": {"text": m.group(2).strip().strip("\"")}}

    m = re.match(r"^(locate_image|find_image)\s+(.+)$", line, re.I)
    if m:
        return {"action": "locate_image", "args": {"path": m.group(2).strip().strip("\"")}}

    if re.match(r"^[A-Za-z]+\+[A-Za-z0-9]+$", line):
        keys = [k.strip().upper() for k in line.split("+")]
        return {"action": "hotkey", "args": {"keys": keys}}

    return {}


def parse_actions(text: str) -> List[Dict[str, Any]]:
    text = _strip_code_fences(text)
    actions = _parse_json(text)
    if actions:
        return actions

    result = []
    for line in text.splitlines():
        action = _parse_line(line)
        if action:
            result.append(action)
    return result
