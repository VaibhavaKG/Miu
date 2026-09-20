"""
Command-line Interface for Miu Desktop Companion.

Entry points:
  hi miu [COMMAND]
  miu [COMMAND]
"""

import os
import sys
import json
import time
import subprocess

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

try:
    from paths import (
        ensure_user_dirs,
        USER_CONFIG_FILE,
        USER_LOG_FILE,
        get_version,
    )
    ensure_user_dirs()
    CONFIG_FILE = USER_CONFIG_FILE
    LOG_FILE = USER_LOG_FILE
    VERSION = get_version()
except ImportError:
    CONFIG_FILE = os.path.join(APP_DIR, "config.json")
    LOG_FILE = os.path.join(APP_DIR, "miu.log")
    VERSION = "2.0.0"

from ipc import send_ipc_command, SOCKET_PATH
from cosmetics import COSMETIC_CATALOG
from pet_state import Personality

ONEKO_PY = os.path.join(APP_DIR, "oneko_plus.py")


def format_stats_output(summary):
    return (
        "Miu\n"
        "Today\n\n"
        f"Focus sessions: {summary.get('sessions', 0)}\n"
        f"Focus time: {summary.get('focus_time', '0m')}\n"
        f"Literary drops: {summary.get('drops_read', 0)}"
    )


def read_offline_stats():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                stats = cfg.get("stats", {})
                sec = stats.get("focus_seconds", 0)
                hours = sec // 3600
                mins = (sec % 3600) // 60
                time_str = f"{hours}h {mins:02d}m" if hours > 0 else f"{mins}m"
                return {
                    "sessions": stats.get("focus_sessions", 0),
                    "focus_time": time_str,
                    "drops_read": stats.get("quotes_read", 0),
                }
        except Exception:
            pass
    return {"sessions": 0, "focus_time": "0m", "drops_read": 0}


def launch_miu_background(args=None):
    cmd = [sys.executable, ONEKO_PY]
    if args:
        cmd.extend(args)
    try:
        log_file = open(LOG_FILE, "a", buffering=1, encoding="utf-8")
    except Exception:
        log_file = subprocess.DEVNULL
    subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=log_file,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    # Give the process a brief instant to bind the socket if needed
    for _ in range(15):
        time.sleep(0.1)
        if os.path.exists(SOCKET_PATH):
            break


def setup_gnome_shortcut():
    """Configures GNOME custom keybinding for summoning Miu."""
    import shutil as _shutil
    miu_bin = _shutil.which("miu") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "miu")
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        current = res.stdout.strip()
        custom_path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom_miu/"

        if custom_path not in current:
            if current in ("@as []", "[]", ""):
                new_list = f"['{custom_path}']"
            else:
                items = eval(current) if current.startswith("[") else []
                if custom_path not in items:
                    items.append(custom_path)
                new_list = str(items)
            subprocess.run(
                ["gsettings", "set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", new_list],
                check=True
            )

        schema = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{custom_path}"
        subprocess.run(["gsettings", "set", schema, "name", "Summon Miu"], check=True)
        subprocess.run(["gsettings", "set", schema, "command", f"{miu_bin} summon"], check=True)
        subprocess.run(["gsettings", "set", schema, "binding", "<Control><Alt>m"], check=True)
        print("✓ GNOME global shortcut registered successfully!")
        print("  Shortcut: <Control><Alt>m")
        print(f"  Command:  {miu_bin} summon")
        print("  Note: Within Miu's window, Ctrl+M also summons directly.")
    except Exception as e:
        print(f"Could not automatically register GNOME shortcut: {e}")
        print("You can configure it manually in GNOME Settings -> Keyboard -> Custom Shortcuts:")
        print("  Name:     Summon Miu")
        print(f"  Command:  {miu_bin} summon")
        print("  Shortcut: <Control><Alt>m or <Control>m")


def print_help():
    # Dynamically generate Customization & Personalities from the canonical source of truth
    themes_list = "\n".join(f"    {i+1}. {t['name']}" for i, t in enumerate(COSMETIC_CATALOG["themes"]))
    acc_list = "\n".join(f"    {i+1}. {a['name']}" for i, a in enumerate(COSMETIC_CATALOG["accessories"]))
    exp_list = "\n".join(f"    {i+1}. {e['name']}" for i, e in enumerate(COSMETIC_CATALOG["expressions"]))

    pers_descs = [
        ("CALM", "Slower movements (0.75x), longer restful pauses, and gentle sitting."),
        ("PLAYFUL", "Frequent reactions, occasional quick sprints, and inquisitive curiosity."),
        ("SLEEPY", "Frequent peaceful naps, slow relaxed movement, and high calmness."),
        ("ENERGETIC", "High movement frequency, eager edge exploring, and quick strides."),
        ("FOCUSED", "Quiet, steady presence, minimal movement; ideal for deep work."),
    ]
    pers_list = "\n".join(f"    {name}\n        {desc}" for name, desc in pers_descs)

    states_descs = [
        ("IDLE", "Resting quietly, breathing, looking around."),
        ("WALKING", "Trotting naturally across the desktop."),
        ("RUNNING", "Quick playful sprint when energetic or evading."),
        ("SITTING", "Sitting upright peacefully."),
        ("SLEEPING", "Curled up nap with gentle floating Zzz."),
        ("STRETCHING", "Yawning and claw stretch."),
        ("CURIOUS", "Alert look with perked ears."),
        ("HAPPY", "Purring happily with heart particles."),
        ("FOCUSED", "Calm companion state during focus sessions."),
        ("BREAK", "Relaxed celebratory state during breaks."),
        ("CLIMBING", "Scaling vertical window edges with claws."),
        ("EXPLORING", "Navigating window ledges and desktop perimeters."),
    ]
    states_list = "\n".join(f"    {name}\n        {desc}" for name, desc in states_descs)

    help_text = f"""MIU
A quiet desktop companion for focus, small moments of literature,
and a little company while you work.

USAGE
    hi miu [COMMAND]

COMMANDS
    hi miu
        Wake / start Miu

    hi miu --home
        Open Miu Home (futuristic control center)

    hi miu --pomodoro
        Toggle / start Pomodoro mode

    hi miu --focus
        Start a 45-minute focus session

    hi miu --pause
        Pause the current timer

    hi miu --resume
        Resume the current timer

    hi miu --reset
        Reset the current timer

    hi miu --break
        Start a break (default: 5 min)

    hi miu --literary
        Show one literary line on the desktop

    hi miu --customize
        Open pet customization (character editor)

    hi miu --stats
        Show today's focus statistics

    hi miu --version
        Show Miu version

    hi miu --stop
        Rest Miu and close companion

    hi miu summon, --summon
        Summon Miu to your active workspace / cursor (Ctrl+M)

    hi miu --setup-shortcut
        Register global shortcut <Control><Alt>m in GNOME

    hi miu --help, -h
        Show this help

FOCUS SYSTEM
    DEFAULT FOCUS:  45 minutes
    SHORT BREAK:     5 minutes
    LONG BREAK:     15 minutes (every 4th cycle)

    During focus, Miu enters FOCUSED behaviour:
    Miu becomes calmer, sits quietly near your workspace,
    and minimizes movement to keep your desktop distraction-free.
    When the session completes, Miu enters BREAK behaviour.

LITERARY SYSTEM
    Literary Drops are strictly ONE LINE of text + author attribution.
    No paragraphs, no excerpts, and no fake or generated quotations.
    Bundled library: 106 verified public-domain classics (Camus,
    Borges, Tolstoy, Woolf, Kafka, Rilke, Oliver, Dickinson, etc.).

    Delivery:
        Default: BREAKS ONLY (1 break = 1 literary drop)
        Optional: Occasional (timed intervals) or Off

    Controls:
        [Save]    Save current line to local favorites
        [Next]    Show another literary line
        [Close]   Dismiss the card

PET PERSONALITIES
{pers_list}

PET BEHAVIOURAL STATES
{states_list}

CURRENT CUSTOMIZATION
    CURRENT COAT / SKIN THEMES:
{themes_list}

    CURRENT ACCESSORIES:
{acc_list}

    CURRENT EYE EXPRESSIONS:
{exp_list}

    Custom PNG accessory overlays can be added anytime through:
    ~/.local/share/miu/accessories/

DESKTOP FEATURES
    • Desktop Pet: Lives quietly on the screen as a transparent companion.
    • Desktop-Aware Roaming: Naturally roams desktop area with non-repetitive pathing.
    • Window Climbing & Ledges: Discovers windows, climbs sides, walks top ledges, and sits on corners.
    • Cursor Courtesy: Yields and scampers away when mouse cursor approaches to prevent obstruction.
    • Dragging: Left-click and drag Miu anywhere on the desktop.
    • Position Persistence: Miu remembers where you last placed it.
    • System Tray: Compact AppIndicator3 menu for quick actions.
    • Context Menu: Right-click Miu for immediate desktop controls.
    • Timer Badge: Unobtrusive collar badge (Always, On Hover, or Hidden).
    • Non-Distracting: Never steals focus or creates loud interruptions.

ATTRIBUTION
    Initially based on Oneko. Later customized and evolved by Vaibhava.
"""
    print(help_text.strip())


def main():
    args = sys.argv[1:]

    # Remove leading "miu" if invoked as `hi miu ...`
    if args and args[0] == "miu":
        args = args[1:]

    # 1. Help flag
    if not args or "--help" in args or "-h" in args:
        if not args:
            # `hi miu` with no arguments -> Wake / Start Miu
            success, resp = send_ipc_command("wake")
            if success:
                print(resp.get("msg", "Miu wakes."))
            else:
                launch_miu_background()
                print("Miu wakes.")
            return
        else:
            print_help()
            return

    # Summon command: `hi miu summon`, `hi miu --summon`, `miu summon`
    if "summon" in args or "--summon" in args or "-m" in args:
        success, resp = send_ipc_command("summon")
        if success:
            print(resp.get("msg", "Miu is on the way!"))
        else:
            launch_miu_background()
            print("Miu wakes and comes to you.")
        return

    # Shortcut setup command: `hi miu --setup-shortcut`
    if "--setup-shortcut" in args or "setup-shortcut" in args:
        setup_gnome_shortcut()
        return

    # 2. Version flag
    if "--version" in args or "-v" in args:
        print(f"Miu {VERSION}")
        return

    # Home flag
    if "--home" in args or "-H" in args or "home" in args:
        success, resp = send_ipc_command("home")
        if success:
            print(resp.get("msg", "Miu Home opened."))
        else:
            launch_miu_background(["--home"])
            print("Miu started with Home.")
        return

    # Pomodoro mode toggle flag
    if "--pomodoro" in args or "-p" in args or "pomodoro" in args:
        success, resp = send_ipc_command("pomodoro_enable")
        if success:
            print("Pomodoro mode enabled.")
        else:
            launch_miu_background(["--pomodoro"])
            print("Miu started in Pomodoro mode.")
        return

    # 3. Focus flag
    if "--focus" in args or "-f" in args:
        success, resp = send_ipc_command("focus")
        if success:
            print(resp.get("msg", "Miu is focused.\n45:00 started."))
        else:
            launch_miu_background(["--focus"])
            print("Miu is focused.\n45:00 started.")
        return

    # 4. Pause flag
    if "--pause" in args:
        success, resp = send_ipc_command("pause")
        if success:
            print(resp.get("msg", "Miu paused."))
        else:
            print("Miu is not currently running. Start Miu with 'hi miu'.")
        return

    # 5. Resume flag
    if "--resume" in args:
        success, resp = send_ipc_command("resume")
        if success:
            print(resp.get("msg", "Miu resumed."))
        else:
            print("Miu is not currently running. Start Miu with 'hi miu'.")
        return

    # 6. Reset flag
    if "--reset" in args:
        success, resp = send_ipc_command("reset")
        if success:
            print(resp.get("msg", "Miu reset."))
        else:
            print("Miu is not currently running. Start Miu with 'hi miu'.")
        return

    # 7. Break flag
    if "--break" in args:
        success, resp = send_ipc_command("break")
        if success:
            print(resp.get("msg", "Miu is on break.\n05:00 started."))
        else:
            print("Miu is not currently running. Start Miu with 'hi miu'.")
        return

    # 8. Literary flag
    if "--literary" in args:
        success, resp = send_ipc_command("literary")
        if success:
            print(resp.get("msg", "Miu has left a line for you."))
        else:
            print("Miu is not currently running. Start Miu with 'hi miu'.")
        return

    # 9. Customize flag
    if "--customize" in args or "-c" in args:
        success, resp = send_ipc_command("customize")
        if success:
            print(resp.get("msg", "Miu customization opened."))
        else:
            launch_miu_background(["--customize"])
            print("Miu customization opened.")
        return

    # 10. Stats flag
    if "--stats" in args or "-s" in args:
        success, resp = send_ipc_command("stats")
        if success and "stats" in resp:
            print(format_stats_output(resp["stats"]))
        else:
            stats = read_offline_stats()
            print(format_stats_output(stats))
        return

    # 11. Stop / Quit flag
    if "--stop" in args or "--quit" in args:
        success, resp = send_ipc_command("quit")
        if success:
            print("Miu is resting.")
        else:
            subprocess.run(["pkill", "-f", "oneko_plus.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Miu is resting.")
        return

    # Fallback for unknown argument
    print(f"Unknown command: {' '.join(args)}")
    print("Try 'hi miu --help' for available commands.")


if __name__ == "__main__":
    main()
