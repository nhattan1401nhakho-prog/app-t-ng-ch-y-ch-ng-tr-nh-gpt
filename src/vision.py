from typing import Optional, Tuple
from difflib import SequenceMatcher

import pyautogui
import pytesseract
import cv2
import numpy as np

from config import TESSERACT_CMD


def _set_tesseract_cmd() -> None:
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def _best_match(query: str, words: list[str]) -> Tuple[int, float]:
    q = query.lower().strip()
    best_i = -1
    best_score = 0.0
    for i, w in enumerate(words):
        w = str(w).lower().strip()
        if not w:
            continue
        if q == w:
            return i, 1.0
        if q in w or w in q:
            score = 0.92
        else:
            score = SequenceMatcher(None, q, w).ratio()
        if score > best_score:
            best_score = score
            best_i = i
    return best_i, best_score


def _preprocess(img_bgr: np.ndarray) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    if max(h, w) < 1400:
        img_bgr = cv2.resize(img_bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def locate_text(query: str) -> Optional[Tuple[int, int]]:
    _set_tesseract_cmd()
    screenshot = pyautogui.screenshot()
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    proc = _preprocess(img)
    data = pytesseract.image_to_data(
        proc,
        output_type=pytesseract.Output.DICT,
        config="--oem 3 --psm 6",
    )
    words = data.get("text", [])
    idx, score = _best_match(query, words)
    if idx == -1 or score < 0.75:
        return None
    x = int(data["left"][idx])
    y = int(data["top"][idx])
    w = int(data["width"][idx])
    h = int(data["height"][idx])
    return x + w // 2, y + h // 2


def locate_image(path: str) -> Optional[Tuple[int, int]]:
    try:
        return pyautogui.locateCenterOnScreen(path, confidence=0.85)
    except Exception:
        try:
            return pyautogui.locateCenterOnScreen(path)
        except Exception:
            return None
