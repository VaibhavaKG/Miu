// main.js — Miu Electron main process
// Transparent fullscreen window, Unix socket IPC, Pomodoro timer, optional tray.

const { app, BrowserWindow, screen, Tray, Menu, nativeImage } = require("electron");
const path = require("path");
const fs = require("fs");
const net = require("net");
const { execFile } = require("child_process");

// Force XWayland so transparency + always-on-top work on Wayland
app.commandLine.appendSwitch("ozone-platform", "x11");
// Transparency support
app.commandLine.appendSwitch("enable-transparent-visuals");
app.commandLine.appendSwitch("disable-gpu-compositing");

const CAT_NAME = "Miu";

// --- Config persistence ---
const configDir =
  path.join(process.env.XDG_CONFIG_HOME || path.join(process.env.HOME, ".config"), "miu");
const configPath = path.join(configDir, "config.json");

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(configPath, "utf8"));
  } catch {
    return { focusMinutes: 50, breakMinutes: 10 };
  }
}

function saveConfig(cfg) {
  try {
    fs.mkdirSync(configDir, { recursive: true });
    fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2));
  } catch (e) {
    console.error("Failed to save config:", e.message);
  }
}

let config = loadConfig();

// --- Timer state ---
let timerState = {
  running: false,
  paused: false,
  type: null,       // "focus" or "break"
  remaining: 0,     // seconds
  total: 0,
  intervalId: null,
};

// --- Window & tray ---
let win = null;
let tray = null;
let catVisible = false;

function createWindow() {
  // Use the primary display size for a fullscreen transparent overlay
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  win = new BrowserWindow({
    width,
    height,
    x: 0,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    resizable: false,
    focusable: false,
    show: false,
    type: "toolbar", // helps skip taskbar on some WMs
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Click-through: ignore mouse events but forward them so the OS handles clicks
  win.setIgnoreMouseEvents(true, { forward: true });

  // Prevent the window from being closed by Alt+F4 etc; hide instead
  win.on("close", (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      hideCat();
    }
  });

  win.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Start cursor polling once the renderer is ready
  win.webContents.on("did-finish-load", () => {
    startCursorPolling();
  });
}

// --- Cursor polling ---
let cursorIntervalId = null;

function startCursorPolling() {
  if (cursorIntervalId) return;
  cursorIntervalId = setInterval(() => {
    if (!win || win.isDestroyed()) return;
    const pos = screen.getCursorScreenPoint();
    win.webContents.send("cursor-move", pos.x, pos.y);
  }, 50);
}

// --- Show / hide cat ---
function showCat() {
  if (!win || win.isDestroyed()) return;
  catVisible = true;
  win.showInactive();
  win.webContents.send("miu-show");
}

function hideCat() {
  if (!win || win.isDestroyed()) return;
  catVisible = false;
  win.webContents.send("miu-hide");
  // Don't actually hide the window if timer is running (need to show bubble)
  // Instead, renderer handles visibility of the cat element
}

// --- Timer ---
function startTimer(type, minutes) {
  stopTimer();
  timerState.running = true;
  timerState.paused = false;
  timerState.type = type;
  timerState.remaining = minutes * 60;
  timerState.total = minutes * 60;

  // Save custom duration to config
  if (type === "focus") config.focusMinutes = minutes;
  else config.breakMinutes = minutes;
  saveConfig(config);

  timerState.intervalId = setInterval(() => {
    if (timerState.paused) return;
    timerState.remaining--;
    if (win && !win.isDestroyed()) {
      win.webContents.send("miu-timer-tick", timerState.remaining);
    }
    if (timerState.remaining <= 0) {
      timerEnd();
    }
  }, 1000);

  // Show cat if hidden
  if (!catVisible) showCat();
  if (win && !win.isDestroyed()) {
    win.webContents.send("miu-timer-start", type, timerState.remaining);
  }
}

function timerEnd() {
  const type = timerState.type;
  clearInterval(timerState.intervalId);
  timerState.running = false;
  timerState.paused = false;
  timerState.intervalId = null;

  // Show cat if hidden
  if (!catVisible) showCat();
  if (win && !win.isDestroyed()) {
    win.webContents.send("miu-timer-end", type);
  }

  // Desktop notification via notify-send
  try {
    execFile("notify-send", [
      "--app-name", CAT_NAME,
      `${CAT_NAME}: Time's up! 🐾`,
      type === "focus" ? "Focus session complete." : "Break is over!",
    ]);
  } catch { /* notify-send may not exist */ }
}

function stopTimer() {
  if (timerState.intervalId) clearInterval(timerState.intervalId);
  timerState.running = false;
  timerState.paused = false;
  timerState.type = null;
  timerState.remaining = 0;
  timerState.intervalId = null;
  if (win && !win.isDestroyed()) {
    win.webContents.send("miu-timer-stop");
  }
}

function pauseTimer() {
  if (timerState.running) timerState.paused = true;
}

function resumeTimer() {
  if (timerState.running) timerState.paused = false;
}

function getStatus() {
  if (!timerState.running) return { running: false };
  const m = Math.floor(timerState.remaining / 60);
  const s = timerState.remaining % 60;
  return {
    running: true,
    paused: timerState.paused,
    type: timerState.type,
    remaining: `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`,
    remainingSeconds: timerState.remaining,
  };
}

// --- IPC command handler ---
function handleCommand(cmd) {
  const parts = cmd.trim().split(/\s+/);
  const first = parts[0]?.toLowerCase();
  const second = parts[1]?.toLowerCase();

  // Handle "hi miu" and "bye miu" aliases
  if (first === "hi" && second === "miu") {
    showCat();
    if (win && !win.isDestroyed()) {
      win.webContents.send("miu-greeting");
    }
    return { ok: true, msg: `${CAT_NAME} says: mew!` };
  }
  if (first === "bye" && second === "miu") {
    hideCat();
    return { ok: true, msg: `${CAT_NAME} hides. Timer keeps running.` };
  }

  // Handle "miu <command>" or just "<command>"
  let command, arg;
  if (first === "miu") {
    command = second;
    arg = parts[2];
  } else {
    command = first;
    arg = second;
  }

  // Also handle bare "hi" / "bye"
  if (command === "hi") {
    showCat();
    if (win && !win.isDestroyed()) {
      win.webContents.send("miu-greeting");
    }
    return { ok: true, msg: `${CAT_NAME} says: mew!` };
  }
  if (command === "bye") {
    hideCat();
    return { ok: true, msg: `${CAT_NAME} hides. Timer keeps running.` };
  }

  switch (command) {
    case "--focus": {
      const mins = parseInt(arg, 10) || config.focusMinutes || 50;
      startTimer("focus", mins);
      return { ok: true, msg: `Focus timer started: ${mins} min.` };
    }
    case "--break": {
      const mins = parseInt(arg, 10) || config.breakMinutes || 10;
      startTimer("break", mins);
      return { ok: true, msg: `Break timer started: ${mins} min.` };
    }
    case "--pause":
      pauseTimer();
      return { ok: true, msg: "Timer paused." };
    case "--resume":
      resumeTimer();
      return { ok: true, msg: "Timer resumed." };
    case "--stop":
      stopTimer();
      return { ok: true, msg: "Timer stopped." };
    case "--status": {
      const st = getStatus();
      if (!st.running) return { ok: true, msg: "No timer running." };
      const label = st.paused ? " (paused)" : "";
      const statusMsg = `${st.type}: ${st.remaining}${label}`;
      // Also show in bubble for 3 seconds
      if (win && !win.isDestroyed()) {
        win.webContents.send("miu-bubble", st.remaining, 3000);
      }
      return { ok: true, msg: statusMsg };
    }
    case "quit":
      app.isQuitting = true;
      app.quit();
      return { ok: true, msg: `${CAT_NAME} says goodbye.` };
    default:
      return { ok: false, msg: `Unknown command: ${cmd.trim()}` };
  }
}

// --- Unix socket server ---
const socketPath =
  path.join(process.env.XDG_RUNTIME_DIR || "/tmp", "miu.sock");

let server = null;

function startSocketServer() {
  // Remove stale socket
  try { fs.unlinkSync(socketPath); } catch { /* ok */ }

  server = net.createServer((conn) => {
    let data = "";
    conn.on("data", (chunk) => {
      data += chunk.toString();
      // Commands are newline-delimited
      const lines = data.split("\n");
      data = lines.pop(); // keep incomplete line
      for (const line of lines) {
        if (!line.trim()) continue;
        const result = handleCommand(line);
        conn.write(JSON.stringify(result) + "\n");
      }
    });
    conn.on("error", () => {}); // ignore broken pipes
  });

  server.listen(socketPath, () => {
    // Make socket accessible to the user
    try { fs.chmodSync(socketPath, 0o600); } catch { /* ok */ }
  });

  server.on("error", (e) => {
    console.error("Socket server error:", e.message);
  });
}

// --- Optional tray ---
function createTray() {
  try {
    // Use a tiny 16x16 transparent icon; tray may fail on GNOME without AppIndicator
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    tray.setToolTip(CAT_NAME);
    const contextMenu = Menu.buildFromTemplate([
      { label: `Call ${CAT_NAME}`, click: () => { showCat(); if (win) win.webContents.send("miu-greeting"); } },
      { type: "separator" },
      { label: "Quit", click: () => { app.isQuitting = true; app.quit(); } },
    ]);
    tray.setContextMenu(contextMenu);
  } catch (e) {
    // Tray not available (e.g. GNOME without AppIndicator) — that's fine
    console.log("Tray not available:", e.message);
    tray = null;
  }
}

// --- App lifecycle ---
app.whenReady().then(() => {
  // Small delay for transparent visuals on some compositors
  setTimeout(() => {
    createWindow();
    createTray();
    startSocketServer();
  }, 300);
});

app.on("before-quit", () => {
  app.isQuitting = true;
  if (server) { try { server.close(); } catch {} }
  try { fs.unlinkSync(socketPath); } catch {}
  if (cursorIntervalId) clearInterval(cursorIntervalId);
});

app.on("window-all-closed", () => {
  app.quit();
});

// Prevent second instance
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
}
