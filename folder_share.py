"""Create a protected SMB share for a chosen folder, with a reviewed GUI flow."""
import configparser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
import sharing_setup as setup


def validate_folder(value, user, allow_home=False):
    folder = Path(value).expanduser().absolute()
    if any(char in str(folder) for char in '\n\r%'):
        raise ValueError('Folder names containing line breaks or % cannot be shared automatically.')
    if folder.resolve(strict=True) != folder:
        raise ValueError('Choose the original folder rather than a symbolic link.')
    home = Path(user.pw_dir).resolve()
    allowed = [home, setup.SHARE_ROOT.resolve(), Path('/media'), Path('/mnt'), Path('/run/media')]
    if not (allow_home and folder == home) and not any(folder != parent and parent in folder.parents for parent in allowed):
        raise ValueError('Choose a folder inside your home, /srv/share-scout, or a mounted drive. Sharing an entire home or system folder is not supported.')
    if home in folder.parents and any(part.startswith('.') for part in folder.relative_to(home).parts):
        raise ValueError('Choose a regular folder, such as Documents or Pictures, rather than a hidden settings folder.')
    if not folder.is_dir() or folder.stat().st_uid != user.pw_uid:
        raise ValueError('Choose a local folder owned by your account.')
    return folder


def validate_name(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _-]{0,63}', name):
        raise ValueError('Use a name up to 64 characters with letters, numbers, spaces, - or _. Start with a letter or number.')
    if name.casefold() in ('global', 'homes', 'printers', 'print', 'ipc', 'admin'):
        raise ValueError('Choose another name; this name is reserved.')
    return name


def suggested_name(folder):
    name = re.sub(r'[^A-Za-z0-9 _-]', '-', Path(folder).name).strip(' -_')[:64]
    return name if name and name[0].isalnum() else 'Shared folder'


def custom_section(user, folder, name, writable=False):
    validate_name(name)
    # Unix permissions still apply; do not change ownership or chmod the folder.
    return (f'\n# Managed by ShareScout: chosen folder\n[{name}]\n'
            f'    path = {folder}\n    browseable = yes\n'
            f'    read only = {"no" if writable else "yes"}\n'
            f'    guest ok = no\n    valid users = {user.pw_name}\n'
            '    follow symlinks = no\n    wide links = no\n'
            '    create mask = 0600\n    directory mask = 0700\n')


def apply_custom(username, value, name, writable=False):
    """Privileged helper revalidates the supplied folder and account."""
    import pwd
    if os.geteuid() != 0: raise RuntimeError('Administrator permission is required.')
    user = pwd.getpwnam(username)
    if user.pw_uid == 0 or os.environ.get('SUDO_USER') != username:
        raise ValueError('The share must belong to the desktop account requesting setup.')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*\$?', username):
        raise ValueError('This account name requires manual configuration.')
    folder = validate_folder(value, user)
    section = custom_section(user, folder, name, writable)
    config = setup.CONFIG_PATH
    if config.is_symlink(): raise RuntimeError('A symbolic-link Samba configuration must be configured manually.')
    original = config.read_text() if config.exists() else '[global]\n    security = user\n'
    effective = setup.execute(['testparm', '-s', str(config)]).stdout if config.exists() else original
    parsed = configparser.RawConfigParser(strict=False); parsed.read_string(effective)
    if any(existing.casefold() == name.casefold() for existing in parsed.sections()):
        raise ValueError('That share name already exists. Choose another name; existing shares are kept.')
    # Samba disables usershares by default. Only query them when enabled; a
    # disabled usershare facility must not prevent ordinary smb.conf shares.
    if int(parsed.get('global', 'usershare max shares', fallback='0')) > 0:
        usershares = setup.execute(['net', 'usershare', 'list', '--long'], check=False)
        if usershares.returncode or any(line.strip().casefold() == name.casefold() for line in usershares.stdout.splitlines()):
            raise ValueError('Could not confirm that the name is unused by file-manager shares. Choose another name or check Samba settings.')
    config.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix='.sharescout-', dir=config.parent)
    temp = Path(filename)
    try:
        with os.fdopen(fd, 'w') as output: output.write(original.rstrip() + '\n' + section)
        if config.exists():
            stat = config.stat(); os.chmod(temp, stat.st_mode & 0o777); os.chown(temp, stat.st_uid, stat.st_gid)
        else: os.chmod(temp, 0o644)
        setup.execute(['testparm', '-s', str(temp)])
        # Recheck immediately before committing the configuration.
        validate_folder(value, user)
        if config.exists():
            backup = config.with_name('smb.conf.sharescout-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak')
            shutil.copy2(config, backup); print('Configuration backup:', backup)
        os.replace(temp, config)
        if setup.tool('restorecon'): setup.execute(['restorecon', '-F', str(config)])
    finally: temp.unlink(missing_ok=True)
    return folder


def prepare_selinux(folder, user):
    if not setup.tool('getenforce') or setup.execute(['getenforce']).stdout.strip() == 'Disabled': return
    if Path(user.pw_dir).resolve() in folder.parents:
        enabled = setup.execute(['getsebool', 'samba_enable_home_dirs']).stdout.strip().endswith('--> on')
        if not enabled:
            print('\nSELinux requires permission for Samba to access folders inside home directories.')
            print('This enables the system-wide samba_enable_home_dirs policy. Only configured shares are published.')
            if input('Allow this policy change? Type yes to continue: ').strip().casefold() != 'yes':
                raise RuntimeError('No share was created. Choose a folder under /srv/share-scout instead, or approve the home-folder policy.')
            setup.execute(['sudo', 'setsebool', '-P', 'samba_enable_home_dirs', 'on'], capture=False)
    else:
        if not setup.tool('semanage'):
            if setup.tool('dnf'): setup.execute(['sudo', 'dnf', 'install', '-y', 'policycoreutils-python-utils'], capture=False)
            else: raise RuntimeError('SELinux management tools are needed to label this folder.')
        print('SELinux will label the chosen folder and its contents for Samba access.')
        setup.label_folder(folder)


def configure_folder(status_file, value, name, writable=False):
    user = setup.identity(); folder = validate_folder(value, user); validate_name(name)
    interface, subnet = setup.primary_network()
    before = setup.inspect()
    if before['error']: raise RuntimeError(before['error'])
    if any(part.casefold() == name.casefold() for part in before['shares']):
        raise ValueError('That share name already exists. Choose another name.')
    print('ShareScout — share a folder\nFolder:', folder, '\nShare name:', name)
    print('Access:', 'Read and write' if writable else 'Read only', '\nAccount:', user.pw_name)
    print('Network:', subnet, '\nAdministrator approval may be requested.')
    if not before['installed'] or not setup.tool('smbpasswd'):
        if setup.tool('apt-get'): setup.execute(['sudo', 'apt-get', 'update'], capture=False)
        setup.execute(setup.package_command(), capture=False)
    prepare_selinux(folder, user)
    # Preserve an existing Samba password. Prompt only when this account is missing.
    accounts = setup.execute(['sudo', 'pdbedit', '-L'], check=False)
    if accounts.returncode: raise RuntimeError('Could not check Samba accounts. No share was created.')
    if not any(line.split(':', 1)[0] == user.pw_name for line in accounts.stdout.splitlines()):
        print('Choose a sharing password for your account. Use it from your other devices.')
        setup.execute(['sudo', 'smbpasswd', '-a', user.pw_name], capture=False)
    setup.execute(['sudo', sys.executable, str(Path(__file__).resolve()), '--apply-custom', user.pw_name,
                   str(folder), name, 'write' if writable else 'read'], capture=False)
    setup.configure_firewall(interface, subnet)
    setup.execute(['sudo', 'systemctl', 'enable', '--now', setup.service_name()], capture=False)
    setup.execute(['sudo', 'systemctl', 'restart', setup.service_name()], capture=False)
    after = setup.inspect()
    if not after['ready'] or name not in after['shares']:
        raise RuntimeError('The share was saved but could not be verified. Use Check sharing to repair it.')
    addresses = json.loads(setup.execute(['ip', '-j', '-4', 'addr', 'show', 'dev', interface]).stdout)
    ips = [addr['local'] for item in addresses for addr in item.get('addr_info', []) if addr.get('family') == 'inet' and addr.get('scope') == 'global']
    result = {'ok': True, 'folder': str(folder), 'name': name, 'account': user.pw_name,
              'address': ips[0] if ips else '', 'writable': writable}
    Path(status_file).write_text(json.dumps(result))
    print('\nSharing is ready locally. Scan from another device to connect.')


def selected_folder(args, environ=None):
    """Scripts may pass arguments or newline-separated selected local paths."""
    environ = os.environ if environ is None else environ
    selected = [] if list(args) == ['--from-file-manager'] else list(args)
    if not selected:
        for key in ('NAUTILUS_SCRIPT_SELECTED_FILE_PATHS', 'CAJA_SCRIPT_SELECTED_FILE_PATHS'):
            if environ.get(key): selected = environ[key].rstrip('\n').split('\n'); break
    if len(selected) > 1: raise ValueError('Select one folder at a time.')
    if not selected: return None
    if not Path(selected[0]).is_absolute() or '://' in selected[0]:
        raise ValueError('Choose a local folder on this computer.')
    return selected[0]


def main():
    if len(sys.argv) == 6 and sys.argv[1] == '--apply-custom':
        if sys.argv[5] not in ('read', 'write'): raise ValueError('Invalid access mode.')
        apply_custom(*sys.argv[2:5], writable=sys.argv[5] == 'write')
        return
    if len(sys.argv) == 6 and sys.argv[1] == '--configure-folder':
        status, folder, name, mode = sys.argv[2:]
        import signal
        def cancelled(signum, frame): raise KeyboardInterrupt('Setup terminal closed.')
        signal.signal(signal.SIGHUP, cancelled)
        signal.signal(signal.SIGTERM, cancelled)
        try:
            if mode not in ('read', 'write'): raise ValueError('Invalid access mode.')
            configure_folder(status, folder, name, mode == 'write')
        except (Exception, KeyboardInterrupt) as exc:
            Path(status).write_text(json.dumps({'ok': False, 'error': str(exc) or 'Setup cancelled.'}))
            print('\nSetup could not finish:', exc)
        try: input('\nPress Enter to close setup. ')
        except (EOFError, KeyboardInterrupt): pass
        return
    import tkinter as tk
    from tkinter import messagebox
    import ui
    from folder_share_ui import FolderShare
    ui.enable_dpi_awareness(); root = tk.Tk(); root.withdraw()
    try: folder = selected_folder(sys.argv[1:])
    except ValueError as exc:
        messagebox.showerror('Share a folder', str(exc), parent=root); root.destroy(); return
    state = Path.home() / '.config/ResourceMapper'; state.mkdir(parents=True, exist_ok=True)
    FolderShare(root, state, folder=folder, done=root.destroy)
    root.mainloop()


if __name__ == '__main__':
    try: main()
    except Exception as exc: print(str(exc), file=sys.stderr); sys.exit(1)
