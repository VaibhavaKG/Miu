"""
45-Minute Focus Session & Pomodoro Engine for Oneko Desktop Companion.

Core philosophy:
- Default focus duration is EXACTLY 45 MINUTES (45:00).
- Standard cycle: 45m Focus -> 5m Short Break -> 45m Focus -> 5m Short Break -> 45m Focus -> 15m Long Break.
- Supports Start, Pause, Resume, Reset, Skip, Manual Break triggers.
- Tracks daily statistics (sessions, focus time).
"""

import time
from datetime import date


class PomodoroPhase:
    IDLE = "IDLE"
    FOCUS = "FOCUS"
    PAUSED = "PAUSED"
    BREAK = "BREAK"
    LONG_BREAK = "LONG_BREAK"


class PomodoroEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.focus_duration_min = self.config.get("focus_duration_min", 45)
        self.short_break_min = self.config.get("short_break_min", 5)
        self.long_break_min = self.config.get("long_break_min", 15)

        self.phase = PomodoroPhase.IDLE
        self.paused_from = PomodoroPhase.FOCUS
        self.time_left = self.focus_duration_min * 60
        self.total_phase_duration = self.time_left
        self.completed_cycles = 0

        # Daily stats
        self.stats = self.config.get("stats", {
            "date": date.today().isoformat(),
            "focus_sessions": 0,
            "focus_seconds": 0,
            "quotes_read": 0
        })
        self._ensure_today_stats()

    def update_durations(self, focus_min=45, short_min=5, long_min=15):
        self.focus_duration_min = max(1, int(focus_min))
        self.short_break_min = max(1, int(short_min))
        self.long_break_min = max(1, int(long_min))
        if self.phase == PomodoroPhase.IDLE:
            self.time_left = self.focus_duration_min * 60
            self.total_phase_duration = self.time_left

    def _ensure_today_stats(self):
        today = date.today().isoformat()
        if self.stats.get("date") != today:
            self.stats = {
                "date": today,
                "focus_sessions": 0,
                "focus_seconds": 0,
                "quotes_read": self.stats.get("quotes_read", 0)
            }

    def start_focus(self):
        self.phase = PomodoroPhase.FOCUS
        self.time_left = self.focus_duration_min * 60
        self.total_phase_duration = self.time_left

    def pause(self):
        if self.phase in (PomodoroPhase.FOCUS, PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK):
            self.paused_from = self.phase
            self.phase = PomodoroPhase.PAUSED

    def resume(self):
        if self.phase == PomodoroPhase.PAUSED:
            self.phase = self.paused_from

    def toggle_pause(self):
        if self.phase == PomodoroPhase.PAUSED:
            self.resume()
        elif self.phase in (PomodoroPhase.FOCUS, PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK):
            self.pause()
        else:
            self.start_focus()

    def reset(self):
        self.phase = PomodoroPhase.IDLE
        self.paused_from = PomodoroPhase.FOCUS
        self.time_left = self.focus_duration_min * 60
        self.total_phase_duration = self.time_left
        self.completed_cycles = 0

    def skip(self):
        """Skips current phase to the next in the cycle."""
        if self.phase == PomodoroPhase.FOCUS:
            self._transition_to_break()
        else:
            self.start_focus()

    def start_short_break(self):
        self.phase = PomodoroPhase.BREAK
        self.time_left = self.short_break_min * 60
        self.total_phase_duration = self.time_left

    def start_long_break(self):
        self.phase = PomodoroPhase.LONG_BREAK
        self.time_left = self.long_break_min * 60
        self.total_phase_duration = self.time_left

    def tick(self):
        """
        Called once per second. Returns event tuple:
        (state_changed: bool, event_type: str or None)
        event_types: 'focus_finished', 'break_finished'
        """
        self._ensure_today_stats()

        if self.phase in (PomodoroPhase.FOCUS, PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK):
            self.time_left -= 1
            if self.phase == PomodoroPhase.FOCUS:
                self.stats["focus_seconds"] += 1

            if self.time_left <= 0:
                if self.phase == PomodoroPhase.FOCUS:
                    self.completed_cycles += 1
                    self.stats["focus_sessions"] += 1
                    self._transition_to_break()
                    return True, "focus_finished"
                else:
                    self.start_focus()
                    return True, "break_finished"

        return False, None

    def _transition_to_break(self):
        if self.completed_cycles > 0 and self.completed_cycles % 3 == 0:
            self.start_long_break()
        else:
            self.start_short_break()

    def get_time_string(self):
        m, s = divmod(max(0, self.time_left), 60)
        return f"{m:02d}:{s:02d}"

    def get_progress_ratio(self):
        if self.total_phase_duration <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (self.time_left / self.total_phase_duration)))

    def get_stats_summary(self):
        self._ensure_today_stats()
        sessions = self.stats["focus_sessions"]
        total_sec = self.stats["focus_seconds"]
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60
        time_str = f"{hours}h {mins:02d}m" if hours > 0 else f"{mins}m"
        drops = self.stats.get("quotes_read", 0)
        return {
            "sessions": sessions,
            "focus_time": time_str,
            "drops_read": drops,
        }
