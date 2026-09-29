#!/usr/bin/env node
// cli.js — miu CLI. Talks to the running Miu app via Unix socket.
// Usage: miu hi | miu bye | miu --focus [N] | miu --break [N] | miu --pause | miu --resume | miu --stop | miu --status | miu quit

const net = require("net");
const path = require("path");
const { spawn } = require("child_process");

const SOCKET_PATH =
  path.join(process.env.XDG_RUNTIME_DIR || "/tmp", "miu.sock");

const args = process.argv.slice(2);
if (args.length === 0) {
  console.log("Usage: miu <command>");
  console.log("Commands: hi, bye, --focus [N], --break [N], --pause, --resume, --stop, --status, quit");
  process.exit(0);
}

// Build the command string from args
const command = args.join(" ");

function sendCommand(cmd, retries) {
  const client = net.createConnection(SOCKET_PATH, () => {
    client.write(cmd + "\n");
  });

  let response = "";
  client.on("data", (data) => {
    response += data.toString();
    const lines = response.split("\n");
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const result = JSON.parse(line);
        console.log(result.msg || JSON.stringify(result));
      } catch {
        console.log(line);
      }
    }
    client.end();
  });

  client.on("end", () => {
    process.exit(0);
  });

  client.on("error", (err) => {
    if (err.code === "ENOENT" || err.code === "ECONNREFUSED") {
      if (retries > 0) {
        // App not running — try to start it
        if (retries === 3) {
          console.log("Miu is not running. Starting...");
          startApp();
        }
        setTimeout(() => sendCommand(cmd, retries - 1), 1500);
      } else {
        console.error("Could not connect to Miu. Is the app running?");
        process.exit(1);
      }
    } else {
      console.error("Error:", err.message);
      process.exit(1);
    }
  });
}

function startApp() {
  // Try to find the electron app. In development, run from project dir.
  // In installed package, the .desktop file handles launching.
  const appDir = path.resolve(__dirname);
  const electronPaths = [
    path.join(appDir, "node_modules", ".bin", "electron"),
    "electron",       // global
    "npx",            // via npx
  ];

  let launched = false;
  for (const electronBin of electronPaths) {
    try {
      const args = electronBin === "npx"
        ? ["electron", "--ozone-platform=x11", appDir]
        : ["--ozone-platform=x11", appDir];
      const child = spawn(electronBin, args, {
        detached: true,
        stdio: "ignore",
        env: { ...process.env },
      });
      child.unref();
      launched = true;
      break;
    } catch {
      continue;
    }
  }

  if (!launched) {
    console.error("Could not start Miu. Make sure Electron is installed.");
    process.exit(1);
  }
}

sendCommand(command, 3);
