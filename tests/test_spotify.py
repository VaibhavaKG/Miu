import unittest
import os
import shutil
from unittest.mock import patch, MagicMock

import app.spotify
from app.spotify import SpotifyManager, CACHE_DIR

class TestSpotifyManager(unittest.TestCase):

    def setUp(self):
        # Create cache dir for tests if not exists
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
    @patch('app.spotify.Gio', None)
    def test_instantiation_without_dbus(self):
        # Mocking Gio to None to simulate D-Bus unavailability
        manager = SpotifyManager()
        self.assertIsNone(manager.bus)
        
    def test_get_current_track_no_player(self):
        manager = SpotifyManager()
        # Mock _get_player_name to return None
        manager._get_player_name = MagicMock(return_value=None)
        
        track = manager.get_current_track()
        self.assertIsNone(track)
        
    def test_is_available_no_player(self):
        manager = SpotifyManager()
        manager._get_player_name = MagicMock(return_value=None)
        self.assertFalse(manager.is_available())
        
    @patch('app.spotify.Gio')
    @patch('app.spotify.GLib')
    def test_get_current_track_success(self, mock_glib, mock_gio):
        manager = SpotifyManager()
        
        # Mock bus and its call_sync
        manager.bus = MagicMock()
        manager._get_player_name = MagicMock(return_value="org.mpris.MediaPlayer2.spotify")
        
        # Mock D-Bus responses
        mock_status_reply = MagicMock()
        mock_status_reply.get_child_value().get_variant().get_string.return_value = "Playing"
        
        mock_meta_reply = MagicMock()
        metadata_variant = MagicMock()
        mock_meta_reply.get_child_value().get_variant.return_value = metadata_variant
        
        # Mock metadata values
        title_var = MagicMock()
        title_var.get_string.return_value = "Test Title"
        
        artist_var = MagicMock()
        artist_var.unpack.return_value = ["Test Artist"]
        
        album_var = MagicMock()
        album_var.get_string.return_value = "Test Album"
        
        def lookup_side_effect(key, type):
            if key == "xesam:title":
                return title_var
            elif key == "xesam:artist":
                return artist_var
            elif key == "xesam:album":
                return album_var
            return None
            
        metadata_variant.lookup_value.side_effect = lookup_side_effect
        
        manager.bus.call_sync.side_effect = [mock_status_reply, mock_meta_reply]
        
        track = manager.get_current_track()
        
        self.assertIsNotNone(track)
        self.assertEqual(track["title"], "Test Title")
        self.assertEqual(track["artist"], "Test Artist")
        self.assertEqual(track["album"], "Test Album")
        self.assertTrue(track["is_playing"])
        
    def test_album_art_cache_directory_creation(self):
        # Even if we delete it, manager instantiation should recreate it
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            
        self.assertFalse(CACHE_DIR.exists())
        manager = SpotifyManager()
        self.assertTrue(CACHE_DIR.exists())

if __name__ == '__main__':
    unittest.main()
