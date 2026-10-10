"""Read the published source version without downloading or executing an update."""
import ast
import base64
import json
import os
import re
import stat
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from app_info import VERSION

REPOSITORY = 'https://github.com/neosoft-nvm/share-scout'
VERSION_URL = 'https://api.github.com/repos/neosoft-nvm/share-scout/contents/app_info.py?ref=main'
SOURCE_ZIP = REPOSITORY + '/archive/refs/heads/main.zip'
MAX_ARCHIVE = 50 * 1024 * 1024
MAX_FILE = 5 * 1024 * 1024
UPDATE_FILES = {'Launch-Linux.sh', 'Launch-Windows.cmd', 'Setup-Windows.ps1',
                'Start-Resource-Mapper', 'sharescout.png', 'sharescout.svg', 'sharescout.ico'}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('The published version format was not recognized.')
    return tuple(int(part) for part in value.split('.'))


def install_root():
    if os.name == 'nt':
        return Path(os.getenv('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'ResourceMapperApp'
    return Path.home() / '.local/share/ResourceMapper'


def source_version(source):
    # Parse a literal constant; never import or execute downloaded Python.
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets):
            value = ast.literal_eval(node.value); version_tuple(value); return value
    raise ValueError('GitHub did not provide a version number.')


def check(installed=VERSION):
    version_tuple(installed)
    request = Request(VERSION_URL, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'ShareScout/' + installed, 'Cache-Control': 'no-cache'})
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read(65537)
        if len(payload) > 65536: raise ValueError('The version response was unexpectedly large.')
        data = json.loads(payload)
        if data.get('encoding') != 'base64': raise ValueError('The version response was not recognized.')
        source = base64.b64decode(data['content']).decode('utf-8')
        latest = source_version(source)
        return {'installed': installed, 'latest': latest, 'newer': version_tuple(latest) > version_tuple(installed)}
    except Exception as exc:
        raise RuntimeError('Could not check GitHub for updates. Check your internet connection and try again.\n\n' + str(exc)) from exc


def stage_update(expected):
    """Download the checked GitHub source ZIP into a safe temporary directory."""
    version_tuple(expected)
    request = Request(SOURCE_ZIP, headers={'User-Agent': 'ShareScout/' + VERSION, 'Accept': 'application/zip'})
    try:
        with urlopen(request, timeout=45) as response:
            archive_data = response.read(MAX_ARCHIVE + 1)
        if len(archive_data) > MAX_ARCHIVE:
            raise ValueError('The update archive is too large.')
        with zipfile.ZipFile(BytesIO(archive_data)) as archive:
            if len(archive.infolist()) > 1000:
                raise ValueError('The update archive has too many files.')
            entries = {}
            uncompressed_size = 0
            for info in archive.infolist():
                parts = info.filename.split('/')
                if len(parts) < 2 or parts[0] != 'share-scout-main':
                    continue
                name = '/'.join(parts[1:])
                if '/' in name or not (name.endswith('.py') or name in UPDATE_FILES):
                    continue
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError('The update archive contains a symbolic link.')
                if info.file_size > MAX_FILE:
                    raise ValueError('An update file is too large.')
                if name in entries:
                    raise ValueError('The update archive contains duplicate file names.')
                uncompressed_size += info.file_size
                if uncompressed_size > MAX_ARCHIVE:
                    raise ValueError('The unpacked update is too large.')
                entries[name] = info
            version_file = entries.get('app_info.py')
            if not version_file:
                raise ValueError('The update archive is missing its version file.')
            latest = source_version(archive.read(version_file))
            if latest != expected:
                raise ValueError(f'The update changed during download (expected {expected}, found {latest}). Check for updates again.')
            required = {'app_info.py', 'resource_mapper.py', 'updates.py', 'apply_update.py'}
            if not required.issubset(entries):
                raise ValueError('The update archive is missing required application files.')
            parent = install_root().parent
            parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix='sharescout-update-', dir=parent))
            try:
                for name, info in entries.items():
                    destination = stage / name
                    destination.write_bytes(archive.read(info))
                    if name in {'Launch-Linux.sh', 'Start-Resource-Mapper'}:
                        destination.chmod(0o755)
                return stage
            except Exception:
                import shutil
                shutil.rmtree(stage, ignore_errors=True)
                raise
    except Exception as exc:
        raise RuntimeError('Could not prepare the ShareScout update. Your installed version was not changed.\n\n' + str(exc)) from exc
