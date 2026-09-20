# Contributing to Miu

Welcome! We are excited that you want to contribute to Miu, the desktop companion project. Here's a brief guide to get you started.

## Setting Up Development Environment

Miu is built with Python 3 and GTK3. 

### Dependencies
You will need the following dependencies installed:
- Python 3
- PyGObject
- GTK3
- Cairo
- libappindicator (for system tray support)

## Running Tests
Run the test suite using `pytest`. Make sure to install dependencies first.
```bash
pytest
```

## Code Style Notes
- We use standard Python conventions (PEP 8).
- Use `GDK_BACKEND=x11` for GTK operations.
- All user data goes to XDG directories (`~/.config/miu/`, `~/.local/share/miu/`, `~/.cache/miu/`).
- Do not hardcode user home paths.
- Keep imports clean and explicit.

## How to Add Literary Works
Add new literary works to the data files ensuring they fit the format structure used by the app. Store them in the appropriate data structures or asset folders.

## How to Add Custom Accessories
Custom accessories can be added by adding their asset files to the assets directory and updating the configuration files or dictionaries that define available accessories for Miu. Make sure to adhere to existing image formats and dimensions.
