"""
Spotify MPRIS D-Bus integration module.

The Media Player Remote Interfacing Specification (MPRIS) is a standard D-Bus
interface which aims to provide a common programmatic API for controlling media
players. It provides a mechanism for discovery, querying and basic playback
control of compliant media players, as well as a tracklist interface to add
context to the active media item.

This module provides a SpotifyManager class to interact with Spotify or any
MPRIS-compatible media player to retrieve current track metadata and download
album art.
"""

import os
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
import hashlib
import logging

try:
    import gi
    gi.require_version('Gio', '2.0')
    gi.require_version('GLib', '2.0')
    from gi.repository import Gio, GLib
except ImportError:
    Gio = None
    GLib = None

try:
    from paths import XDG_CACHE_HOME
except ImportError:
    try:
        from app.paths import XDG_CACHE_HOME
    except ImportError:
        XDG_CACHE_HOME = Path(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')))

CACHE_DIR = XDG_CACHE_HOME / 'miu' / 'album_art'
POLL_INTERVAL_MS = 8000

logger = logging.getLogger(__name__)

class SpotifyManager:
    """Manages integration with Spotify via MPRIS D-Bus interface."""

    def __init__(self):
        self.bus = None
        self._polling_id = None
        self._on_track_change_callback = None
        self.current_track_info = None

        try:
            if Gio is not None:
                self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except Exception as e:
            logger.error(f"Failed to connect to D-Bus session bus: {e}")
            self.bus = None
            
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create cache directory {CACHE_DIR}: {e}")

    def _get_player_name(self):
        """Find the D-Bus name for Spotify or the first available MPRIS player."""
        if self.bus is None:
            return None
            
        try:
            reply = self.bus.call_sync(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "ListNames",
                None,
                Gio.VariantType.new("(as)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            
            if reply:
                names = reply.get_child_value(0).unpack()
                mpris_names = [name for name in names if name.startswith("org.mpris.MediaPlayer2.")]
                
                if "org.mpris.MediaPlayer2.spotify" in mpris_names:
                    return "org.mpris.MediaPlayer2.spotify"
                elif mpris_names:
                    return mpris_names[0]
        except Exception as e:
            logger.error(f"Error querying D-Bus names: {e}")
            
        return None

    def is_available(self):
        """Check if an MPRIS player is available."""
        return self._get_player_name() is not None

    def get_current_track(self):
        """Retrieve information about the currently playing track."""
        if self.bus is None:
            return None

        player_name = self._get_player_name()
        if not player_name:
            return None

        try:
            # Get PlaybackStatus
            status_reply = self.bus.call_sync(
                player_name,
                "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties",
                "Get",
                GLib.Variant("(ss)", ("org.mpris.MediaPlayer2.Player", "PlaybackStatus")),
                Gio.VariantType.new("(v)"),
                Gio.DBusCallFlags.NONE,
                1000,
                None
            )
            
            if not status_reply:
                return None
                
            playback_status = status_reply.get_child_value(0).get_variant().get_string()
            is_playing = playback_status == "Playing"

            # Get Metadata
            meta_reply = self.bus.call_sync(
                player_name,
                "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties",
                "Get",
                GLib.Variant("(ss)", ("org.mpris.MediaPlayer2.Player", "Metadata")),
                Gio.VariantType.new("(v)"),
                Gio.DBusCallFlags.NONE,
                1000,
                None
            )
            
            if not meta_reply:
                return None

            metadata = meta_reply.get_child_value(0).get_variant()
            
            title = None
            artist = None
            album = None
            art_url = None
            
            try:
                title = metadata.lookup_value("xesam:title", GLib.VariantType("s"))
                title = title.get_string() if title else None
            except Exception:
                pass
                
            try:
                artist_var = metadata.lookup_value("xesam:artist", GLib.VariantType("as"))
                if artist_var:
                    artists = artist_var.unpack()
                    artist = ", ".join(artists) if artists else None
            except Exception:
                pass
                
            try:
                album = metadata.lookup_value("xesam:album", GLib.VariantType("s"))
                album = album.get_string() if album else None
            except Exception:
                pass
                
            try:
                art_url = metadata.lookup_value("mpris:artUrl", GLib.VariantType("s"))
                art_url = art_url.get_string() if art_url else None
            except Exception:
                pass
                
            art_path = None
            if art_url:
                art_path = self._download_album_art(art_url)
                
            self.current_track_info = {
                "title": title or "Unknown Title",
                "artist": artist or "Unknown Artist",
                "album": album or "Unknown Album",
                "art_path": art_path,
                "is_playing": is_playing
            }
            
            return self.current_track_info
            
        except Exception as e:
            logger.debug(f"Failed to get track info: {e}")
            return None

    def _download_album_art(self, url):
        """Download album art from URL and cache it locally."""
        if not url:
            return None
            
        if url.startswith("file://"):
            return url.replace("file://", "")
            
        try:
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".jpg"
            filename = f"{url_hash}{ext}"
            filepath = CACHE_DIR / filename
            
            if filepath.exists():
                return str(filepath)
                
            # Need to download
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    with open(filepath, 'wb') as f:
                        f.write(response.read())
                return str(filepath)
            except (urllib.error.URLError, Exception) as e:
                logger.debug(f"Failed to download album art from {url}: {e}")
                return None
                
        except Exception as e:
            logger.debug(f"Unexpected error handling album art url {url}: {e}")
            return None

    def set_on_track_change_callback(self, callback):
        self._on_track_change_callback = callback

    def _poll_track(self):
        """Poll the current track periodically."""
        try:
            new_track_info = self.get_current_track()
            if self._on_track_change_callback and new_track_info != self.current_track_info:
                self._on_track_change_callback(new_track_info)
        except Exception:
            pass
        return True  # Keep GLib timeout active

    def start_polling(self):
        """Start polling MPRIS player every 8 seconds."""
        if GLib is None:
            return
            
        if self._polling_id is None:
            self.get_current_track() # initial fetch
            self._polling_id = GLib.timeout_add(POLL_INTERVAL_MS, self._poll_track)

    def stop_polling(self):
        """Stop polling."""
        if GLib is not None and self._polling_id is not None:
            GLib.source_remove(self._polling_id)
            self._polling_id = None
