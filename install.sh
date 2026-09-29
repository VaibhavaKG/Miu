#!/usr/bin/env bash
# install.sh — Install the miu CLI command and optional autostart.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

echo "=== Miu Installer ==="
echo ""

# Symlink CLI + daemon
mkdir -p "$BIN_DIR"
ln -sf "${SCRIPT_DIR}/miu" "${BIN_DIR}/miu"
chmod +x "${SCRIPT_DIR}/miu" "${SCRIPT_DIR}/miu-daemon"
echo "✓ Installed 'miu' to ${BIN_DIR}/miu"

# PATH check
if ! echo "$PATH" | grep -q "${BIN_DIR}"; then
  echo ""
  echo "⚠ ${BIN_DIR} is not in your PATH."
  echo "  Add to ~/.bashrc:  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Optional autostart
echo ""
read -rp "Start Miu on login (hidden, timer-only)? [y/N] " answer
if [[ "${answer,,}" == "y" ]]; then
  AUTOSTART_DIR="${HOME}/.config/autostart"
  mkdir -p "$AUTOSTART_DIR"
  cat > "${AUTOSTART_DIR}/miu.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Miu
Comment=Pixel cat Pomodoro timer
Exec=env GDK_BACKEND=x11 ${SCRIPT_DIR}/miu-daemon
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
  echo "✓ Autostart entry created"
else
  echo "  Skipped."
fi

echo ""
echo "Done! Run 'miu hi' to say hello."
