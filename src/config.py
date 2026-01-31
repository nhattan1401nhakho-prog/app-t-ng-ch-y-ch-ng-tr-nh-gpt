# Config for GPT mouse/keyboard automation

ALLOWLIST_APPS = [
    "chrome",
    "notepad",
    "powershell",
    "windows powershell",
    "terminal",
    "code",
    "visual studio code",
]

DANGEROUS_KEYWORDS = [
    "cmd",
    "command prompt",
    "registry",
    "regedit",
    "control panel",
    "uninstall",
    "format",
    "delete",
    "remove",
    "shutdown",
    "restart",
]

# Hotkeys
HOTKEY_RUN_CLIPBOARD = "<f8>"
HOTKEY_EXIT = "<f10>"

# OCR
TESSERACT_CMD = ""

# Safety
FAILSAFE = True
DEFAULT_PAUSE = 0.15

# If True, block actions when active window title is not in allowlist
ENFORCE_ALLOWLIST = True

# Retry defaults for vision actions
LOCATE_TIMEOUT = 6.0
LOCATE_INTERVAL = 0.5
