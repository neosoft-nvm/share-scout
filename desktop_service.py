"""Private JSON-lines service for the Tauri desktop. Never exposes a network port."""
from concurrent.futures import ThreadPoolExecutor
import base64
import json
import os
from pathlib import Path
import re
import shlex
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen
import cloud_setup
import credentials as credential_store
import network
import permanent_mounts
from app_info import VERSION

WINDOWS = os.name == 'nt'
STATE = Path(os.environ['SHARESCOUT_STATE_DIR']) if os.getenv('SHARESCOUT_STATE_DIR') else Path(os.getenv('LOCALAPPDATA', str(Path.home() / '.config'))) / 'ResourceMapper'
CONFIG = STATE / 'connections.json'


def normalize_source(value):
    value = value.strip().replace('\\', '/')
    if value.startswith('smb://'):
        value = value[6:]
    value = value.lstrip('/')
    host, separator, path = value.partition('/')
    if not separator or not path or re.search(r'[/@:\s\x00]', host) or any(c in path for c in '\r\n\x00'):
        raise ValueError('Enter a server and shared folder, such as smb://server/photos or \\\\server\\photos.')
    if WINDOWS:
        return '\\\\' + host + '\\' + unquote(path).replace('/', '\\')
    return 'smb://' + host + '/' + quote(unquote(path), safe='/')


def server_address(source):
    return urlsplit(source.replace('\\', '/').replace('//', 'smb://', 1) if source.startswith('\\\\') else source).hostname or ''


def resource_key(item):
    return (item['kind'], item['source'])


def validate_items(items):
    if not isinstance(items, list):
        raise ValueError('Saved connections must be a list.')
    clean = []
    for item in items:
        if not isinstance(item, dict) or item.get('kind') not in ('Network share', 'Google Drive', 'OneDrive'):
            raise ValueError('A saved connection has an unsupported type. Your settings were kept.')
        if not all(isinstance(item.get(k), str) and item[k] for k in ('name', 'source')):
            raise ValueError('A saved connection is incomplete. Your settings were kept.')
        if item.get('target') is not None and not isinstance(item['target'], str):
            raise ValueError('A saved connection has an invalid mount location.')
        clean.append({**{k: item[k] for k in ('name', 'kind', 'source')}, 'target': item.get('target') or '',
                      'auto': bool(item.get('auto')), 'status': 'Disconnected',
                      **({'mountMode': 'system'} if item.get('mountMode') == 'system' and item['kind'] == 'Network share' else {})})
    return clean


def terminal_command(args):
    for terminal, flags in [('ptyxis', ['--new-window', '--']), ('gnome-terminal', ['--']),
                            ('kgx', ['--']), ('konsole', ['-e']), ('xfce4-terminal', ['-x']),
                            ('mate-terminal', ['-e']), ('x-terminal-emulator', ['-e']), ('xterm', ['-e'])]:
        if shutil.which(terminal):
            # MATE expects one shell-quoted command string, rather than an argv tail.
            return [terminal] + flags + ([shlex.join(args)] if terminal == 'mate-terminal' else args)
    raise RuntimeError('Install a desktop terminal to approve sharing setup.')


class DesktopService:
    def __init__(self):
        self.lock = threading.RLock()
        self.sessions = {}
        self.auth = {}
        self.mounts = {}
        self.scans = {}
        self.operation_locks = {}

    def read_items(self):
        try:
            return validate_items(json.loads(CONFIG.read_text()))
        except FileNotFoundError:
            return []

    def save_items(self, items):
        clean = validate_items(items)
        with self.lock:
            # Refuse to overwrite malformed settings even if the UI offers an empty list.
            self.read_items()
            STATE.mkdir(parents=True, exist_ok=True)
            fd, filename = tempfile.mkstemp(prefix='connections-', suffix='.tmp', dir=STATE)
            temp = Path(filename)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as output:
                    json.dump(clean, output, indent=2)
                    output.flush()
                    os.fsync(output.fileno())
                if CONFIG.exists():
                    shutil.copy2(CONFIG, CONFIG.with_suffix('.backup.json'))
                os.replace(temp, CONFIG)
            finally:
                temp.unlink(missing_ok=True)
        return True

    def get_auth(self, address):
        with self.lock:
            cached = self.auth.get(address)
        return cached or credential_store.load(address)

    def signed_in(self, address, auth, remember):
        if not auth or not isinstance(auth.get('username'), str) or not auth['username'].strip():
            raise ValueError('Enter a username.')
        value = {k: str(auth.get(k, '')) for k in ('username', 'password', 'domain')}
        with self.lock:
            self.auth[address] = value
        if remember:
            credential_store.save(address, value)

    def refresh(self):
        with self.lock:
            items = self.read_items()
        connected = network.connected_folders()
        actual = {normalize_source(x['source']): x for x in connected}
        for item in items:
            if item['kind'] == 'Network share' and item.get('mountMode') != 'system':
                found = actual.get(normalize_source(item['source']))
                if found:
                    item.update(status='Connected', target=found['target'])
            elif item['kind'] != 'Network share':
                mount = self.mounts.get(resource_key(item))
                if mount and mount['process'].poll() is None and self.is_mounted(mount['target']):
                    item.update(status='Connected', target=mount['target'])
        sources = {normalize_source(x['source']) for x in items if x['kind'] == 'Network share'}
        items.extend(x for x in connected if normalize_source(x['source']) not in sources)
        managed = permanent_mounts.records()
        for record in managed:
            item = next((x for x in items if x['kind'] == 'Network share' and normalize_source(x['source']) == normalize_source(record['source'])), None)
            if item is None:
                item = {'name': Path(record['target']).name, 'kind': 'Network share', 'source': record['source']}
                items.append(item)
            item.update(target=record['target'], mountMode='system', auto=False,
                        status='Connected' if record['connected'] else 'Disconnected')
        return items

    @staticmethod
    def is_mounted(target):
        return Path(target + '\\').exists() if WINDOWS else os.path.ismount(target)

    def mount(self, item, auth=None, remember=False):
        item = validate_items([item])[0]
        if item['kind'] == 'Network share' and item.get('mountMode') == 'system':
            record = next((x for x in permanent_mounts.records() if normalize_source(x['source']) == normalize_source(item['source'])), None)
            if not record:
                raise RuntimeError('This permanent mount is no longer configured. Use Permanent Mount to set it up again.')
            # Access triggers the system automount; mount timeout bounds offline hosts.
            result = subprocess.run(['timeout', '35', 'stat', '--', record['target']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode or not permanent_mounts.mounted(record['target'], permanent_mounts.defaults(item['source'])['source']):
                raise RuntimeError('The permanent mount is offline. Check that the sharing computer is on and reachable.')
            return {**item, 'target': record['target'], 'auto': False, 'status': 'Connected'}
        if item['kind'] == 'Network share':
            item['source'] = normalize_source(item['source'])
            address = server_address(item['source'])
            if WINDOWS and not item['target']:
                item['target'] = network.free_drive()
            network.mount_share(item['source'], item['target'], auth or self.get_auth(address))
            if auth:
                try:
                    self.signed_in(address, auth, remember)
                except RuntimeError as exc:
                    item['warning'] = 'Connected, but the password could not be saved: ' + str(exc)
        else:
            key = resource_key(item)
            with self.lock:
                existing = self.mounts.get(key)
            if existing and existing['process'].poll() is None and self.is_mounted(existing['target']):
                return {**item, 'target': existing['target'], 'status': 'Connected'}
            if (item['source'], item['kind']) not in cloud_setup.existing_accounts():
                raise ValueError('Select a saved cloud account or sign in again.')
            target = item['target']
            if WINDOWS:
                target = target or network.free_drive()
                if not re.fullmatch(r'[D-Zd-z]:', target) or Path(target + '\\').exists():
                    raise ValueError('Choose an unused drive letter from D: to Z:.')
            else:
                path = Path(target).expanduser().absolute()
                if not target or path in (Path('/'), Path.home()):
                    raise ValueError('Choose a dedicated empty mount folder.')
                path.mkdir(parents=True, exist_ok=True)
                if path.is_symlink() or os.path.ismount(path) or any(path.iterdir()):
                    raise ValueError('The mount folder must be empty and not already mounted.')
                target = str(path)
            STATE.mkdir(parents=True, exist_ok=True)
            log = STATE / ('cloud-' + str(time.time_ns()) + '.log')
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            rc_password = secrets.token_urlsafe(32)
            environment = os.environ.copy()
            environment.update(RCLONE_RC_USER='sharescout', RCLONE_RC_PASS=rc_password, RCLONE_RC_ADDR=f'127.0.0.1:{port}')
            with log.open('w') as output:
                process = subprocess.Popen(['rclone', 'mount', item['source'] + ':', target,
                    '--vfs-cache-mode', 'full', '--vfs-cache-max-size', '2G', '--vfs-write-back', '0s', '--log-level', 'ERROR', '--rc'],
                    env=environment, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                    creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Cloud mount failed. Check Rclone, FUSE or WinFsp in Sharing Diagnostics.')
                    if self.is_mounted(target):
                        item['target'] = target
                        with self.lock:
                            self.mounts[key] = {'process': process, 'target': target, 'rc_port': port, 'rc_password': rc_password}
                        break
                    time.sleep(.2)
                else:
                    raise RuntimeError('Cloud mount timed out. Check your connection and try again.')
            except Exception:
                self.stop_process(process)
                raise
        return {**item, 'status': 'Connected'}

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def uploads_pending(self, mount):
        if mount['process'].poll() is not None:
            return False
        token = base64.b64encode(('sharescout:' + mount['rc_password']).encode()).decode()
        request = Request(f"http://127.0.0.1:{mount['rc_port']}/vfs/stats", data=b'{}',
                          headers={'Authorization': 'Basic ' + token, 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=5) as response:
                stats = json.loads(response.read(65536))
            cache = stats['diskCache']
            return bool(stats['inUse'] or cache['uploadsInProgress'] or cache['uploadsQueued'] or cache['erroredFiles'])
        except Exception as exc:
            raise RuntimeError('Could not verify pending cloud uploads. Keep the drive connected and retry.') from exc

    def unmount(self, item):
        if item.get('mountMode') == 'system':
            raise RuntimeError('Use Permanent Mount → Remove Permanent Mount to stop and remove this system mount.')
        if item['kind'] == 'Network share':
            if WINDOWS:
                network.win_disconnect(item['target'] or normalize_source(item['source']))
            else:
                network.command(['gio', 'mount', '-u', normalize_source(item['source'])])
        else:
            key = resource_key(item)
            with self.lock:
                mount = self.mounts.get(key)
            if not mount:
                raise RuntimeError('This cloud drive is not mounted by this ShareScout session.')
            if self.uploads_pending(mount):
                raise RuntimeError('Cloud files are open or uploads are pending. Close files and let uploads finish, then retry.')
            if not WINDOWS and self.is_mounted(mount['target']):
                network.command([shutil.which('fusermount3') or 'fusermount', '-u', mount['target']])
            self.stop_process(mount['process'])
            if self.is_mounted(mount['target']):
                raise RuntimeError('The cloud drive is still mounted. Close files on it and retry.')
            with self.lock:
                self.mounts.pop(key, None)
        return True

    def scan(self, scan_id):
        networks = network.local_networks()
        with self.lock:
            stop = self.scans.setdefault(scan_id, threading.Event())
        addresses = []
        try:
            network.scan(networks, stop, lambda address, done, total: addresses.append(address) if address else None)
            return {'devices': [{'address': address} for address in sorted(set(addresses))],
                    'networks': networks, 'cancelled': stop.is_set()}
        finally:
            with self.lock:
                self.scans.pop(scan_id, None)

    def share(self, folder, name, read_only):
        if WINDOWS:
            network.win_share_folder()
            return {'ok': False, 'wizard': True, 'message': 'Complete the Windows sharing wizard to create the share.'}
        import folder_share
        user = folder_share.setup.identity()
        folder_share.validate_folder(folder, user)
        folder_share.validate_name(name)
        return self.setup_terminal('folder_share.py', ['--configure-folder'], [folder, name, 'read' if read_only else 'write'])

    def setup_terminal(self, script, prefix, suffix):
        with tempfile.TemporaryDirectory(prefix='sharescout-setup-') as directory:
            status = Path(directory) / 'result.json'
            subprocess.Popen(terminal_command([sys.executable, str(Path(__file__).with_name(script))] + prefix + [str(status)] + suffix),
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                if status.exists():
                    try:
                        result = json.loads(status.read_text())
                    except ValueError:
                        time.sleep(.1)
                        continue
                    if not result.get('ok'):
                        raise RuntimeError(result.get('error') or 'Sharing setup did not finish.')
                    return result
                time.sleep(.3)
            raise RuntimeError('Sharing setup timed out. Close its terminal before retrying.')

    def diagnostics(self):
        checks = []
        required = [('rclone', 'Rclone Cloud Engine')]
        if not WINDOWS:
            required += [('smbclient', 'Samba Client'), ('gio', 'GIO File System Mounts'), ('ip', 'Network Tools')]
        for tool, label in required:
            ready = bool(shutil.which(tool))
            checks.append({'name': label, 'ok': ready, 'status': 'Installed' if ready else 'Missing',
                           'desc': 'Available' if ready else 'Run the setup launcher to install it.'})
        if WINDOWS:
            ready = any((Path(os.getenv(key, 'C:/')) / 'WinFsp').exists() for key in ('ProgramFiles', 'ProgramFiles(x86)'))
        else:
            ready = Path('/dev/fuse').exists() and bool(shutil.which('fusermount3') or shutil.which('fusermount'))
        checks.append({'name': 'WinFsp' if WINDOWS else 'FUSE Filesystem Support', 'ok': ready,
                       'status': 'Available' if ready else 'Missing', 'desc': 'Required for cloud mounts.'})
        try:
            nets = network.local_networks()
            checks.append({'name': 'Local Network', 'ok': bool(nets), 'status': 'Active' if nets else 'Unavailable',
                           'desc': ', '.join(x['network'] for x in nets) or 'No connected IPv4 network.'})
        except Exception:
            checks.append({'name': 'Local Network', 'ok': False, 'status': 'Unavailable', 'desc': 'Could not read network interfaces.'})
        if not WINDOWS:
            import sharing_setup
            sharing = sharing_setup.inspect()
            checks.append({'name': 'Local Folder Sharing', 'ok': sharing['ready'],
                           'status': 'Ready' if sharing['ready'] else 'Needs setup',
                           'desc': sharing.get('error') or ', '.join(sharing['shares']) or 'No configured shares.'})
        return {'checks': checks, 'windows': WINDOWS, 'version': VERSION}

    def call(self, method, args):
        if method == 'load':
            return self.refresh()
        if method == 'save':
            return self.save_items(args['items'])
        if method in ('mount', 'unmount'):
            key = resource_key(args['item'])
            with self.lock:
                operation_lock = self.operation_locks.setdefault(key, threading.Lock())
            with operation_lock:
                return self.mount(args['item'], args.get('credentials'), args.get('remember', False)) if method == 'mount' else self.unmount(args['item'])
        if method == 'open':
            item = args['item']
            path = item.get('target') or normalize_source(item['source'])
            if not path.startswith(('smb://', '\\\\')):
                path = str(Path(path).expanduser()) + ('\\' if WINDOWS and re.fullmatch('[A-Za-z]:', path) else '')
            if WINDOWS:
                os.startfile(path)
            else:
                network.command(['gio', 'open', path])
            return True
        if method == 'scan':
            return self.scan(args['scanId'])
        if method == 'stop_scan':
            with self.lock:
                self.scans.setdefault(args['scanId'], threading.Event()).set()
            return True
        if method == 'shares':
            address = network.validate_ip(args['address'])
            auth = args.get('credentials') or self.get_auth(address)
            shares = network.list_shares(address, auth)
            if args.get('credentials'):
                self.signed_in(address, auth, args.get('remember', False))
            return shares
        if method == 'cloud_accounts':
            return [{'remote': remote, 'provider': provider} for remote, provider in cloud_setup.existing_accounts()]
        if method == 'cloud_start':
            session = cloud_setup.CloudSession(args['provider'])
            with self.lock:
                self.sessions[session.remote] = session
            return {'session': session.remote, 'remote': session.remote}
        if method == 'cloud_step':
            with self.lock:
                session = self.sessions[args['session']]
            result = session.step(args.get('state'), args.get('answer'))
            # Never forward tokens/password questions as provider errors or logs.
            if result.get('Error'):
                result['Error'] = 'That choice was not accepted. Try again.'
            return result
        if method == 'cloud_cancel':
            with self.lock:
                session = self.sessions.pop(args['session'], None)
            if session:
                session.cancel()
                # execute() owns termination; wait for it before deleting its unique remote.
                deadline = time.monotonic() + 10
                while session.process is not None and time.monotonic() < deadline:
                    time.sleep(.1)
                session.cleanup(force=True)
            return True
        if method == 'cloud_finish':
            with self.lock:
                session = self.sessions[args['session']]
                if not session.complete:
                    raise ValueError('Finish cloud sign-in first.')
                self.sessions.pop(args['session'])
            return True
        if method == 'permanent_defaults':
            info = permanent_mounts.defaults(args['source'])
            if info.get('supported'):
                info['existing'] = next((x for x in permanent_mounts.records() if normalize_source(x['source']) == normalize_source(args['source'])), None)
            return info
        if method == 'permanent_preview':
            if not permanent_mounts.supported():
                raise RuntimeError('Permanent service mounts require Linux with systemd.')
            return permanent_mounts.preview(args['source'], args['target'], args['account'], args.get('readOnly', True))
        if method == 'permanent_apply':
            source = normalize_source(args['source'])
            auth = args.get('credentials') or self.get_auth(server_address(source))
            if not auth:
                raise PermissionError('Enter the sharing account username and password, or sign in to this device first.')
            result = permanent_mounts.invoke({'operation': 'create', 'source': source, 'target': args['target'],
                                             'account': args['account'], 'readOnly': args.get('readOnly', True), 'credentials': auth})
            return {**result, 'resources': self.refresh()}
        if method == 'permanent_remove':
            source = normalize_source(args['source'])
            result = permanent_mounts.invoke({'operation': 'remove', 'source': source})
            items = self.read_items()
            for item in items:
                if item.get('mountMode') == 'system' and normalize_source(item['source']) == source:
                    item.pop('mountMode', None)
                    item.update(target='', auto=False)
            self.save_items(items)
            return {**result, 'resources': self.refresh()}
        if method == 'defaults':
            return {'windows': WINDOWS, 'mountRoot': str(Path.home() / 'ShareScout'),
                    'drive': network.free_drive() if WINDOWS else '', 'version': VERSION}
        if method == 'pick_folder':
            if WINDOWS:
                command = ['powershell', '-NoProfile', '-Command',
                           "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.FolderBrowserDialog; if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath }"]
            else:
                command = ['zenity', '--file-selection', '--directory', '--title=Select folder to share']
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            if result.returncode == 1:
                return None
            if result.returncode:
                raise RuntimeError('The folder picker could not open. You can enter the folder path instead.')
            return result.stdout.strip() or None
        if method == 'share':
            return self.share(args['folderPath'], args['shareName'], args['readOnly'])
        if method == 'diagnostics':
            return self.diagnostics()
        if method == 'network_info':
            return network.local_network_info()
        if method == 'repair':
            if WINDOWS:
                network.win_share_folder()
                return {'message': 'Complete the Windows sharing wizard, then check again.'}
            return self.setup_terminal('sharing_setup.py', ['--configure'], [])
        if method == 'startup_update':
            try:
                preference = json.loads((STATE / 'update-check.json').read_text())
                if not preference.get('automatic', True): return None
            except (OSError, ValueError, AttributeError):
                pass
            try:
                result = self.call('check_updates', {})
                return result if result['newer'] and result['canInstall'] else None
            except Exception:
                return None
        if method == 'update_preference':
            STATE.mkdir(parents=True, exist_ok=True)
            with self.lock:
                fd, filename = tempfile.mkstemp(prefix='update-check-', dir=STATE)
                temp = Path(filename)
                try:
                    with os.fdopen(fd, 'w') as output:
                        json.dump({'automatic': bool(args['automatic'])}, output)
                    os.replace(temp, STATE / 'update-check.json')
                finally:
                    temp.unlink(missing_ok=True)
            return True
        if method == 'check_updates':
            import native_updates
            result = native_updates.check()
            return {k: v for k, v in result.items() if k != 'asset'}
        if method == 'prepare_update':
            if self.mounts:
                raise RuntimeError('Disconnect cloud drives before upgrading.')
            import native_updates
            return str(native_updates.stage(args['version']))
        if method == 'install_update':
            self.call('shutdown', {})
            import native_updates
            stage = Path(args['stage']).resolve()
            root = native_updates.install_root().resolve()
            if stage.parent != root.parent or not stage.name.startswith('sharescout-native-update-') or not (stage / 'candidate/release.json').is_file():
                raise ValueError('The staged update was not recognized.')
            subprocess.Popen([sys.executable, str(Path(__file__).with_name('native_updates.py')), str(stage), str(os.getppid())],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0, start_new_session=not WINDOWS)
            return True
        if method == 'shutdown':
            if self.mounts:
                raise RuntimeError('Disconnect cloud drives and allow pending uploads to finish before closing.')
            self.cleanup()
            return True
        raise ValueError('Unknown desktop operation.')

    def cleanup(self):
        for stop in list(self.scans.values()):
            stop.set()
        for session in list(self.sessions.values()):
            session.cancel()
        for mount in list(self.mounts.values()):
            try:
                self.stop_process(mount['process'])
            except Exception:
                pass
        for session in list(self.sessions.values()):
            try:
                deadline = time.monotonic() + 10
                while session.process is not None and time.monotonic() < deadline:
                    time.sleep(.1)
                session.cleanup(force=True)
            except Exception:
                pass


def serve():
    from single_instance import SingleInstance
    service = DesktopService()
    writer = threading.Lock()
    instance = SingleInstance(STATE)
    if not instance.acquire():
        instance.activate_existing()
        print(json.dumps({'event': 'already_running'}), flush=True)
        return
    def activation_events():
        import queue
        while not instance.stop.is_set():
            try:
                instance.events.get(timeout=.2)
            except queue.Empty:
                continue
            with writer:
                print(json.dumps({'event': 'activate'}), flush=True)
    threading.Thread(target=activation_events, daemon=True).start()
    def respond(request):
        try:
            response = {'id': request['id'], 'result': service.call(request['method'], request.get('args') or {})}
        except Exception as exc:
            response = {'id': request.get('id'), 'error': {'message': str(exc), 'auth': isinstance(exc, PermissionError) and exc.errno is None}}
        with writer:
            print(json.dumps(response), flush=True)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for line in sys.stdin:
                request = json.loads(line)
                pool.submit(respond, request)
            service.cleanup()
    finally:
        service.cleanup()
        instance.close()


if __name__ == '__main__':
    serve()
