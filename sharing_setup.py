"""Optional Linux Samba server setup; never runs privileged changes on import."""
import configparser
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

CONFIG_PATH = Path('/etc/samba/smb.conf')
SHARE_ROOT = Path('/srv/share-scout')


def tool(name):
    return shutil.which(name) or next((str(path) for folder in ('/usr/sbin', '/sbin') if (path := Path(folder) / name).is_file() and os.access(path, os.X_OK)), None)


def execute(args, check=True, capture=True):
    args = [tool(args[0]) or args[0]] + args[1:]
    result = subprocess.run(args, text=True, capture_output=capture, timeout=60 if capture else None,
                            env={**os.environ, 'LC_ALL': 'C'})
    if check and result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Command failed').strip() if capture else 'The command did not complete. Please try setup again.')
    return result


def visible_shares(text):
    config = configparser.RawConfigParser(strict=False)
    config.read_string(text)
    result = []
    for name in config.sections():
        if name.casefold() in ('global', 'homes', 'printers') or name.endswith('$'): continue
        section = config[name]
        def enabled(key, default=True):
            return section.get(key, 'yes' if default else 'no').casefold() in ('yes', 'true', '1')
        if not enabled('available') or not enabled('browseable', enabled('browsable')) or enabled('printable', False): continue
        if section.get('path', '').strip(): result.append(name)
    return result


def reachable_listener(output):
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4: continue
        address = parts[3].rsplit(':', 1)[0].strip('[]')
        if address in ('*', '0.0.0.0'): return True
        try:
            ip = ipaddress.ip_address(address)
            if ip.version == 4 and not ip.is_loopback: return True
        except ValueError: pass
    return False


def inspect():
    server = bool(tool('smbd'))
    shares = []
    error = None
    if tool('testparm') and CONFIG_PATH.exists():
        try: shares = visible_shares(execute(['testparm', '-s', str(CONFIG_PATH)]).stdout)
        except Exception as exc: error = str(exc)
    # File-manager sharing extensions can define usershares outside smb.conf.
    if server and tool('net'):
        try:
            usershares = execute(['net', 'usershare', 'list', '--long'], check=False)
            if usershares.returncode == 0:
                shares = sorted(set(shares + [name.strip() for name in usershares.stdout.splitlines() if name.strip() and not name.endswith('$')]))
        except Exception: pass
    listener = False
    try: listener = reachable_listener(execute(['ss', '-H', '-4', '-ltn', 'sport = :445']).stdout)
    except Exception as exc: error = error or str(exc)
    return {'installed': server, 'shares': shares, 'listening': listener, 'error': error,
            'ready': server and bool(shares) and listener and not error}


def identity():
    import pwd
    user = pwd.getpwuid(os.getuid())
    if user.pw_uid == 0: raise RuntimeError('Start ShareScout as your normal desktop user, not as root.')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*\$?', user.pw_name):
        raise RuntimeError('This username requires manual Samba configuration.')
    return user


def package_command():
    if tool('dnf'): return ['sudo', 'dnf', 'install', '-y', 'samba', 'policycoreutils-python-utils']
    if tool('apt-get'): return ['sudo', 'apt-get', 'install', '-y', 'samba']
    if tool('pacman'): return ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'samba']
    raise RuntimeError('Automatic sharing setup supports Fedora, Debian/Ubuntu/Zorin and Arch.')


def service_name():
    return 'smb' if tool('dnf') or tool('pacman') else 'smbd'


def primary_network():
    routes = json.loads(execute(['ip', '-j', '-4', 'route', 'show', 'default']).stdout)
    routes = sorted(routes, key=lambda item: item.get('metric', 0))
    if not routes: raise RuntimeError('Connect to your home Wi-Fi or Ethernet network, then run sharing setup again.')
    interface = routes[0]['dev']
    if interface.startswith(('tun', 'tap', 'wg', 'tailscale')):
        raise RuntimeError('Your default connection is a VPN. Disconnect it and run setup on your home Wi-Fi or Ethernet network.')
    addresses = json.loads(execute(['ip', '-j', '-4', 'addr', 'show', 'dev', interface]).stdout)
    for item in addresses:
        for address in item.get('addr_info', []):
            if address.get('family') == 'inet' and address.get('scope') == 'global':
                subnet = ipaddress.IPv4Interface(f"{address['local']}/{address['prefixlen']}").network
                if subnet.prefixlen < 16: raise RuntimeError('This network is too broad for automatic firewall setup. Use a home network or configure sharing manually.')
                return interface, str(subnet)
    raise RuntimeError('No IPv4 address was found on your current connection.')


def firewall_commands(interface, subnet, firewall, zone=None):
    subnet = str(ipaddress.IPv4Network(subnet))
    if firewall == 'firewalld':
        if not zone or not re.fullmatch(r'[\w-]+', zone): raise ValueError('Could not determine your connection’s firewall zone.')
        rule = f'rule family="ipv4" source address="{subnet}" port port="445" protocol="tcp" accept'
        return [['sudo', 'firewall-cmd', '--zone=' + zone, '--add-rich-rule=' + rule],
                ['sudo', 'firewall-cmd', '--permanent', '--zone=' + zone, '--add-rich-rule=' + rule]]
    if firewall == 'ufw': return [['sudo', 'ufw', 'allow', 'from', subnet, 'to', 'any', 'port', '445', 'proto', 'tcp']]
    return []


def configure_firewall(interface, subnet):
    if tool('firewall-cmd') and execute(['firewall-cmd', '--state'], check=False).returncode == 0:
        zone = execute(['firewall-cmd', '--get-zone-of-interface=' + interface], check=False).stdout.strip()
        if not zone or zone == 'no zone': zone = execute(['firewall-cmd', '--get-default-zone']).stdout.strip()
        commands = firewall_commands(interface, subnet, 'firewalld', zone)
    elif tool('ufw') and 'Status: active' in execute(['sudo', 'ufw', 'status']).stdout:
        commands = firewall_commands(interface, subnet, 'ufw')
    else:
        print('No active firewalld/UFW firewall found. Other firewall rules may still require adjustment.')
        return
    for command in commands: execute(command)


def share_section(username, folder):
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*\$?', username): raise ValueError('Invalid account name.')
    return f'\n# Managed by ShareScout: dedicated, password-protected folder\n[ShareScout-{username}]\n    path = {folder}\n    browseable = yes\n    read only = no\n    guest ok = no\n    valid users = {username}\n    create mask = 0600\n    directory mask = 0700\n'


def apply_share(username):
    """Privileged mode: only a real non-root account and a dedicated folder."""
    import pwd
    if os.geteuid() != 0: raise RuntimeError('Administrator permission is required for Samba configuration.')
    user = pwd.getpwnam(username)
    if user.pw_uid == 0: raise ValueError('A normal user account is required.')
    folder = SHARE_ROOT / username
    section = share_section(username, folder)
    if CONFIG_PATH.is_symlink(): raise RuntimeError('Samba configuration is a symbolic link. Configure this custom setup manually; it will not be replaced.')
    original = CONFIG_PATH.read_text() if CONFIG_PATH.exists() else '[global]\n    security = user\n'
    # Validate existing includes/config before adding anything, using Samba itself.
    effective = execute(['testparm', '-s', str(CONFIG_PATH)]).stdout if CONFIG_PATH.exists() else original
    parsed = configparser.RawConfigParser(strict=False); parsed.read_string(effective)
    name = 'ShareScout-' + username
    if any(part.casefold() == name.casefold() for part in parsed.sections()):
        raise RuntimeError('A ShareScout share with this name already exists. Setup will not overwrite it. Check its settings in /etc/samba/smb.conf.')
    SHARE_ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    if SHARE_ROOT.is_symlink() or folder.is_symlink(): raise RuntimeError('The dedicated share path must not be a symbolic link.')
    if folder.exists():
        if not folder.is_dir() or folder.stat().st_uid != user.pw_uid:
            raise RuntimeError('The share folder already exists with different ownership. Setup will not change it.')
    else:
        folder.mkdir(mode=0o700); os.chown(folder, user.pw_uid, user.pw_gid)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix='.sharescout-', dir=CONFIG_PATH.parent)
    temp = Path(filename)
    try:
        with os.fdopen(fd, 'w') as output: output.write(original.rstrip() + '\n' + section)
        if CONFIG_PATH.exists():
            metadata = CONFIG_PATH.stat(); os.chmod(temp, metadata.st_mode & 0o777); os.chown(temp, metadata.st_uid, metadata.st_gid)
        else: os.chmod(temp, 0o644)
        execute(['testparm', '-s', str(temp)])
        backup = CONFIG_PATH.with_name('smb.conf.sharescout-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak')
        if CONFIG_PATH.exists(): shutil.copy2(CONFIG_PATH, backup)
        os.replace(temp, CONFIG_PATH)
        if tool('restorecon'): execute(['restorecon', '-F', str(CONFIG_PATH)])
        print('Samba configuration saved. Backup:', backup)
    finally:
        temp.unlink(missing_ok=True)
    return folder


def label_folder(folder):
    if not tool('getenforce'): return
    if execute(['getenforce']).stdout.strip() == 'Disabled': return
    pattern = re.escape(str(folder)) + '(/.*)?'
    add = execute(['sudo', 'semanage', 'fcontext', '-a', '-t', 'samba_share_t', pattern], check=False)
    if add.returncode:
        if 'already defined' not in ((add.stderr or '') + (add.stdout or '')):
            raise RuntimeError((add.stderr or add.stdout).strip())
        execute(['sudo', 'semanage', 'fcontext', '-m', '-t', 'samba_share_t', pattern])
    execute(['sudo', 'restorecon', '-RF', str(folder)])


def configure(status_file):
    user = identity()
    interface, subnet = primary_network()
    before = inspect()
    if before['error']: raise RuntimeError('Existing sharing settings could not be checked: ' + before['error'])
    print('ShareScout sharing setup\n-----------------------')
    print('Account:', user.pw_name, '\nNetwork:', subnet, 'on', interface)
    print('Administrator approval may be requested. Existing shared folders will be kept.')
    if not before['installed'] or not tool('smbpasswd'):
        if tool('apt-get'): execute(['sudo', 'apt-get', 'update'], capture=False)
        execute(package_command(), capture=False)
    # Check the effective configuration again after installing Samba.
    current = inspect()
    if current['error']: raise RuntimeError('Samba configuration needs attention: ' + current['error'])
    folder = None
    if not current['shares']:
        print('\nChoose a sharing password when prompted. Use it when connecting from your other device.')
        execute(['sudo', 'smbpasswd', '-a', user.pw_name], capture=False)
        execute(['sudo', sys.executable, str(Path(__file__).resolve()), '--apply', user.pw_name], capture=False)
        folder = SHARE_ROOT / user.pw_name
        if tool('getenforce') and not tool('semanage'):
            if tool('dnf'): execute(['sudo', 'dnf', 'install', '-y', 'policycoreutils-python-utils'], capture=False)
            else: raise RuntimeError('SELinux is active but semanage is unavailable. Install SELinux management tools and retry.')
        label_folder(folder)
    else:
        print('Keeping existing shares:', ', '.join(current['shares']))
        managed = SHARE_ROOT / user.pw_name
        if ('ShareScout-' + user.pw_name) in current['shares'] and managed.is_dir():
            folder = managed
            if tool('getenforce') and not tool('semanage') and tool('dnf'):
                execute(['sudo', 'dnf', 'install', '-y', 'policycoreutils-python-utils'], capture=False)
            label_folder(folder)
    configure_firewall(interface, subnet)
    execute(['sudo', 'systemctl', 'enable', '--now', service_name()], capture=False)
    execute(['sudo', 'systemctl', 'restart', service_name()], capture=False)
    after = inspect()
    if not after['ready']: raise RuntimeError('Samba was configured but could not be verified as listening with a visible share. Check the setup messages and run Check sharing again.')
    result = {'ok': True, 'shares': after['shares'], 'folder': str(folder) if folder else None,
              'message': 'Sharing is ready locally. Rescan from your other device to check network access.'}
    if folder:
        link = Path(user.pw_dir) / 'Shared with ShareScout'
        if not link.exists() and not link.is_symlink():
            try: link.symlink_to(folder)
            except OSError: print('The folder shortcut could not be created. Use:', folder)
        print('\nPut files to share in:', link)
    Path(status_file).write_text(json.dumps(result))
    print('\nSetup complete. Rescan from your other device.')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--apply':
        try: apply_share(sys.argv[2])
        except Exception as exc: print(str(exc), file=sys.stderr); sys.exit(1)
    elif len(sys.argv) == 3 and sys.argv[1] == '--configure':
        try:
            configure(sys.argv[2])
        except (Exception, KeyboardInterrupt) as exc:
            Path(sys.argv[2]).write_text(json.dumps({'ok': False, 'error': str(exc)}))
            print('\nSetup could not finish:', exc)
        try: input('\nPress Enter to close setup. ')
        except (EOFError, KeyboardInterrupt): pass
    else:
        print(json.dumps(inspect()))
