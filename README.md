# Miu 2.0 🐱

A tiny pixel cat that lives on your Linux desktop with a Pomodoro timer you control from the terminal.

![Miu demo](assets/demo.gif) <!-- TODO: record a GIF -->

---

## Why Miu?

I've always liked the idea of a little desktop cat — something alive on the screen, keeping me company while I work. But I'm allergic to real cat fur, so a pixel cat is the next best thing. Miu is that cat: she follows your cursor, naps when you're idle, and nudges you when your focus timer runs out.

Started from Oneko, then heavily customised and expanded.

## What Miu Does

- **Follows your cursor** across the screen with classic pixel-art animations.
- **Sleeps** when you stop moving, **scratches** near screen edges.
- **Runs a Pomodoro timer** shown as a speech bubble above her head.
- **Notifies you** when the timer ends (desktop notification + animation).
- **Hides on demand** — the timer keeps running silently in the background.

All interaction is through the `miu` command. No GUI, no settings screens.

### Commands

| Command | What it does |
|---------|-------------|
| `miu hi` | Miu appears, follows cursor, says "mew!" |
| `miu bye` | Miu hides (timer keeps running) |
| `miu --focus` | Start a 50-minute focus timer |
| `miu --focus 25` | Custom-length focus timer |
| `miu --break` | Start a 10-minute break timer |
| `miu --break 5` | Custom-length break timer |
| `miu --pause` | Pause the timer |
| `miu --resume` | Resume the timer |
| `miu --stop` | Cancel the timer |
| `miu --status` | Show remaining time |
| `miu quit` | Close the app |

## Installation

```bash
git clone https://github.com/VaibhavaKG/Miu.git ~/Applications/miu
~/Applications/miu/install.sh
```

That's it. No pip, no npm, no build step. Miu uses **Python 3, GTK 3, and Cairo** — all pre-installed on Fedora and most GNOME desktops.

### Dependencies

Already installed on Fedora. On other distros:

```bash
# Ubuntu / Debian
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Arch
sudo pacman -S python-gobject gtk3
```

### Try it

```bash
miu hi            # cat appears
miu --focus 1     # 1-minute test timer
miu --status      # check time
miu bye           # hide cat
miu quit          # stop app
```

## Known Limitations

**Wayland**: Miu runs under XWayland (`GDK_BACKEND=x11`) so transparency, always-on-top, and click-through work. On Wayland sessions (GNOME, KDE), cursor tracking may pause when the mouse is over a native Wayland window — the cat catches up when the cursor crosses an X11 surface. This is a fundamental XWayland limitation.

**Multi-monitor**: The cat lives on the primary monitor only.

## Credits

Developed by **Vaibhava**.

Sprite art from the classic Neko desktop toy (Naoshi Watanabe, 1989). Movement logic adapted from [oneko.js](https://github.com/adryd325/oneko.js) by adryd325.

## License

MIT — see [LICENSE](LICENSE).
