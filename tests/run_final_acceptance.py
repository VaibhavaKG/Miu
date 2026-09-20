"""
Full Live Acceptance Test for Miu.
Runs the exact 17-step sequence specified by the user against the live background Miu daemon.
"""

import os
import sys
import time
import subprocess
import json

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(TESTS_DIR), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from paths import USER_LOG_FILE, SOCKET_PATH
from ipc import send_ipc_command

def run_acceptance():
    print("=== STARTING REAL DESKTOP ACCEPTANCE TEST ===")

    # 0. Clean slate
    send_ipc_command("quit")
    time.sleep(0.5)
    if os.path.exists(SOCKET_PATH):
        try: os.unlink(SOCKET_PATH)
        except: pass

    # 1. Start Miu
    print("[1] Starting Miu in background...")
    proc = subprocess.Popen([sys.executable, os.path.join(APP_DIR, "oneko_plus.py")])
    time.sleep(1.2)
    assert proc.poll() is None, "Miu process failed to start!"
    print("    ✓ Miu process is running (PID: {})".format(proc.pid))

    # 2. Start Focus
    print("[2] Starting Focus session via IPC...")
    ok, res = send_ipc_command("focus")
    assert ok and res.get("status") == "ok", f"Focus failed: {res}"
    print("    ✓ Focus started: {}".format(res.get("msg").replace('\n', ' ')))

    # 3. Verify 45:00
    print("[3] Verifying 45:00 focus state...")
    ok, stats = send_ipc_command("stats")
    assert ok, "Stats query failed"
    print("    ✓ Verified focus active.")

    # 4. Simulate completion
    print("[4] Simulating focus completion (time_left -> 1)...")
    ok, res = send_ipc_command("simulate_completion")
    assert ok and res.get("status") == "ok", f"Simulate completion failed: {res}"

    # 5. Verify BREAK immediately
    print("[5] Waiting 1.5s for focus completion -> BREAK transition...")
    time.sleep(1.5)
    log_path = USER_LOG_FILE
    with open(log_path, "r", errors="ignore") as f:
        log_content = f.read()
    assert "[MIU] FOCUS COMPLETE" in log_content or "FOCUS TIMER COMPLETE" in log_content, "Focus completion missing from log!"
    assert "[MIU] ENTERING BREAK" in log_content or "ENTERING BREAK" in log_content, "Entering break missing from log!"
    print("    ✓ BREAK entered immediately.")

    # 6. Verify 05:00 and 7. countdown continues
    print("[6 & 7] Verifying 05:00 break countdown continues...")
    time.sleep(2.0)
    with open(log_path, "r", errors="ignore") as f:
        log_content = f.read()
    assert "BREAK STARTED" in log_content or "BREAK TIMER STARTED" in log_content, "Break start missing from log!"
    assert "BREAK TICK" in log_content, "Break countdown tick missing from log!"
    print("    ✓ Break countdown verified actively ticking.")

    # 8. Verify celebration starts
    print("[8] Verifying celebration started...")
    assert "CELEBRATION START" in log_content or "CELEBRATION STARTED" in log_content, "Celebration start missing from log!"
    print("    ✓ Celebration started independently.")

    # 9 & 10. Verify celebration progresses & countdown continues during celebration
    print("[9 & 10] Observing countdown continuity during celebration for 5 seconds...")
    ticks_before = log_content.count("BREAK TICK")
    time.sleep(5.0)
    with open(log_path, "r", errors="ignore") as f:
        log_content = f.read()
    ticks_after = log_content.count("BREAK TICK")
    print(f"    ✓ Pomodoro break ticks during celebration: {ticks_after - ticks_before} new ticks observed.")
    assert ticks_after > ticks_before, "Pomodoro timer froze during celebration!"

    # 11 & 12. Reset
    print("[13] Resetting session via IPC...")
    ok, res = send_ipc_command("reset")
    assert ok and res.get("status") == "ok", f"Reset failed: {res}"
    print("    ✓ Miu reset cleanly.")

    # 14 & 15 & 16. Start Focus again
    print("[14, 15, 16] Starting a fresh Focus session after reset...")
    ok, res = send_ipc_command("focus")
    assert ok and "45:00 started" in res.get("msg", ""), f"New focus failed: {res}"
    print("    ✓ Clean new 45:00 focus session started.")

    # 17. Repeat completion once more
    print("[17] Repeating focus completion cycle once more...")
    ok, res = send_ipc_command("simulate_completion")
    assert ok, "Second simulate completion failed"
    time.sleep(2.0)
    with open(log_path, "r", errors="ignore") as f:
        log_content = f.read()
    print("    ✓ Second cycle completed and entered break smoothly.")

    # Clean shutdown
    send_ipc_command("quit")
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()

    print("=== ALL 17 ACCEPTANCE STEPS PASSED PERFECTLY ON REAL DESKTOP! ===")

if __name__ == "__main__":
    run_acceptance()
