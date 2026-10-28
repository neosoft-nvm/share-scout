"""Linux system SMB mounts, with an explicit preview and a bounded privileged helper.

Passwords travel over stdin and are stored only in root-owned 0600 files after
confirmation. Managed systemd units never modify existing fstab entries or mounts.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import unquote, urlsplit

MOUNT_ROOT = Path('/mnt/sharescout')
STATE_ROOT = Path('/etc/sharescout-mounts')
UNIT_ROOT = Path('/etc/systemd/system')
MARKER = '# Managed by ShareScout permanent mounts\n'


def supported():
    return sys.platform == 'linux' and Path('/run/systemd/system').is_dir()


def source_parts(source):
    if not isinstance(source, str):
        raise ValueError('Choose an SMB shared folder.')
    parsed = urlsplit(source.replace('\\', '/').replace('//', 'smb://', 1) if source.startswith('\\\\') else source)
    host = parsed.hostname or ''
    share = unquote(parsed.path).strip('/')
    if (parsed.scheme != 'smb' or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,252}', host)
            or not share or share != share.strip() or len(share) > 128 or '/' in share or share in ('.', '..')
            or any(ord(c) < 32 or c in '%\\' for c in share)):
        raise ValueError('Use the shared folder itself, such as smb://computer/Movies, without a subfolder.')
    return host.lower(), share


def validate_target(target):
    target = Path(target)
    if target.parent != MOUNT_ROOT or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', target.name):
        raise ValueError('Choose a folder directly inside /mnt/sharescout using letters, numbers, underscores or hyphens.')
    return target


def identifier(source, uid):
    host, share = source_parts(source)
    return hashlib.sha256(f'{uid}:{host}/{share}'.encode()).hexdigest()[:20]


def defaults(source):
    if not supported():
        return {'supported': False, 'reason': 'Permanent service mounts are available on Linux with systemd. Windows desktop drive mapping remains available through Connect.'}
    import pwd
    host, share = source_parts(source)
    current = pwd.getpwuid(os.getuid())
    accounts = [{'name': current.pw_name, 'label': 'My account (' + current.pw_name + ')'}]
    try:
        plex = pwd.getpwnam('plex')
        if plex.pw_uid != current.pw_uid:
            accounts.append({'name': 'plex', 'label': 'Plex media server'})
    except KeyError:
        pass
    slug = re.sub(r'[^A-Za-z0-9_-]', '-', share).strip('-_')[:38] or 'Share'
    return {'supported': True, 'target': str(MOUNT_ROOT / (slug + '-' + identifier(source, os.getuid())[:8])),
            'accounts': accounts, 'account': accounts[-1]['name'], 'toolsReady': bool(shutil.which('mount.cifs')),
            'approvalAvailable': bool(shutil.which('pkexec')), 'source': f'//{host}/{share}'}


def preview(source, target, account, read_only=True):
    import pwd
    host, share = source_parts(source)
    target = validate_target(target)
    try:
        user = pwd.getpwnam(account)
    except KeyError as exc:
        raise ValueError('The selected local account does not exist.') from exc
    if user.pw_uid == 0:
        raise ValueError('Choose your account or a service account such as plex.')
    if not isinstance(read_only, bool):
        raise ValueError('Choose read-only or read/write access.')
    return {'source': f'//{host}/{share}', 'target': str(target), 'account': user.pw_name,
            'readOnly': read_only, 'id': identifier(source, os.getuid())}


def command(args, check=True, timeout=60):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('The mount operation failed. Check the network, sharing password and administrator approval.')
    return result


def tool(name):
    for directory in ('/usr/sbin', '/usr/bin', '/sbin', '/bin'):
        path = Path(directory) / name
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    raise RuntimeError('Required system tool is missing: ' + name)


def unit_names(target):
    escaped = command([tool('systemd-escape'), '--path', str(target)]).stdout.strip()
    return escaped + '.mount', escaped + '.automount'


def mounted(target, source):
    result = command([tool('findmnt'), '--json', '--list', '-t', 'cifs', '-o', 'TARGET,SOURCE'], check=False)
    if result.returncode:
        return False
    records = json.loads(result.stdout).get('filesystems', [])
    return any(x.get('target') == str(target) and x.get('source') == source for x in records)


def trusted_file(path):
    info = path.lstat()
    return stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022


def records():
    if not supported() or not STATE_ROOT.exists():
        return []
    result = []
    for path in STATE_ROOT.glob('*.json'):
        try:
            if not trusted_file(path):
                continue
            data = json.loads(path.read_text())
            if data.get('owner') != os.getuid() or data.get('id') != path.stem:
                continue
            host, share = source_parts(data['source'])
            target = validate_target(data['target'])
            result.append({**data, 'connected': mounted(target, f'//{host}/{share}')})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return result


def invoke(payload):
    if not supported():
        raise RuntimeError('Permanent mounts require Linux with systemd.')
    if not shutil.which('pkexec'):
        raise RuntimeError('Administrator approval is unavailable. Install polkit and open ShareScout in your desktop session.')
    approval = [shutil.which('pkexec'), '--disable-internal-agent', '/usr/bin/python3', '-I', str(Path(__file__).resolve()), '--admin']
    # A remotely updated app may still belong to an ended SSH session. Ask from
    # the desktop user manager so polkit can reach the existing graphical agent.
    runner = shutil.which('systemd-run')
    if runner:
        approval = [runner, '--user', '--quiet', '--wait', '--pipe', '--collect', '--service-type=exec'] + approval
    result = subprocess.run(approval, input=json.dumps(payload), capture_output=True, text=True, timeout=600)
    if result.returncode == 126:
        raise RuntimeError('Administrator approval was cancelled. Nothing was changed.')
    if result.returncode == 127:
        detail = getattr(result, 'stderr', '')
        if 'No authentication agent found' in detail:
            raise RuntimeError('No desktop administrator-approval agent was found. Open ShareScout from the Applications menu in your signed-in desktop session and retry. Nothing was changed.')
        raise RuntimeError('Administrator approval is unavailable. Check that your desktop session and polkit are running. Nothing was changed.')
    try:
        response = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError('The mount helper could not finish. No success was reported.') from exc
    if result.returncode or not response.get('ok'):
        raise RuntimeError(response.get('error') or 'The mount helper could not finish.')
    return response


def secure_directory(path):
    """Reject symlinks and directories another account could replace."""
    if not path.exists() and not path.is_symlink():
        path.mkdir(mode=0o755)
        path.chmod(0o755)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise RuntimeError('The managed mount directory must be owned by root and not writable by other accounts.')


def create_file(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def unit_value(value):
    # What= is a single string, not a shell/ExecStart word list. Literal quotes
    # would become part of the SMB source. Specifiers must still be escaped.
    return value.replace('%', '%%')


def ensure_cifs():
    try:
        tool('mount.cifs')
        return
    except RuntimeError:
        pass
    if Path('/usr/bin/apt-get').exists():
        command(['/usr/bin/apt-get', 'install', '-y', 'cifs-utils'], timeout=180)
    elif Path('/usr/bin/dnf').exists():
        command(['/usr/bin/dnf', 'install', '-y', 'cifs-utils'], timeout=180)
    else:
        raise RuntimeError('Install cifs-utils with your system package manager, then try again.')
    tool('mount.cifs')


def apply(payload, owner):
    import pwd
    operation = payload.get('operation')
    if operation not in ('create', 'remove'):
        raise ValueError('Unknown permanent mount operation.')
    source = payload.get('source', '')
    host, share = source_parts(source)
    mount_id = identifier(source, owner)
    metadata = STATE_ROOT / (mount_id + '.json')
    secure_directory(STATE_ROOT)
    if operation == 'remove':
        if not trusted_file(metadata):
            raise RuntimeError('The mount record is not trusted.')
        data = json.loads(metadata.read_text())
        if data.get('owner') != owner or data.get('id') != mount_id or data.get('source') != source:
            raise RuntimeError('This mount belongs to a different account or share.')
        target = validate_target(data['target'])
        mount_unit, auto_unit = unit_names(target)
        for name in (mount_unit, auto_unit):
            p = UNIT_ROOT / name
            if not trusted_file(p) or not p.read_text().startswith(MARKER):
                raise RuntimeError('An existing system mount is not managed by ShareScout.')
        # Stop both together; never force-unmount a folder being used by Plex.
        result = command([tool('systemctl'), 'stop', auto_unit, mount_unit], check=False)
        if result.returncode or mounted(target, f'//{host}/{share}'):
            command([tool('systemctl'), 'start', auto_unit], check=False)
            raise RuntimeError('The folder is busy. Stop playback or close files, then retry. The mount setup was kept.')
        command([tool('systemctl'), 'disable', auto_unit])
        for name in (mount_unit, auto_unit):
            (UNIT_ROOT / name).unlink()
        (STATE_ROOT / (mount_id + '.credentials')).unlink()
        metadata.unlink()
        command([tool('systemctl'), 'daemon-reload'])
        try:
            target.rmdir()
        except OSError:
            pass
        return {'ok': True, 'removed': True, 'target': str(target)}

    account = payload.get('account', '')
    plan = preview(source, payload.get('target', ''), account, payload.get('readOnly', True))
    reader = pwd.getpwnam(account)
    caller = pwd.getpwuid(owner)
    auth = payload.get('credentials')
    if not isinstance(auth, dict):
        raise ValueError('Enter the sharing account username and password.')
    values = {key: auth.get(key, '') for key in ('username', 'password', 'domain')}
    if not values['username'] or any(not isinstance(v, str) or len(v) > 4096 or any(c in v for c in '\r\n\x00') for v in values.values()):
        raise ValueError('Enter a valid sharing username, password and optional domain.')
    target = validate_target(plan['target'])
    secure_directory(MOUNT_ROOT)
    if target.exists() or target.is_symlink():
        raise RuntimeError('That mount folder already exists. Choose a new folder; existing mounts and files are kept.')
    if metadata.exists() or metadata.is_symlink():
        raise RuntimeError('This share already has a permanent mount. Use Manage Mount to remove it first.')
    mount_unit, auto_unit = unit_names(target)
    for name in (mount_unit, auto_unit):
        if any((directory / name).exists() or (directory / name).is_symlink() for directory in (UNIT_ROOT, Path('/run/systemd/generator'), Path('/run/systemd/system'), Path('/usr/lib/systemd/system'), Path('/lib/systemd/system'))):
            raise RuntimeError('An existing system mount uses that folder. Choose another folder.')
    ensure_cifs()
    credentials = STATE_ROOT / (mount_id + '.credentials')
    options = ','.join(['ro' if plan['readOnly'] else 'rw', 'nosuid', 'nodev', 'noexec',
                        'credentials=' + str(credentials), f'uid={reader.pw_uid}', f'gid={caller.pw_gid}',
                        'forceuid', 'forcegid', 'nounix', 'file_mode=0440' if plan['readOnly'] else 'file_mode=0660',
                        'dir_mode=0550' if plan['readOnly'] else 'dir_mode=0770'])
    mount_text = (MARKER + '[Unit]\nDescription=ShareScout permanent network folder\nWants=network-online.target\nAfter=network-online.target\n'
                  + '[Mount]\nWhat=' + unit_value(f'//{host}/{share}') + '\nWhere=' + str(target)
                  + '\nType=cifs\nOptions=' + options + '\nTimeoutSec=25\n')
    auto_text = (MARKER + '[Unit]\nDescription=ShareScout network folder on demand\n'
                + '[Automount]\nWhere=' + str(target) + '\nDirectoryMode=0755\n[Install]\nWantedBy=multi-user.target\n')
    created = []
    enable_attempted = False
    target.mkdir(mode=0o755)
    target.chmod(0o755)
    try:
        for path, text, mode in [(credentials, ''.join(k + '=' + v + '\n' for k, v in values.items()), 0o600),
                                 (UNIT_ROOT / mount_unit, mount_text, 0o644), (UNIT_ROOT / auto_unit, auto_text, 0o644)]:
            create_file(path, text, mode)
            created.append(path)
        data = {**plan, 'id': mount_id, 'owner': owner, 'source': source}
        create_file(metadata, json.dumps(data), 0o644)
        created.append(metadata)
        command([tool('systemctl'), 'daemon-reload'])
        enable_attempted = True
        command([tool('systemctl'), 'enable', '--now', auto_unit])
        command([tool('systemctl'), 'start', mount_unit], timeout=40)
        if not mounted(target, f'//{host}/{share}'):
            raise RuntimeError('The network folder was not mounted. Setup will be rolled back.')
        # Verify directory access as the selected local account.
        probe = subprocess.run([tool('runuser'), '-u', reader.pw_name, '--', tool('ls'), '-U', '--', str(target)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=35)
        if probe.returncode:
            raise RuntimeError('The selected account cannot read the folder. Setup will be rolled back.')
        return {'ok': True, **data}
    except Exception as exc:
        stopped = command([tool('systemctl'), 'stop', auto_unit, mount_unit], check=False) if enable_attempted else None
        if enable_attempted and (stopped.returncode or mounted(target, f'//{host}/{share}')):
            raise RuntimeError('Setup did not finish and the mount could not be stopped. Its managed configuration was kept; use Remove Permanent Mount after closing files.') from exc
        if enable_attempted:
            command([tool('systemctl'), 'disable', auto_unit], check=False)
        for path in reversed(created):
            path.unlink(missing_ok=True)
        command([tool('systemctl'), 'daemon-reload'], check=False)
        target.rmdir()
        raise


def main():
    try:
        if sys.argv[1:] != ['--admin'] or os.geteuid() != 0:
            raise RuntimeError('This helper requires desktop administrator approval.')
        owner = int(os.environ.get('PKEXEC_UID', '0'))
        if owner <= 0:
            raise RuntimeError('The requesting desktop account could not be identified.')
        payload = json.loads(sys.stdin.read(65537))
        # Serialize setup/removal so concurrent windows cannot race system changes.
        import fcntl
        secure_directory(STATE_ROOT)
        fd = os.open(STATE_ROOT / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            response = apply(payload, owner)
        print(json.dumps(response))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
