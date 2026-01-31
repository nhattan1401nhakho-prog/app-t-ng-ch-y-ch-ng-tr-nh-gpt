import time
import threading
import tkinter as tk
import traceback
from tkinter import messagebox

from pynput import keyboard
import pyperclip
import pyautogui

from agent import parse_actions
from guardrails import (
    danger_reason,
    needs_active_window,
    is_allowed_window,
    is_allowed_app,
    active_window_title,
)
from executor import execute_action
from vision import locate_text, locate_image
from config import HOTKEY_RUN_CLIPBOARD, HOTKEY_EXIT, ALLOWLIST_APPS, ENFORCE_ALLOWLIST


running = True


def _log_exception(err: Exception) -> None:
    try:
        with open("app.log", "a", encoding="utf-8") as f:
            f.write("\n---\n")
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            f.write("\n")
            f.write("".join(traceback.format_exception(type(err), err, err.__traceback__)))
    except Exception:
        pass


class UiApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("GPT Control")
        self.root.geometry("640x480")

        self.allowlist = list(ALLOWLIST_APPS)

        self.input = tk.Text(self.root, height=10, wrap="word")
        self.input.pack(fill="x", padx=10, pady=8)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10)

        tk.Button(btn_frame, text="Run Raw Text", command=self.run_raw_text).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Run Actions (JSON)", command=self.run_from_text).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Run Clipboard", command=self.run_from_clipboard).pack(side="left", padx=4)

        self.preview_only = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame, text="Preview only", variable=self.preview_only).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Clear", command=self.clear_input).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Exit", command=self.exit_app).pack(side="right", padx=4)

        self.log = tk.Text(self.root, height=12, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=8)

    def log_line(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_input(self) -> None:
        self.input.delete("1.0", "end")

    def exit_app(self) -> None:
        global running
        running = False
        self.root.destroy()

    def run_from_text(self) -> None:
        text = self.input.get("1.0", "end").strip()
        self._run_actions(text)

    def run_raw_text(self) -> None:
        text = self.input.get("1.0", "end")
        self._run_raw(text)

    def run_from_clipboard(self) -> None:
        text = pyperclip.paste() or ""
        self._run_actions(text)

    def _suggest_allow_keyword(self, title: str) -> str:
        t = title.strip()
        if " - " in t:
            t = t.split(" - ")[-1].strip()
        elif "-" in t:
            t = t.split("-")[-1].strip()
        return t[:64] if t else ""

    def _ensure_allowlist_for_active_window(self) -> bool:
        if not ENFORCE_ALLOWLIST:
            return True
        if is_allowed_window(self.allowlist):
            return True
        title = active_window_title()
        if not title:
            messagebox.showwarning("Allowlist", "Cannot detect active window title.")
            return False
        suggestion = self._suggest_allow_keyword(title)
        msg = f"Active window not in allowlist:\n{title}\n\nAllow for this session?\nKeyword: {suggestion}"
        if not messagebox.askyesno("Allowlist", msg):
            return False
        if suggestion:
            self.allowlist.append(suggestion)
            self.log_line(f"[allowlist] added: {suggestion}")
            return True
        return False

    def _ensure_allowlist_for_app(self, app: str) -> bool:
        if not ENFORCE_ALLOWLIST:
            return True
        if is_allowed_app(app, allowlist=self.allowlist):
            return True
        msg = f"App not in allowlist: {app}\n\nAllow for this session?"
        if not messagebox.askyesno("Allowlist", msg):
            return False
        self.allowlist.append(app)
        self.log_line(f"[allowlist] added: {app}")
        return True

    def _confirm_danger(self, reason: str) -> bool:
        msg = f"Dangerous action detected:\n{reason}\n\nProceed?"
        return messagebox.askyesno("Confirm Dangerous Action", msg)

    def _confirm_continue_after_fail(self, reason: str) -> bool:
        msg = f"Action failed:\n{reason}\n\nContinue next steps?"
        return messagebox.askyesno("Action Failed", msg)

    def _run_actions(self, text: str) -> None:
        if not text.strip():
            self.log_line("[info] empty input")
            return
        actions = parse_actions(text)
        if not actions:
            self.log_line("[warn] no actions parsed; use Run Raw Text to paste as-is")
            return
        if not self._confirm_preview(actions=actions):
            self.log_line("[info] preview only or user cancelled")
            return
        for action in actions:
            if not self._step_confirm(action):
                self.log_line("[info] step-by-step cancelled")
                break
            reason = danger_reason(action)
            if reason and not self._confirm_danger(reason):
                self.log_line("[blocked] user rejected dangerous action")
                continue
            if action.get("action") == "open_app":
                app = str(action.get("args", {}).get("app", ""))
                if not self._ensure_allowlist_for_app(app):
                    self.log_line("[blocked] app not in allowlist")
                    continue
            elif needs_active_window(action):
                if not self._ensure_allowlist_for_active_window():
                    self.log_line("[blocked] active window not in allowlist")
                    continue
            ok, msg = execute_action(action, self.allowlist)
            if not ok:
                self.log_line(f"[warn] action failed: {msg}")
                if not self._confirm_continue_after_fail(msg):
                    break
            time.sleep(0.05)

    def _run_raw(self, text: str) -> None:
        if not text.strip():
            self.log_line("[info] empty input")
            return
        if not self._confirm_preview(raw_text=text):
            self.log_line("[info] preview only or user cancelled")
            return
        action = {"action": "type", "args": {"text": text}}
        if not self._step_confirm(action):
            self.log_line("[info] step-by-step cancelled")
            return
        reason = danger_reason(action)
        if reason and not self._confirm_danger(reason):
            self.log_line("[blocked] user rejected dangerous action")
            return
        if needs_active_window(action):
            if not self._ensure_allowlist_for_active_window():
                self.log_line("[blocked] active window not in allowlist")
                return
        ok, msg = execute_action(action, self.allowlist)
        if not ok:
            self.log_line(f"[warn] action failed: {msg}")

    def _confirm_preview(self, actions=None, raw_text: str | None = None) -> bool:
        preview_lines = []
        if actions:
            for i, a in enumerate(actions, start=1):
                act = a.get("action", "")
                args = a.get("args", {})
                preview_lines.append(f"{i}. {act} {args}")
        if raw_text is not None:
            raw = raw_text.rstrip("\n")
            lines = raw.splitlines()
            preview_lines.append(f"1. type raw text ({len(lines)} lines, {len(raw)} chars)")
            preview_lines.append("---")
            preview_lines.extend(lines[:20])
            if len(lines) > 20:
                preview_lines.append("... (truncated)")

        if not self.preview_only.get():
            return True
        return self._show_preview_dialog(preview_lines, preview_only=True)

    def _show_preview_dialog(self, lines: list[str], preview_only: bool) -> bool:
        dlg = tk.Toplevel(self.root)
        dlg.title("Preview Steps")
        dlg.geometry("720x520")
        dlg.transient(self.root)
        dlg.grab_set()

        info = tk.Label(dlg, text="Preview of steps to execute:")
        info.pack(anchor="w", padx=10, pady=6)

        box = tk.Text(dlg, wrap="word")
        box.pack(fill="both", expand=True, padx=10, pady=6)
        box.insert("1.0", "\n".join(lines))
        box.configure(state="disabled")

        result = {"run": False}

        def _run_now():
            result["run"] = True
            dlg.destroy()

        def _cancel():
            result["run"] = False
            dlg.destroy()

        btns = tk.Frame(dlg)
        btns.pack(fill="x", padx=10, pady=8)

        if preview_only:
            tk.Button(btns, text="Close", command=_cancel).pack(side="right")
        else:
            tk.Button(btns, text="Cancel", command=_cancel).pack(side="right", padx=6)
            tk.Button(btns, text="Run", command=_run_now).pack(side="right")

        self.root.wait_window(dlg)
        return result["run"]

    def _step_confirm(self, action: dict) -> bool:
        act = action.get("action", "")
        args = action.get("args", {})
        pos = None
        if act == "click":
            try:
                pos = (int(args.get("x", 0)), int(args.get("y", 0)))
            except Exception:
                pos = None
        elif act == "locate_text":
            query = str(args.get("text", ""))
            pos = locate_text(query)
            if not pos:
                messagebox.showwarning("Step Preview", f"Text not found: {query}")
                return False
        elif act == "locate_image":
            path = str(args.get("path", ""))
            pos = locate_image(path)
            if not pos:
                messagebox.showwarning("Step Preview", f"Image not found: {path}")
                return False

        overlay = None
        if pos:
            overlay = self._show_overlay(*pos)

        msg = f"Next step:\n- {act} {args}\n\nRun this step?"
        ok = messagebox.askyesno("Step Preview", msg)
        if overlay:
            overlay.destroy()
        return ok

    def _show_overlay(self, x: int, y: int) -> tk.Toplevel:
        w, h = pyautogui.size()
        ov = tk.Toplevel(self.root)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        ov.attributes("-alpha", 0.25)
        ov.geometry(f"{w}x{h}+0+0")

        canvas = tk.Canvas(ov, width=w, height=h, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        r = 18
        canvas.create_oval(x - r, y - r, x + r, y + r, outline="red", width=4)
        canvas.create_line(x - 40, y, x + 40, y, fill="red", width=2)
        canvas.create_line(x, y - 40, x, y + 40, fill="red", width=2)
        return ov


def on_activate_run(ui: UiApp):
    ui.log_line("[hotkey] run from clipboard")
    ui.run_from_clipboard()


def on_activate_exit(ui: UiApp):
    ui.log_line("[hotkey] exit")
    ui.exit_app()
    return False


def _hotkey_thread(ui: UiApp) -> None:
    try:
        with keyboard.GlobalHotKeys({
            HOTKEY_RUN_CLIPBOARD: lambda: on_activate_run(ui),
            HOTKEY_EXIT: lambda: on_activate_exit(ui),
        }) as _h:
            while running:
                time.sleep(0.2)
    except Exception as e:
        _log_exception(e)
        ui.log_line(f"[warn] hotkey thread error: {e}")


def main():
    ui = UiApp()
    ui.log_line("GPT control ready")
    ui.log_line(f"Hotkey run: {HOTKEY_RUN_CLIPBOARD} | exit: {HOTKEY_EXIT}")

    t = threading.Thread(target=_hotkey_thread, args=(ui,), daemon=True)
    t.start()
    ui.root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log_exception(e)
        try:
            messagebox.showerror("GPT Control Error", f"{e}\n\nChi ti?t trong app.log")
        except Exception:
            pass
        time.sleep(2)
