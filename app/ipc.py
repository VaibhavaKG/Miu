"""
Lightweight IPC Server and Client for Miu Desktop Companion.

Uses a local Unix domain socket in $XDG_RUNTIME_DIR for single-instance
communication between the CLI (hi miu) and the running desktop pet.
"""

import os
import sys
import json
import socket
import errno
import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

try:
    from paths import SOCKET_PATH
except ImportError:
    SOCKET_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "miu.sock")


class MiuIPCServer:
    def __init__(self, app):
        self.app = app
        self.server_sock = None
        self.source_id = None
        self._start_server()

    def _start_server(self):
        # Check if another instance is already running
        if os.path.exists(SOCKET_PATH):
            test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                test_sock.connect(SOCKET_PATH)
                test_sock.close()
                # If connect succeeded, another instance is alive
                print("Warning: Another Miu instance is already listening on", SOCKET_PATH)
                return
            except (socket.error, ConnectionRefusedError):
                # Stale socket from previous crash or unclean exit
                try:
                    os.unlink(SOCKET_PATH)
                except OSError:
                    pass
            finally:
                test_sock.close()

        try:
            self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_sock.setblocking(False)
            self.server_sock.bind(SOCKET_PATH)
            self.server_sock.listen(5)
            # Set permissions: user only
            os.chmod(SOCKET_PATH, 0o700)

            # Register with GLib event loop for non-blocking event-driven processing
            self.source_id = GLib.io_add_watch(
                self.server_sock.fileno(),
                GLib.IO_IN,
                self._on_client_connect
            )
        except Exception as e:
            print(f"Could not bind Miu IPC server on {SOCKET_PATH}: {e}", file=sys.stderr)

    def _on_client_connect(self, source, condition):
        if not self.server_sock:
            return False

        try:
            conn, _ = self.server_sock.accept()
            conn.settimeout(2.0)
            data = conn.recv(4096)
            if data:
                try:
                    payload = json.loads(data.decode("utf-8"))
                    response = self._handle_command(payload)
                except Exception as e:
                    response = {"status": "error", "msg": str(e)}
                conn.sendall(json.dumps(response).encode("utf-8"))
            conn.close()
        except Exception:
            pass
        return True

    def _handle_command(self, payload):
        cmd = payload.get("cmd", "")
        app = self.app

        if cmd == "ping":
            return {"status": "ok", "msg": "pong"}

        elif cmd == "summon":
            res = app.summon_miu() if hasattr(app, "summon_miu") else {"status": "ok", "msg": "Miu is on the way!"}
            app.present()
            return {"status": "ok", "msg": res.get("msg", "Miu is on the way!")}

        elif cmd == "wake":
            app.set_pet_paused(False)
            app.present()
            return {"status": "ok", "msg": "Miu is awake."}

        elif cmd == "focus":
            app.start_focus_session()
            app.present()
            dur = app.config.get("focus_duration_min", 45)
            return {
                "status": "ok",
                "msg": f"Miu is focused.\n{dur:02d}:00 started."
            }

        elif cmd == "pause":
            app.pomodoro.pause()
            app.tray.update_menu()
            app.queue_draw()
            return {"status": "ok", "msg": "Miu paused."}

        elif cmd == "resume":
            app.pomodoro.resume()
            app.tray.update_menu()
            app.queue_draw()
            return {"status": "ok", "msg": "Miu resumed."}

        elif cmd == "reset":
            if hasattr(app, "reset_session"):
                app.reset_session()
            else:
                app.pomodoro.reset()
                app.tray.update_menu()
                app.queue_draw()
            return {"status": "ok", "msg": "Miu reset."}

        elif cmd in ("simulate_completion", "test_complete"):
            if hasattr(app, "simulate_focus_completion"):
                app.simulate_focus_completion()
                return {"status": "ok", "msg": "Focus timer set to 1s for immediate completion."}
            elif hasattr(app, "pomodoro"):
                app.pomodoro.time_left = 1
                return {"status": "ok", "msg": "Pomodoro time_left set to 1."}

        elif cmd == "break":
            app.pomodoro.start_short_break()
            app.pet_state.set_break_mode(True)
            app.tray.update_menu()
            app.queue_draw()
            m = app.config.get("short_break_min", 5)
            return {
                "status": "ok",
                "msg": f"Miu is on break.\n{m:02d}:00 started."
            }

        elif cmd == "literary":
            app.trigger_literary_drop()
            app.present()
            return {"status": "ok", "msg": "Miu has left a line for you."}

        elif cmd == "customize":
            GLib.idle_add(app.open_preferences)
            return {"status": "ok", "msg": "Miu customization opened."}

        elif cmd == "stats":
            summary = app.pomodoro.get_stats_summary()
            return {
                "status": "ok",
                "stats": summary,
                "msg": f"Miu\nToday\n\nFocus sessions: {summary['sessions']}\nFocus time: {summary['focus_time']}\nLiterary drops: {summary['drops_read']}"
            }

        elif cmd == "home":
            if hasattr(app, "open_home"):
                GLib.idle_add(app.open_home)
            return {"status": "ok", "msg": "Miu Home opened."}

        elif cmd == "pomodoro_enable":
            app.config["pomodoro_enabled"] = True
            app.save_config()
            app.tray.update_menu()
            app.update_window_shape_and_size()
            app.queue_draw()
            return {"status": "ok", "msg": "Pomodoro mode enabled."}

        elif cmd == "pomodoro_disable":
            app.config["pomodoro_enabled"] = False
            app.save_config()
            app.tray.update_menu()
            app.update_window_shape_and_size()
            app.queue_draw()
            return {"status": "ok", "msg": "Pomodoro mode disabled."}

        elif cmd == "get_state":
            summary = app.pomodoro.get_stats_summary()
            return {
                "status": "ok",
                "pet_name": app.config.get("pet_name", "Miu"),
                "personality": app.config.get("personality", "calm"),
                "theme": app.config.get("cat_theme", "classic"),
                "accessory": app.config.get("cat_accessory", "none"),
                "expression": app.config.get("cat_expression", "normal"),
                "pomodoro_enabled": app.config.get("pomodoro_enabled", False),
                "phase": app.pomodoro.phase.value if hasattr(app.pomodoro.phase, "value") else str(app.pomodoro.phase),
                "time_string": app.pomodoro.get_time_string(),
                "time_left": app.pomodoro.time_left,
                "stats": summary
            }

        elif cmd == "get_spotify":
            track = None
            if hasattr(app, "spotify_manager") and app.spotify_manager:
                track = app.spotify_manager.get_current_track()
            else:
                try:
                    from spotify import SpotifyManager
                    sm = SpotifyManager()
                    track = sm.get_current_track()
                except Exception:
                    track = None
            return {"status": "ok", "track": track}

        elif cmd == "yarn":
            if hasattr(app, "living_world") and app.living_world:
                item = app.living_world.spawn_yarn_ball()
                if item:
                    app.current_destination = {
                        "type": "walk",
                        "pos": (item.x, item.y),
                        "post_action": "investigate_item"
                    }
                    app.pet_state.state = app.pet_state.state.WALKING
                    return {"status": "ok", "msg": "Spawned yarn ball."}
            return {"status": "error", "msg": "Could not spawn yarn ball."}

        elif cmd == "quit":
            GLib.idle_add(app.quit_app)
            return {"status": "ok", "msg": "Miu is resting."}

        return {"status": "error", "msg": f"Unknown command '{cmd}'"}

    def stop(self):
        if self.source_id:
            GLib.source_remove(self.source_id)
            self.source_id = None
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except Exception:
                pass


def send_ipc_command(cmd, args=None, timeout=2.0):
    """Sends command to running Miu instance. Returns (success: bool, response: dict)."""
    if not os.path.exists(SOCKET_PATH):
        return False, {"status": "error", "msg": "Miu is not running"}

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(SOCKET_PATH)
        req = {"cmd": cmd, "args": args or {}}
        sock.sendall(json.dumps(req).encode("utf-8"))
        data = sock.recv(8192)
        if data:
            return True, json.loads(data.decode("utf-8"))
        return False, {"status": "error", "msg": "Empty response"}
    except (socket.error, ConnectionRefusedError) as e:
        # Socket file exists but connection refused -> stale socket
        try:
            os.unlink(SOCKET_PATH)
        except OSError:
            pass
        return False, {"status": "error", "msg": "Miu is not running"}
    finally:
        sock.close()
