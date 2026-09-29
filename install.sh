#!/usr/bin/env bash
# install.sh — Install Miu CLI and optional autostart entry.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
AUTOSTART_DIR="${HOME}/.config/autostart"

echo "=== Miu Installer ==="
echo ""

# 1. Symlink CLI
mkdir -p "$BIN_DIR"
ln -sf "${SCRIPT_DIR}/cli.js" "${BIN_DIR}/miu"
chmod +x "${SCRIPT_DIR}/cli.js"
echo "✓ Installed 'miu' command to ${BIN_DIR}/miu"

# Check if ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "${BIN_DIR}"; then
  echo ""
  echo "⚠ ${BIN_DIR} is not in your PATH."
  echo "  Add this to your ~/.bashrc or ~/.zshrc:"
  echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# 2. Optional autostart
echo ""
read -rp "Add Miu to autostart (launches hidden on login)? [y/N] " answer
if [[ "${answer,,}" == "y" ]]; then
  mkdir -p "$AUTOSTART_DIR"
  cat > "${AUTOSTART_DIR}/miu.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Miu
Comment=Pixel cat Pomodoro timer
Exec=${BIN_DIR}/miu hi
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
EOF
  echo "✓ Autostart entry created at ${AUTOSTART_DIR}/miu.desktop"
else
  echo "  Skipped autostart."
fi

echo ""
echo "Done! Run 'miu hi' to say hello to Miu."
