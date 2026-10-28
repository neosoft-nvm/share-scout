"""Create the per-user native runtime ZIP used by installers and GUI updates."""
import json
from pathlib import Path
import platform
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_info import VERSION

BACKEND = ['desktop_service', 'network', 'linux_mount', 'credentials', 'cloud_setup',
           'permanent_mounts', 'sharing_permissions', 'folder_share', 'sharing_setup', 'updates', 'native_updates', 'single_instance', 'app_info']


def build(binary=None, output=None):
    windows = sys.platform == 'win32'
    name = 'share-scout.exe' if windows else 'share-scout'
    binary = Path(binary) if binary else ROOT / 'src-tauri/target/release' / name
    architecture = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(platform.machine().lower(), platform.machine().lower())
    output = Path(output) if output else ROOT / 'dist' / f'sharescout-desktop-{"windows" if windows else "linux"}-{architecture}.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(binary, name)
        archive.write(ROOT / 'sharescout.png', 'sharescout.png')
        for module in BACKEND:
            archive.write(ROOT / f'{module}.py', f'backend/{module}.py')
        archive.writestr('release.json', json.dumps({'version': VERSION, 'platform': 'windows' if windows else 'linux'}))
    return output


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
