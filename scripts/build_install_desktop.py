"""Build and install the native desktop app, stopping on any build failure."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    npm = 'npm.cmd' if sys.platform == 'win32' else 'npm'
    subprocess.run([npm, 'run', 'tauri', '--', 'build', '--no-bundle'], cwd=ROOT, check=True)
    command = [sys.executable, str(ROOT / 'scripts/install_desktop.py')]
    if '--no-launch' in sys.argv[1:]:
        command.append('--no-launch')
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
