"""Store optional SMB credentials in the operating system's credential store."""
import ctypes
import json
import os
import subprocess

_APP = 'ShareScout'


def _windows_target(address):
    return f'{_APP}/SMB/{address}'


def load(address):
    if os.name == 'nt':
        return _windows_load(address)
    try:
        result = subprocess.run(
            ['secret-tool', 'lookup', 'application', _APP, 'server', address],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    try:
        value = json.loads(result.stdout)
        return value if isinstance(value, dict) and all(isinstance(value.get(k), str) for k in ('username', 'password', 'domain')) else None
    except (ValueError, TypeError):
        return None


def save(address, value):
    payload = json.dumps({key: value.get(key, '') for key in ('username', 'password', 'domain')})
    if os.name == 'nt':
        return _windows_save(address, payload)
    try:
        result = subprocess.run(
            ['secret-tool', 'store', '--label=ShareScout network sign-in',
             'application', _APP, 'server', address],
            input=payload, capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError as exc:
        raise RuntimeError('The system password store is unavailable. Install libsecret tools and unlock your desktop keyring.') from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('The system password store did not respond. Unlock your desktop keyring and try again.') from exc
    if result.returncode:
        raise RuntimeError('Could not save this sign-in to your desktop keyring. Unlock it and try again.')


def delete(address):
    if os.name == 'nt':
        _windows_delete(address)
        return
    try:
        subprocess.run(
            ['secret-tool', 'clear', 'application', _APP, 'server', address],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _win_api():
    class FILETIME(ctypes.Structure):
        _fields_ = [('dwLowDateTime', ctypes.c_ulong), ('dwHighDateTime', ctypes.c_ulong)]

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ('Flags', ctypes.c_ulong), ('Type', ctypes.c_ulong), ('TargetName', ctypes.c_wchar_p),
            ('Comment', ctypes.c_wchar_p), ('LastWritten', FILETIME), ('CredentialBlobSize', ctypes.c_ulong),
            ('CredentialBlob', ctypes.POINTER(ctypes.c_byte)), ('Persist', ctypes.c_ulong),
            ('AttributeCount', ctypes.c_ulong), ('Attributes', ctypes.c_void_p),
            ('TargetAlias', ctypes.c_wchar_p), ('UserName', ctypes.c_wchar_p),
        ]

    api = ctypes.windll.advapi32
    api.CredReadW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    api.CredReadW.restype = ctypes.c_bool
    api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), ctypes.c_ulong]
    api.CredWriteW.restype = ctypes.c_bool
    api.CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong]
    api.CredDeleteW.restype = ctypes.c_bool
    api.CredFree.argtypes = [ctypes.c_void_p]
    return api, CREDENTIAL


def _windows_load(address):
    api, CREDENTIAL = _win_api()
    pointer = ctypes.POINTER(CREDENTIAL)()
    if not api.CredReadW(_windows_target(address), 1, 0, ctypes.byref(pointer)):
        return None
    try:
        blob = ctypes.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize)
        value = json.loads(blob.decode('utf-8'))
        return value if isinstance(value, dict) else None
    except (ValueError, UnicodeError):
        return None
    finally:
        api.CredFree(pointer)


def _windows_save(address, payload):
    api, CREDENTIAL = _win_api()
    blob = payload.encode('utf-8')
    data = (ctypes.c_byte * len(blob)).from_buffer_copy(blob)
    credential = CREDENTIAL()
    credential.Type = 1  # CRED_TYPE_GENERIC
    credential.TargetName = _windows_target(address)
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(data, ctypes.POINTER(ctypes.c_byte))
    credential.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = 'ShareScout'
    if not api.CredWriteW(ctypes.byref(credential), 0):
        raise RuntimeError('Windows could not save this sign-in in Credential Manager.')


def _windows_delete(address):
    api, _ = _win_api()
    api.CredDeleteW(_windows_target(address), 1, 0)
