"""
Unit and Integration Tests for Miu CLI & IPC System.
Verifies all commands:
  hi miu
  hi miu --focus
  hi miu --pause
  hi miu --resume
  hi miu --reset
  hi miu --break
  hi miu --literary
  hi miu --customize
  hi miu --stats
  hi miu --version
  hi miu --help, -h
"""

import os
import sys
import time
import unittest
import subprocess

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from ipc import send_ipc_command, SOCKET_PATH
from miu_cli import print_help, read_offline_stats, VERSION


class TestMiuCLIHelpAndStatic(unittest.TestCase):
    def test_version_output(self):
        self.assertEqual(VERSION, "2.1.0")

    def test_help_content_comprehensive(self):
        import io
        captured = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = captured
            print_help()
        finally:
            sys.stdout = old_stdout

        text = captured.getvalue()
        # Verify required sections
        self.assertIn("MIU", text)
        self.assertIn("USAGE", text)
        self.assertIn("hi miu [COMMAND]", text)
        self.assertIn("hi miu --focus", text)
        self.assertIn("hi miu --pause", text)
        self.assertIn("hi miu --resume", text)
        self.assertIn("hi miu --reset", text)
        self.assertIn("hi miu --break", text)
        self.assertIn("hi miu --literary", text)
        self.assertIn("hi miu --customize", text)
        self.assertIn("hi miu --stats", text)
        self.assertIn("hi miu --help", text)

        # Focus section
        self.assertIn("FOCUS SYSTEM", text)
        self.assertIn("45 minutes", text)
        self.assertIn("5 minutes", text)
        self.assertIn("15 minutes", text)

        # Literature section
        self.assertIn("LITERARY SYSTEM", text)
        self.assertIn("ONE LINE", text)
        self.assertIn("106", text)

        # Personalities
        self.assertIn("CALM", text)
        self.assertIn("PLAYFUL", text)
        self.assertIn("SLEEPY", text)
        self.assertIn("ENERGETIC", text)
        self.assertIn("FOCUSED", text)

        # States
        for st in ["IDLE", "WALKING", "RUNNING", "SITTING", "SLEEPING", "STRETCHING", "CURIOUS", "HAPPY", "FOCUSED", "BREAK"]:
            self.assertIn(st, text)

        # Customization
        self.assertIn("CURRENT COAT / SKIN THEMES:", text)
        self.assertIn("Classic Neko", text)
        self.assertIn("Ginger Tabby", text)
        self.assertIn("Midnight Black", text)
        self.assertIn("CURRENT ACCESSORIES:", text)
        self.assertIn("Gentleman Top Hat", text)
        self.assertIn("CURRENT EYE EXPRESSIONS:", text)
        self.assertIn("Standard", text)

        # Attribution
        self.assertIn("Initially based on Oneko. Later customized and evolved by Vaibhava.", text)

    def test_offline_stats_format(self):
        stats = read_offline_stats()
        self.assertIn("sessions", stats)
        self.assertIn("focus_time", stats)
        self.assertIn("drops_read", stats)


class TestMiuLiveIPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean any stale socket
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass

        # Spawn background Miu instance
        oneko_py = os.path.join(APP_DIR, "oneko_plus.py")
        cls.proc = subprocess.Popen(
            [sys.executable, oneko_py],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Wait up to 3 seconds for socket to appear
        for _ in range(30):
            time.sleep(0.1)
            if os.path.exists(SOCKET_PATH):
                break

    @classmethod
    def tearDownClass(cls):
        send_ipc_command("quit")
        try:
            cls.proc.terminate()
            cls.proc.wait(timeout=1.0)
        except Exception:
            pass
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass

    def test_ipc_wake(self):
        success, resp = send_ipc_command("wake")
        self.assertTrue(success)
        self.assertEqual(resp.get("status"), "ok")
        self.assertEqual(resp.get("msg"), "Miu is awake.")

    def test_ipc_focus(self):
        success, resp = send_ipc_command("focus")
        self.assertTrue(success)
        self.assertEqual(resp.get("status"), "ok")
        self.assertIn("Miu is focused.", resp.get("msg", ""))
        self.assertIn("45:00 started.", resp.get("msg", ""))

    def test_ipc_pause_resume_reset(self):
        # Pause
        success, resp = send_ipc_command("pause")
        self.assertTrue(success)
        self.assertEqual(resp.get("msg"), "Miu paused.")

        # Resume
        success, resp = send_ipc_command("resume")
        self.assertTrue(success)
        self.assertEqual(resp.get("msg"), "Miu resumed.")

        # Reset
        success, resp = send_ipc_command("reset")
        self.assertTrue(success)
        self.assertEqual(resp.get("msg"), "Miu reset.")

    def test_ipc_break(self):
        success, resp = send_ipc_command("break")
        self.assertTrue(success)
        self.assertEqual(resp.get("status"), "ok")
        self.assertIn("Miu is on break.", resp.get("msg", ""))

    def test_ipc_literary(self):
        success, resp = send_ipc_command("literary")
        self.assertTrue(success)
        self.assertEqual(resp.get("status"), "ok")
        self.assertEqual(resp.get("msg"), "Miu has left a line for you.")

    def test_ipc_stats(self):
        success, resp = send_ipc_command("stats")
        self.assertTrue(success)
        self.assertEqual(resp.get("status"), "ok")
        self.assertIn("Miu\nToday", resp.get("msg", ""))

    def test_ipc_summon(self):
        success, resp = send_ipc_command("summon")
        self.assertTrue(success)
        self.assertEqual(resp.get("status"), "ok")
        self.assertIn("Miu is on the way!", resp.get("msg", ""))


if __name__ == "__main__":
    unittest.main()
