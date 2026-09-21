# Miu 2.0

A small desktop companion for Linux.

Miu is a lightweight, frameless desktop cat built with Python, GTK 3, and Cairo. It quietly lives on your desktop, walks around, rests in corners, plays with things, and occasionally gets distracted.

You can simply run Miu and leave it alone, or open **Miu Home** for a more complete interface.

---

## Why Miu?

I recently happened to develop a minor interest in cats.

It seemed like a fun idea to have one around on my desktop, without having to deal with the actual cat part of owning a cat. So I started with **Oneko**, a small free desktop cat project, and gradually began changing it.

Over the following days, I kept adding things. Better behaviour, objects to interact with, a little home, music, focus sessions, customisation, and eventually a proper interface around it.

I named it **Miu**.

The funny part is that I still hate cats.

Especially the fact that they shed their fur absolutely everywhere.

So this is probably the ideal arrangement: I get a cat that walks around, plays with things, and keeps me company while I work, without leaving fur on my clothes.

---

## What Miu Does

### Desktop Companion

```bash
miu
```

Miu stays quietly on the desktop and can:

* Walk around windows
* Sleep and idle
* Play with small objects such as yarn
* Avoid the cursor while you work
* Be summoned to your cursor

### Miu Home

```bash
miu --home
```

Miu Home is the main interface for the project.

It includes Miu's habitat, appearance customisation, currently playing music, focus controls, and a small activity view.

The design takes inspiration from astronomical observatories, but keeps the interface deliberately minimal.

### Focus Mode

```bash
miu --focus
```

Miu can also act as a simple focus companion with 45-minute sessions and breaks.

It stays completely optional. Normal Miu does not show a timer or productivity overlay.

### Music

Miu Home can display the currently playing track through Linux MPRIS-compatible players such as Spotify.

---

## Commands

| Command           | Action                   |
| ----------------- | ------------------------ |
| `miu`             | Start Miu                |
| `miu --home`      | Open Miu Home            |
| `miu --focus`     | Start a focus session    |
| `miu --pause`     | Pause the session        |
| `miu --resume`    | Resume the session       |
| `miu --reset`     | Reset the session        |
| `miu --stop`      | Stop Miu                 |
| `miu summon`      | Summon Miu to the cursor |
| `miu --customize` | Open customisation       |

`Ctrl + M` can also be used to summon Miu.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/VaibhavaKG/Miu.git ~/.local/share/miu-app
```

Run the installer:

```bash
~/.local/share/miu-app/install.sh
```

The installer sets up the `miu` command and adds Miu to the application menu.

### Dependencies

#### Fedora

```bash
sudo dnf install python3-gobject gtk3 cairo libappindicator-gtk3 libwnck3
```

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 gir1.2-wnck-3.0
```

#### Arch

```bash
sudo pacman -S --needed python-gobject gtk3 cairo libappindicator-gtk3 libwnck3
```

---

## Built With

* Python
* GTK 3
* PyGObject
* Cairo
* Linux MPRIS

Miu is a native Linux application with no Electron or browser runtime.

There is no telemetry. User configuration, logs, accessories, and cached data remain on the local machine using standard XDG directories.

---

## Credits

Miu started with **Oneko**, a free desktop cat project, and has since been heavily customised and expanded.

Developed by **Vaibhava**.

## License

MIT
