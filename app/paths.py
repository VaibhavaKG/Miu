"""
Miu Application Paths and Directory Management.

Distinguishes between:
1. Static Package Paths (read-only application assets and code)
2. User State Paths (writable configuration, accessories, and logs in standard XDG dirs)
"""

import os
import shutil
from pathlib import Path

# Package root (resolved relative to this file)
_APP_PATH = Path(__file__).resolve().parent
_PACKAGE_PATH = _APP_PATH.parent

_STATIC_ASSETS_PATH = _PACKAGE_PATH / "assets"
_LITERATURE_PATH = _PACKAGE_PATH / "literature"
_ICONS_PATH = _PACKAGE_PATH / "icons"

APP_DIR = str(_APP_PATH)
PACKAGE_DIR = str(_PACKAGE_PATH)

STATIC_ASSETS_DIR = str(_STATIC_ASSETS_PATH)
LITERATURE_DIR = str(_LITERATURE_PATH)
ICONS_DIR = str(_ICONS_PATH)

SPRITE_FILE = str(_STATIC_ASSETS_PATH / "oneko.gif")
CHIME_FILE = str(_STATIC_ASSETS_PATH / "chime.wav")
PURR_FILE = str(_STATIC_ASSETS_PATH / "purr.wav")
WATER_FILE = str(_STATIC_ASSETS_PATH / "water.wav")

ICON_PNG = str(_ICONS_PATH / "miu.png")
ICON_SVG = str(_ICONS_PATH / "miu.svg")

VERSION_FILE = _PACKAGE_PATH / "VERSION"

# User-specific directories (XDG compliant)
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")))
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")))
XDG_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")))
XDG_RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))

USER_CONFIG_DIR = XDG_CONFIG_HOME / "miu"
USER_CONFIG_FILE = str(USER_CONFIG_DIR / "config.json")

USER_DATA_DIR = XDG_DATA_HOME / "miu"
USER_ACCESSORIES_DIR = str(USER_DATA_DIR / "accessories")
USER_LOG_FILE = str(USER_DATA_DIR / "miu.log")

USER_CACHE_DIR = XDG_CACHE_HOME / "miu"

SOCKET_PATH = str(XDG_RUNTIME_DIR / "miu.sock")

# Legacy directory for seamless migration
LEGACY_DIR = Path(os.path.expanduser("~/.local/share/oneko-plus"))
LEGACY_CONFIG = LEGACY_DIR / "config.json"
LEGACY_ACCESSORIES = LEGACY_DIR / "accessories"


def ensure_user_dirs():
    """Ensure user config, data, and cache directories exist, performing migration if necessary."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    USER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs(USER_ACCESSORIES_DIR, exist_ok=True)

    # Migrate config.json if not present in ~/.config/miu
    if not os.path.exists(USER_CONFIG_FILE) and LEGACY_CONFIG.exists():
        try:
            shutil.copy2(LEGACY_CONFIG, USER_CONFIG_FILE)
        except Exception:
            pass

    # Migrate custom accessories if present in legacy dir
    if LEGACY_ACCESSORIES.exists() and LEGACY_ACCESSORIES.is_dir():
        try:
            for item in LEGACY_ACCESSORIES.iterdir():
                dest = Path(USER_ACCESSORIES_DIR) / item.name
                if not dest.exists():
                    if item.is_file():
                        shutil.copy2(item, dest)
        except Exception:
            pass


def get_version():
    """Read version string."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "2.0.0"
