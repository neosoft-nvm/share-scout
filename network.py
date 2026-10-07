"""Local IPv4 discovery and share browsing. No hostname knowledge required."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from urllib.parse import quote

WINDOWS = os.name == 'nt'


def command(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0, **kwargs)
    if result.returncode:
        error = '\n'.join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
        if any(code in error for code in ['NT_STATUS_ACCESS_DENIED', 'NT_STATUS_LOGON_FAILURE']):
            raise PermissionError('This computer needs a username and password.')
        raise RuntimeError(error or 'The computer did not answer.')
    return result.stdout


def scan_ranges(interfaces):
    """Bound large connected networks to the device's /24, with a visible label."""
    result = []
    seen = set()
    for address, prefix in interfaces:
        interface = ipaddress.IPv4Interface(f'{address}/{prefix}')
        if interface.ip.is_loopback or interface.ip.is_unspecified: continue
        actual = interface.network
        network = actual if actual.num_addresses <= 4096 else ipaddress.IPv4Network(f'{address}/24', strict=False)
        if str(network) in seen: continue
        seen.add(str(network))
        result.append({'network': str(network), 'local': address, 'limited': network != actual})
    return result


def local_networks():
    if WINDOWS:
        output = command(['powershell', '-NoProfile', '-Command',
            'Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.AddressState -eq "Preferred"} | Select-Object IPAddress,PrefixLength | ConvertTo-Json -Compress'])
        data = json.loads(output or '[]')
        if isinstance(data, dict): data = [data]
        return scan_ranges([(item['IPAddress'], item['PrefixLength']) for item in data])
    output = command(['ip', '-j', '-4', 'addr', 'show', 'up'])
    data = json.loads(output)
    return scan_ranges([(addr['local'], addr['prefixlen']) for item in data for addr in item.get('addr_info', []) if addr.get('family') == 'inet'])


def validate_ip(value):
    ip = ipaddress.IPv4Address(value.strip())
    if ip.is_unspecified or ip.is_multicast or ip == ipaddress.IPv4Address('255.255.255.255'):
        raise ValueError('Enter a computer’s IPv4 address, such as 192.168.1.20.')
    return str(ip)


def has_smb(address):
    try:
        with socket.create_connection((address, 445), timeout=.65): return True
    except OSError: return False


def scan(networks, stop, update):
    addresses = sorted({str(ip) for item in networks for ip in ipaddress.IPv4Network(item['network']).hosts()}, key=ipaddress.IPv4Address)
    if len(addresses) > 8192:
        raise ValueError('Too many connected networks. Use an IP address instead.')
    with ThreadPoolExecutor(max_workers=48) as pool:
        pending = {pool.submit(has_smb, address): address for address in addresses}
        done = 0
        for future in as_completed(pending):
            if stop.is_set():
                for task in pending: task.cancel()
                break
            done += 1
            update(pending[future] if future.result() else None, done, len(addresses))


def parse_shares(output):
    shares = []
    for line in output.splitlines():
        parts = line.split('|', 2)
        if len(parts) >= 2 and parts[0] == 'Disk' and not parts[1].endswith('$'):
            shares.append({'name': parts[1], 'comment': parts[2] if len(parts) > 2 else ''})
    return shares


def share_source(address, share, windows=None):
    if windows is None: windows = WINDOWS
    validate_ip(address)
    if not share or any(char in share for char in '\\/\r\n\x00'):
        raise ValueError('The server returned an invalid shared folder name.')
    if windows: return '\\\\' + address + '\\' + share
    return 'smb://' + address + '/' + quote(share, safe='')


def free_drive(used=()):
    for letter in 'RSTUVWXYZDEFGHIJKLMNOPQ':
        target = letter + ':'
        if target not in used and not Path(target + '\\').exists(): return target
    raise RuntimeError('No free drive letter is available. Disconnect an unused drive first.')


def win_connect(remote, target=None, credentials=None):
    from ctypes import wintypes as w
    class RESOURCE(ctypes.Structure):
        _fields_ = [('scope', w.DWORD), ('type', w.DWORD), ('display', w.DWORD), ('usage', w.DWORD),
                    ('local', w.LPWSTR), ('remote', w.LPWSTR), ('comment', w.LPWSTR), ('provider', w.LPWSTR)]
    api = ctypes.WinDLL('mpr')
    api.WNetAddConnection2W.argtypes = [ctypes.POINTER(RESOURCE), w.LPCWSTR, w.LPCWSTR, w.DWORD]
    api.WNetAddConnection2W.restype = w.DWORD
    if target:
        api.WNetGetConnectionW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.POINTER(w.DWORD)]
        api.WNetGetConnectionW.restype = w.DWORD
        buffer = ctypes.create_unicode_buffer(32768); size = w.DWORD(32768)
        existing = api.WNetGetConnectionW(target, buffer, ctypes.byref(size))
        if existing == 0:
            if buffer.value.casefold() == remote.casefold(): return
            raise RuntimeError('This drive letter is already connected to another folder.')
    resource = RESOURCE(0, 1, 0, 0, target, remote, None, None)
    credentials = credentials or {}
    username = credentials.get('username') or None
    if username and credentials.get('domain'): username = credentials['domain'] + '\\' + username
    result = api.WNetAddConnection2W(ctypes.byref(resource), credentials.get('password'), username, 0)
    if result in (5, 86, 1326): raise PermissionError('This computer needs a username and password.')
    if result == 1219: raise RuntimeError('Windows is already signed into this computer with a different account. Disconnect that computer’s existing Windows connections, then retry.')
    if result: raise OSError(result, ctypes.FormatError(result))


def win_disconnect(target):
    from ctypes import wintypes as w
    api = ctypes.WinDLL('mpr')
    api.WNetCancelConnection2W.argtypes = [w.LPCWSTR, w.DWORD, w.BOOL]
    api.WNetCancelConnection2W.restype = w.DWORD
    code = api.WNetCancelConnection2W(target, 0, False)
    if code not in (0, 2250): raise OSError(code, ctypes.FormatError(code))


def win_shares(address, credentials=None):
    from ctypes import wintypes as w
    if credentials: win_connect('\\\\' + address + '\\IPC$', credentials=credentials)
    class SHARE(ctypes.Structure):
        _fields_ = [('name', w.LPWSTR), ('type', w.DWORD), ('remark', w.LPWSTR)]
    api = ctypes.WinDLL('Netapi32')
    api.NetShareEnum.argtypes = [w.LPWSTR, w.DWORD, ctypes.POINTER(ctypes.c_void_p), w.DWORD,
                               ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD)]
    api.NetShareEnum.restype = w.DWORD
    api.NetApiBufferFree.argtypes = [ctypes.c_void_p]
    api.NetApiBufferFree.restype = w.DWORD
    resume = w.DWORD(0)
    shares = []
    while True:
        buf = ctypes.c_void_p(); count = w.DWORD(); total = w.DWORD()
        code = api.NetShareEnum('\\\\' + address, 1, ctypes.byref(buf), 0xFFFFFFFF, ctypes.byref(count), ctypes.byref(total), ctypes.byref(resume))
        try:
            if code in (5, 86, 1326): raise PermissionError('This computer needs a username and password.')
            if code not in (0, 234): raise OSError(code, ctypes.FormatError(code))
            records = ctypes.cast(buf, ctypes.POINTER(SHARE))
            for i in range(count.value):
                record = records[i]
                if record.type & 0xFFFF == 0 and not record.name.endswith('$'):
                    shares.append({'name': record.name, 'comment': record.remark or ''})
        finally:
            if buf: api.NetApiBufferFree(buf)
        if code != 234: return shares


def list_shares(address, credentials=None):
    address = validate_ip(address)
    if WINDOWS: return win_shares(address, credentials)
    if not shutil.which('smbclient'): raise RuntimeError('Network browsing needs smbclient. Run ShareScout’s Launch-Linux.sh to finish setup.')
    args = ['smbclient', '-g', '-L', address, '-I', address, '-t', '10']
    env = os.environ.copy()
    for key in ('PASSWD', 'PASSWD_FD', 'PASSWD_FILE'): env.pop(key, None)
    if credentials:
        args += ['-U', credentials['username']]
        if credentials.get('domain'): args += ['-W', credentials['domain']]
        env['PASSWD'] = credentials.get('password', '')
    else: args += ['-N']
    return sorted(parse_shares(command(args, env=env)), key=lambda item: item['name'].casefold())


def mount_share(source, target, credentials=None):
    if WINDOWS: return win_connect(source, target, credentials)
    output = command([sys.executable, str(Path(__file__).with_name('linux_mount.py')), source],
                     input=json.dumps(credentials or {}))
    response = json.loads(output)
    if not response.get('ok'):
        if response.get('auth'): raise PermissionError('Sign in to open this shared folder.')
        raise RuntimeError(response.get('error', 'Could not connect.'))
