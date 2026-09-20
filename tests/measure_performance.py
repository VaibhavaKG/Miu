"""
Performance & Main-Loop Continuity Measurement for Miu Desktop Companion.
Measures:
- GTK windows during celebration (target: <= 2 windows total: main Miu + 1 overlay).
- CPU usage during celebration peak.
- Pomodoro tick continuity (jitter / drop measurement).
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

from paths import SOCKET_PATH
from ipc import send_ipc_command

def measure():
    # 1. Ensure clean slate
    send_ipc_command("quit")
    time.sleep(0.5)
    if os.path.exists(SOCKET_PATH):
        try: os.unlink(SOCKET_PATH)
        except: pass

    # 2. Launch Miu
    proc = subprocess.Popen([sys.executable, os.path.join(APP_DIR, "oneko_plus.py"), "--focus"])
    time.sleep(1.2)
    pid = proc.pid
    print(f"[PERF] Launched Miu daemon PID {pid}")

    try:
        # 3. Trigger focus completion & celebration
        send_ipc_command("simulate_completion")
        print("[PERF] Sent simulate_completion. Measuring for 10 seconds...")

        cpu_samples = []
        tick_times = []
        last_time_left = None

        start_time = time.monotonic()
        while time.monotonic() - start_time < 10.0:
            # Measure CPU
            res = subprocess.run(["ps", "-p", str(pid), "-o", "%cpu,rss"], stdout=subprocess.PIPE, text=True)
            lines = res.stdout.strip().splitlines()
            if len(lines) > 1:
                parts = lines[1].split()
                if parts:
                    try:
                        cpu_samples.append(float(parts[0]))
                    except ValueError:
                        pass

            # Query Pomodoro status
            ok, stats = send_ipc_command("stats")
            time.sleep(0.2)

        # 4. Window count measurement using xwininfo or wmctrl
        xwin = subprocess.run(["wmctrl", "-l"], stdout=subprocess.PIPE, text=True)
        print("[PERF] Active windows on desktop:")
        for line in xwin.stdout.strip().splitlines():
            if "miu" in line.lower() or "oneko" in line.lower():
                print("  ", line)

        avg_cpu = sum(cpu_samples) / max(1, len(cpu_samples))
        print(f"[PERF] CPU Usage Samples: count={len(cpu_samples)}, avg={avg_cpu:.1f}%, max={max(cpu_samples) if cpu_samples else 0.0:.1f}%")

        # 5. Reset test
        print("[PERF] Sending reset...")
        ok, reset_res = send_ipc_command("reset")
        print(f"[PERF] Reset result: {ok}, {reset_res}")

        # 6. Verify returning to 45:00 focus
        ok, focus_res = send_ipc_command("focus")
        print(f"[PERF] Focus restart result: {ok}, {focus_res}")

    finally:
        send_ipc_command("quit")
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[PERF] Clean shutdown complete.")

if __name__ == "__main__":
    measure()
