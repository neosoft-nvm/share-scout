#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
missing=0
for tool in smbclient gio ip rclone secret-tool; do command -v "$tool" >/dev/null || missing=1; done
command -v fusermount3 >/dev/null || command -v fusermount >/dev/null || missing=1
python3 -c 'import tkinter; import gi; from gi.repository import Gio' 2>/dev/null || missing=1
if (( missing )); then
  echo 'Setting up ShareScout. Your computer may ask for your administrator password.'
  if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-tk python3-gi smbclient iproute2 rclone fuse3 gvfs-backends libglib2.0-bin libsecret-tools
  elif command -v dnf >/dev/null; then
    sudo dnf install -y python3 python3-tkinter python3-gobject samba-client iproute rclone fuse3 gvfs-smb libsecret
  elif command -v pacman >/dev/null; then
    sudo pacman -S --needed --noconfirm python tk python-gobject smbclient iproute2 rclone fuse3 gvfs-smb libsecret
  else
    echo 'Install Python 3 with Tk and PyGObject, smbclient, iproute2, rclone, FUSE, GVfs SMB support and secret-tool for your distribution.'
    read -r -p 'Press Enter to close.'
    exit 1
  fi
fi
# Install a stable copy and a menu shortcut so future launches need no terminal.
app_dir="$HOME/.local/share/ResourceMapper"
mkdir -p "$app_dir" "$HOME/.local/share/applications"
if [[ "$PWD" != "$app_dir" ]]; then
  cp -- ./*.py ./Launch-Linux.sh ./Start-Resource-Mapper ./sharescout.png ./sharescout.svg "$app_dir/"
  chmod +x "$app_dir/Launch-Linux.sh" "$app_dir/Start-Resource-Mapper"
fi
icon_dir="$HOME/.local/share/icons/hicolor/128x128/apps"
mkdir -p "$icon_dir"
cp -- "$app_dir/sharescout.png" "$icon_dir/sharescout.png"
python3 - "$app_dir" <<'PY'
from pathlib import Path
import sys
location = Path(sys.argv[1])
# Desktop Exec quoting escapes only the characters specified by the desktop entry format.
value = str(location / 'Start-Resource-Mapper')
for char in ['\\', '"', '`', '$']:
    value = value.replace(char, '\\' + char)
value = value.replace('%', '%%')
entry = '[Desktop Entry]\nType=Application\nName=ShareScout\nComment=Find and connect shared folders\nExec="' + value + '"\nIcon=' + str(location / 'sharescout.png') + '\nStartupWMClass=ShareScout\nTerminal=false\nCategories=Network;FileManager;\n'
(Path.home() / '.local/share/applications/resource-mapper.desktop').write_text(entry)
PY
python3 "$app_dir/file_manager.py" "$app_dir"
exec python3 "$app_dir/resource_mapper.py" --check-sharing
