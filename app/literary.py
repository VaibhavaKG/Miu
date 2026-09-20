"""
One-Line Literary Engine for Oneko Desktop Companion.

Enforces strict product requirements:
- EXACTLY ONE LINE of literary text + Author attribution.
- Modes: 'breaks_only' (default), 'occasional', 'off'.
- Minimal interaction: SAVE, NEXT, CLOSE.
- Content loaded from literature/works.json.
- Tracks saved literary lines in persistent storage.
"""

import os
import json
import random


class LiteraryEngine:
    def __init__(self, app_dir=None, config=None):
        if app_dir is None:
            try:
                from paths import LITERATURE_DIR, PACKAGE_DIR
                self.app_dir = str(PACKAGE_DIR)
                self.works_path = os.path.join(LITERATURE_DIR, "works.json")
                self.legacy_path = os.path.join(LITERATURE_DIR, "quotes.json")
            except ImportError:
                self.app_dir = os.path.expanduser("~/.local/share/oneko-plus")
                self.works_path = os.path.join(self.app_dir, "literature", "works.json")
                self.legacy_path = os.path.join(self.app_dir, "quotes.json")
        else:
            self.app_dir = app_dir
            if os.path.exists(os.path.join(app_dir, "works.json")):
                self.works_path = os.path.join(app_dir, "works.json")
                self.legacy_path = os.path.join(app_dir, "quotes.json")
            else:
                self.works_path = os.path.join(app_dir, "literature", "works.json")
                self.legacy_path = os.path.join(app_dir, "quotes.json")
        self.config = config or {}

        self.mode = self.config.get("literary_mode", "breaks_only")  # breaks_only, occasional, off
        self.occasional_interval_sec = self.config.get("quote_interval_min", 15) * 60
        self.occasional_timer = self.occasional_interval_sec

        self.works = []
        self.unused_works = []
        self.saved_works = list(self.config.get("saved_quotes", []))
        self.current_work = None
        self.is_active = False

        self._load_works()

    def _load_works(self):
        target_path = self.works_path if os.path.exists(self.works_path) else self.legacy_path
        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for item in raw:
                        text = item.get("text") or item.get("quote") or ""
                        author = item.get("author") or "Unknown"
                        source = item.get("source") or item.get("work") or ""
                        # Strict one line enforcement: strip all newlines
                        cleaned_text = " ".join(text.split()).strip()
                        if cleaned_text and author:
                            self.works.append({
                                "text": cleaned_text,
                                "author": author.strip(),
                                "source": source.strip()
                            })
            except Exception:
                pass

        if not self.works:
            self.works = [
                {"text": "One must imagine Sisyphus happy.", "author": "Albert Camus", "source": "The Myth of Sisyphus"},
                {"text": "All happy families are alike; each unhappy family is unhappy in its own way.", "author": "Leo Tolstoy", "source": "Anna Karenina"},
                {"text": "In the midst of winter, I found there was, within me, an invincible summer.", "author": "Albert Camus", "source": "Return to Tipasa"},
                {"text": "I have always imagined that Paradise will be a kind of library.", "author": "Jorge Luis Borges", "source": "Poem of the Gifts"},
                {"text": "Tell me, what is it you plan to do with your one wild and precious life?", "author": "Mary Oliver", "source": "The Summer Day"}
            ]

        self.unused_works = list(self.works)
        random.shuffle(self.unused_works)

    def set_mode(self, mode):
        self.mode = mode if mode in ("breaks_only", "occasional", "off") else "breaks_only"

    def set_occasional_interval(self, minutes):
        self.occasional_interval_sec = max(1, int(minutes)) * 60
        self.occasional_timer = self.occasional_interval_sec

    def trigger_drop(self):
        """Picks the next genuine literary one-liner and activates the drop card."""
        if not self.unused_works:
            self.unused_works = list(self.works)
            random.shuffle(self.unused_works)

        self.current_work = self.unused_works.pop()
        self.is_active = True
        return self.current_work

    def next_drop(self):
        """Action: NEXT -> Show another literary line."""
        return self.trigger_drop()

    def save_current(self):
        """Action: SAVE -> Save current line to local storage."""
        if self.current_work and self.current_work not in self.saved_works:
            self.saved_works.append(self.current_work)
            return True
        return False

    def is_current_saved(self):
        return self.current_work in self.saved_works if self.current_work else False

    def dismiss(self):
        """Action: CLOSE -> Dismiss current literary drop."""
        self.is_active = False
        self.occasional_timer = self.occasional_interval_sec

    def tick_second(self, is_in_focus=False):
        """
        Called once per second. Returns True if an occasional drop should trigger.
        Will NOT interrupt an active focus session.
        """
        if self.mode == "occasional" and not self.is_active and not is_in_focus:
            self.occasional_timer -= 1
            if self.occasional_timer <= 0:
                self.occasional_timer = self.occasional_interval_sec
                self.trigger_drop()
                return True
        return False
