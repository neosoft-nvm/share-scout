"""Install a locally built, trusted ShareScout native runtime for the current user."""
from pathlib import Path
import shutil
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import native_updates
from app_info import VERSION
from package_desktop import build


def install(binary=None, launch=True):
    archive = build(binary)
    root = native_updates.install_root()
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='sharescout-native-update-', dir=root.parent))
    try:
        native_updates.extract_verified(archive, stage / 'candidate', VERSION)
        native_updates.apply(stage, launch=launch)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return root


if __name__ == '__main__':
    args = [arg for arg in sys.argv[1:] if arg != '--no-launch']
    print('Installed ShareScout desktop:', install(args[0] if args else None, launch='--no-launch' not in sys.argv))
