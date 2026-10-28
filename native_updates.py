"""Verified native desktop release staging and per-user installation."""
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile
from app_info import VERSION

RELEASE_URL = 'https://api.github.com/repos/neosoft-nvm/share-scout/releases/latest'
WINDOWS = os.name == 'nt'
MAX_ARCHIVE = 250 * 1024 * 1024
MAX_UNPACKED = 600 * 1024 * 1024
BACKEND_FILES = ['desktop_service', 'network', 'linux_mount', 'credentials', 'cloud_setup',
                 'permanent_mounts', 'folder_share', 'sharing_setup', 'updates', 'native_updates', 'single_instance', 'app_info']


def install_root():
    if WINDOWS:
        return Path(os.getenv('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'ShareScoutDesktop'
    return Path.home() / '.local/share/ShareScoutDesktop'


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('The release version was not recognized.')
    return tuple(map(int, value.split('.')))


def request(url):
    return Request(url, headers={'User-Agent': 'ShareScout/' + VERSION, 'Accept': 'application/vnd.github+json'})


def asset_name():
    machine = platform.machine().lower()
    architecture = {'amd64': 'x86_64', 'x86_64': 'x86_64', 'aarch64': 'aarch64', 'arm64': 'aarch64'}.get(machine)
    if not architecture:
        raise RuntimeError('Automatic updates are unavailable for this processor.')
    return f'sharescout-desktop-{"windows" if WINDOWS else "linux"}-{architecture}.zip'


def check():
    try:
        with urlopen(request(RELEASE_URL), timeout=10) as response:
            data = json.loads(response.read(2 * 1024 * 1024))
        latest = data['tag_name'].removeprefix('v')
        version(latest)
        if data.get('draft') or data.get('prerelease'):
            raise ValueError('No stable release is available.')
        asset = next((x for x in data.get('assets', []) if x['name'] == asset_name()), None)
        digest = asset.get('digest', '') if asset else ''
        compatible = bool(asset and re.fullmatch(r'sha256:[a-fA-F0-9]{64}', digest))
        return {'installed': VERSION, 'latest': latest, 'newer': version(latest) > version(VERSION),
                'canInstall': compatible, 'asset': asset if compatible else None}
    except Exception as exc:
        raise RuntimeError('Could not check published desktop releases. Check your internet connection and try again.') from exc


def extract_verified(archive_path, destination, expected_version):
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if len(entries) > 200:
            raise ValueError('The update contains too many files.')
        total = 0
        seen = set()
        names = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename:
                raise ValueError('The update contains an unsafe file path.')
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('The update contains a symbolic link.')
            names.add(entry.filename)
            folded = str(path).casefold()
            if folded in seen:
                raise ValueError('The update contains duplicate paths.')
            seen.add(folded)
            total += entry.file_size
            if total > MAX_UNPACKED:
                raise ValueError('The unpacked update is too large.')
        manifest = json.loads(archive.read('release.json'))
        if manifest.get('version') != expected_version or manifest.get('platform') != ('windows' if WINDOWS else 'linux'):
            raise ValueError('The update does not match the selected release or platform.')
        required = {'release.json', 'sharescout.png', 'share-scout.exe' if WINDOWS else 'share-scout'}
        required.update('backend/' + name + '.py' for name in BACKEND_FILES)
        if not required.issubset(names):
            raise ValueError('The update is incomplete.')
        archive.extractall(destination)
    if not WINDOWS:
        (destination / 'share-scout').chmod(0o755)


def stage(expected):
    result = check()
    if result['latest'] != expected or not result['newer'] or not result['canInstall']:
        raise RuntimeError('The release changed or its verified desktop package is unavailable. Check again.')
    asset = result['asset']
    url = asset['browser_download_url']
    if not url.startswith('https://github.com/neosoft-nvm/share-scout/releases/download/'):
        raise ValueError('The update download location was not recognized.')
    root = install_root()
    root.parent.mkdir(parents=True, exist_ok=True)
    stage_dir = Path(tempfile.mkdtemp(prefix='sharescout-native-update-', dir=root.parent))
    archive_path = stage_dir / 'download.zip'
    try:
        digest = hashlib.sha256()
        total = 0
        with urlopen(request(url), timeout=60) as response, archive_path.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ARCHIVE:
                    raise ValueError('The update download is too large.')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != asset['digest'].split(':', 1)[1].lower():
            raise ValueError('The update verification failed. The installed app was kept.')
        candidate = stage_dir / 'candidate'
        candidate.mkdir()
        extract_verified(archive_path, candidate, expected)
        archive_path.unlink()
        return stage_dir
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def launcher(target):
    executable = target / ('share-scout.exe' if WINDOWS else 'share-scout')
    if WINDOWS:
        def literal(value): return "'" + str(value).replace("'", "''") + "'"
        script = ("$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Programs'), 'ShareScout.lnk')); "
                  f"$s.TargetPath = {literal(executable)}; $s.WorkingDirectory = {literal(target)}; $s.IconLocation = {literal(executable)}; $s.Save()")
        subprocess.run(['powershell', '-NoProfile', '-Command', script], check=True, capture_output=True)
    else:
        value = str(executable)
        for char in ('\\', '"', '`', '$'):
            value = value.replace(char, '\\' + char)
        value = value.replace('%', '%%')
        applications = Path.home() / '.local/share/applications'
        applications.mkdir(parents=True, exist_ok=True)
        (applications / 'resource-mapper.desktop').write_text(
            f'[Desktop Entry]\nType=Application\nName=ShareScout\nExec="{value}"\nIcon={target / "sharescout.png"}\nTerminal=false\nStartupWMClass=ShareScout\nCategories=Network;FileManager;\n')


def process_alive(pid):
    if WINDOWS:
        api = ctypes.windll.kernel32
        api.OpenProcess.restype = ctypes.c_void_p
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        handle = api.OpenProcess(0x00100000, False, pid)
        if not handle:
            return False
        try: return api.WaitForSingleObject(handle, 0) != 0
        finally: api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def apply(stage_path, pid=0, launch=True):
    root = install_root().resolve()
    stage_dir = Path(stage_path).resolve()
    if stage_dir.parent != root.parent or not stage_dir.name.startswith('sharescout-native-update-'):
        raise ValueError('The staged update location was not recognized.')
    candidate = stage_dir / 'candidate'
    if not (candidate / 'release.json').is_file():
        raise ValueError('The staged update is incomplete.')
    deadline = time.monotonic() + 60
    while pid and process_alive(pid):
        if time.monotonic() > deadline:
            raise RuntimeError('ShareScout did not close in time. The installed version was kept.')
        time.sleep(.2)
    backup = root.with_name(root.name + '.previous')
    if backup.exists():
        shutil.rmtree(backup)
    moved = False
    shortcut = None if WINDOWS else Path.home() / '.local/share/applications/resource-mapper.desktop'
    old_shortcut = shortcut.read_bytes() if shortcut and shortcut.exists() else None
    try:
        if root.exists():
            root.rename(backup)
            moved = True
        candidate.rename(root)
        launcher(root)
        flags = subprocess.CREATE_NO_WINDOW if WINDOWS else 0
        if launch:
            process = subprocess.Popen([str(root / ('share-scout.exe' if WINDOWS else 'share-scout'))], cwd=root,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=flags, start_new_session=not WINDOWS)
            time.sleep(2)
            if process.poll() is not None:
                raise RuntimeError('The updated application did not start. The previous installation was restored.')
    except Exception:
        if root.exists(): root.rename(stage_dir / 'failed-install')
        if moved: backup.rename(root)
        if shortcut:
            if old_shortcut is not None: shortcut.write_bytes(old_shortcut)
            else: shortcut.unlink(missing_ok=True)
        elif moved:
            launcher(root)
        raise
    shutil.rmtree(stage_dir, ignore_errors=True)


if __name__ == '__main__':
    try:
        apply(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    except Exception as exc:
        # Keep a user-readable error if the old process has already closed.
        state = Path(os.getenv('LOCALAPPDATA', str(Path.home() / '.config'))) / 'ResourceMapper'
        state.mkdir(parents=True, exist_ok=True)
        (state / 'native-update-error.txt').write_text(str(exc))
        if not WINDOWS and shutil.which('zenity'):
            subprocess.run(['zenity', '--error', '--text=ShareScout update failed: ' + str(exc)])
        sys.exit(1)
