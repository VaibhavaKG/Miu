#!/usr/bin/env bash
# ==============================================================================
# Miu 2.0 — Quick One-Line Installer
# ==============================================================================

set -e

MIU_DIR="${HOME}/.local/share/miu-app"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"

echo "✦ Installing Miu Desktop Companion..."

# 1. Detect Package Manager and advise dependencies if missing
if command -v dnf &>/dev/null; then
    PKG_HINT="sudo dnf install -y python3-gobject gtk3 cairo libappindicator-gtk3 libwnck3"
elif command -v apt-get &>/dev/null; then
    PKG_HINT="sudo apt update && sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 gir1.2-wnck-3.0"
elif command -v pacman &>/dev/null; then
    PKG_HINT="sudo pacman -S --needed python-gobject gtk3 cairo libappindicator-gtk3 libwnck3"
else
    PKG_HINT="Ensure python3, GTK 3, PyGObject, and Cairo are installed."
fi

# 2. Check if running from clone or need to clone
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

if [ -f "${SOURCE_DIR}/bin/miu" ]; then
    # Running from inside the cloned repository
    INSTALL_SRC="${SOURCE_DIR}"
else
    echo "Cloning repository to ${MIU_DIR}..."
    rm -rf "${MIU_DIR}"
    git clone https://github.com/VaibhavaKG/Miu.git "${MIU_DIR}"
    INSTALL_SRC="${MIU_DIR}"
fi

# 3. Create symlinks in ~/.local/bin
mkdir -p "${BIN_DIR}"
chmod +x "${INSTALL_SRC}/bin/miu"
ln -sf "${INSTALL_SRC}/bin/miu" "${BIN_DIR}/miu"

# Symlink 'hi' wrapper
cat << 'HI_EOF' > "${BIN_DIR}/hi"
#!/usr/bin/env bash
if [[ "$1" == "miu" ]]; then
    exec miu "${@:2}"
elif [[ "$1" == "--help" || "$1" == "-h" || -z "$1" ]]; then
    exec miu --help
else
    echo "Usage: hi miu [COMMAND]"
    echo "Try 'hi miu --help' for details."
    exit 1
fi
HI_EOF
chmod +x "${BIN_DIR}/hi"

# 4. Create desktop application launcher entry
mkdir -p "${APP_DIR}"
cat << DESKTOP_EOF > "${APP_DIR}/miu.desktop"
[Desktop Entry]
Name=Miu
GenericName=Desktop Pet & Companion
Comment=A tiny, futuristic desktop companion and focus partner
Exec=${BIN_DIR}/miu
Icon=${INSTALL_SRC}/icons/miu.svg
Terminal=false
Type=Application
Categories=Utility;Amusement;
Keywords=cat;pet;oneko;focus;companion;
DESKTOP_EOF

chmod +x "${APP_DIR}/miu.desktop"

# 5. Check PATH warning
case ":$PATH:" in
    *":${BIN_DIR}:"*) ;;
    *) echo -e "\n⚠️  Note: ${BIN_DIR} is not currently in your PATH."
       echo "Add this to your ~/.bashrc or ~/.zshrc:"
       echo 'export PATH="${HOME}/.local/bin:${PATH}"'
       ;;
esac

echo ""
echo "✦ Miu installed successfully!"
echo "----------------------------------------------------"
echo "To ensure system dependencies are satisfied, run:"
echo "  ${PKG_HINT}"
echo ""
echo "To run Miu:"
echo "  miu             # Launch desktop companion"
echo "  miu --home      # Open Miu Home observatory console"
echo "  hi miu --focus  # Start a focus session"
echo "----------------------------------------------------"
