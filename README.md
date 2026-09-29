# Miu 2.0 🐱

A tiny pixel cat that lives on your Linux desktop with a Pomodoro timer you control from the terminal.

---

## Why Miu?

I've always liked the idea of a little desktop cat — something alive on the screen, keeping me company while I work. But I'm allergic to real cat fur, so a pixel cat is the next best thing. Miu is that cat: she follows your cursor, naps when you're idle, and nudges you when your focus timer runs out.

Started from Oneko, then heavily customised and expanded.

## What Miu Does

Miu is a desktop cat that:

- **Follows your cursor** across the screen with classic pixel-art walking animations.
- **Sleeps** when you stop moving the mouse, **scratches** walls near screen edges.
- **Runs a Pomodoro timer** shown as a speech bubble above her head.
- **Notifies you** with a desktop notification and animation when the timer ends.
- **Hides on demand** — the timer keeps running silently in the background.

All interaction is through the `miu` command in your terminal. No GUI controls, no dashboards.

### Commands

| Command | Description |
|---------|-------------|
| `miu hi` | Miu appears, follows cursor, says "mew!" |
| `miu bye` | Miu hides (timer keeps running silently) |
| `miu --focus` | Start a 50-minute focus timer |
| `miu --focus 25` | Start a custom-length focus timer |
| `miu --break` | Start a 10-minute break timer |
| `miu --break 5` | Start a custom-length break timer |
| `miu --pause` | Pause the timer |
| `miu --resume` | Resume the timer |
| `miu --stop` | Cancel the timer |
| `miu --status` | Show remaining time in bubble and terminal |
| `miu quit` | Close the app |

## Installation

```bash
git clone https://github.com/VaibhavaKG/Miu.git ~/Applications/miu
cd ~/Applications/miu
npm install
./install.sh
```

The install script puts the `miu` command in `~/.local/bin` and optionally adds an autostart entry.

### Run from source

```bash
cd ~/Applications/miu
npm start
```

In a separate terminal:

```bash
miu hi
```

### Build distributable packages

```bash
npm run build
```

Produces AppImage, `.rpm`, and `.deb` in `dist/`.

### Install from .rpm (Fedora)

```bash
sudo dnf install ./dist/miu-*.rpm
```

### Install from .deb (Ubuntu/Debian)

```bash
sudo dpkg -i ./dist/miu-*.deb
```

## How It Works

- **Electron** with a fullscreen transparent, frameless, always-on-top, click-through window.
- The cat sprite follows the global cursor position (polled via `screen.getCursorScreenPoint()`).
- The `miu` CLI talks to the running app over a Unix socket at `$XDG_RUNTIME_DIR/miu.sock`.
- If the app isn't running, `miu hi` auto-starts it.
- Last custom timer durations are saved in `~/.config/miu/config.json`.

## Known Limitations

**Wayland**: Miu runs under XWayland (`--ozone-platform=x11`) for reliable transparency and always-on-top behaviour. On Wayland sessions (GNOME, KDE), cursor tracking may pause when the mouse is over a native Wayland window — the cat catches up as soon as the cursor crosses an X11 surface. This is a fundamental XWayland limitation, not a bug.

**System tray**: On GNOME the tray icon requires the [AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/). Miu works fully without a tray — use the CLI.

## Credits

Developed by **Vaibhava**.

Sprite art from the classic Neko desktop toy (Naoshi Watanabe, 1989). JavaScript base from [oneko.js](https://github.com/adryd325/oneko.js) by adryd325.

## License

MIT — see [LICENSE](LICENSE).
