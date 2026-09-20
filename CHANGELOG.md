# Changelog

## [2.1.0] — 2026-09-21
### Added
- Miu Home: futuristic interactive control center (`miu --home`)
- Pomodoro is now optional — Miu is a companion first
- Spotify/MPRIS now-playing display in Miu Home
- Autonomous yarn ball play behavior with cooldowns
- Enhanced idle behaviors (expression changes, edge exploration, cursor reactions)
- `miu --pomodoro` to enable Pomodoro mode
- `miu --home` to open Miu Home

### Changed
- Miu launches as pure desktop companion by default (no timer)
- CLI help text simplified
- Tray menu updated with Home and Pomodoro toggle
- All hardcoded paths removed for portability

### Fixed
- Missing GdkPixbuf import in preferences dialog
- Hardcoded user paths in GNOME shortcut setup

## [2.0.0] — 2026-09-18
### Added
- Complete rewrite from Oneko base
- 45-minute focus sessions with 5/15 minute breaks
- Living world system (toys, discoveries, sleep, absence)
- 106-work literary collection
- 8 coat themes, 10 accessories, 5 expressions
- Desktop-aware window climbing
- Cursor personality system
- 60-second celebration overlay
- XDG-compliant data storage
- Full IPC system
- System tray integration
