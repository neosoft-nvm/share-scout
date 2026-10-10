"""Finish a staged ShareScout update after the running app closes."""
import os
import ctypes
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import messagebox


def install_root():
    if os.name == 'nt':
        return Path(os.getenv('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'ResourceMapperApp'
    return Path.home() / '.local/share/ResourceMapper'


def wait_for_process(pid, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if os.name == 'nt':
            kernel = ctypes.windll.kernel32
            kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.WaitForSingleObject.restype = ctypes.c_ulong
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
            if not handle: return
            try:
                if kernel.WaitForSingleObject(handle, 0) == 0: return
            finally:
                kernel.CloseHandle(handle)
            time.sleep(.2)
            continue
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(.2)
    raise RuntimeError('ShareScout did not close in time. Close it and choose Upgrade again.')


def write_linux_launcher(target):
    icon_dir = Path.home() / '.local/share/icons/hicolor/128x128/apps'
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target / 'sharescout.png', icon_dir / 'sharescout.png')
    applications = Path.home() / '.local/share/applications'
    applications.mkdir(parents=True, exist_ok=True)
    executable = str(target / 'Start-Resource-Mapper')
    for char in ('\\', '"', '`', '$'):
        executable = executable.replace(char, '\\' + char)
    executable = executable.replace('%', '%%')
    entry = ('[Desktop Entry]\nType=Application\nName=ShareScout\n'
             'Comment=Find and connect shared folders\nExec="' + executable + '"\n'
             'Icon=sharescout\nTerminal=false\nCategories=Network;FileManager;\n')
    (applications / 'resource-mapper.desktop').write_text(entry, encoding='utf-8')


def apply(pid, stage_path, python_executable):
    stage = Path(stage_path).resolve()
    target = install_root().resolve()
    if stage.parent != target.parent or not stage.name.startswith('sharescout-update-'):
        raise RuntimeError('The staged update location was not recognized.')
    if not (stage / 'app_info.py').is_file() or not (stage / 'resource_mapper.py').is_file():
        raise RuntimeError('The staged update is incomplete. Your current version is unchanged.')
    wait_for_process(pid)

    candidate = stage / 'new-install'
    if target.exists():
        shutil.copytree(target, candidate)
    else:
        candidate.mkdir()
    for source in stage.iterdir():
        if source.is_file():
            shutil.copy2(source, candidate / source.name)
    for name in ('Launch-Linux.sh', 'Start-Resource-Mapper'):
        path = candidate / name
        if path.exists(): path.chmod(0o755)

    backup = target.with_name(target.name + '.previous')
    if backup.exists(): shutil.rmtree(backup)
    moved_old = False
    try:
        if target.exists():
            target.rename(backup); moved_old = True
        candidate.rename(target)
    except Exception:
        if moved_old and not target.exists(): backup.rename(target)
        raise
    try:
        if os.name != 'nt':
            write_linux_launcher(target)
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.Popen([python_executable, str(target / 'resource_mapper.py')], cwd=target,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags, start_new_session=os.name != 'nt')
    except Exception:
        failed = target.with_name(target.name + '.failed-update')
        if failed.exists(): shutil.rmtree(failed)
        if target.exists(): target.rename(failed)
        if moved_old and backup.exists(): backup.rename(target)
        shutil.rmtree(failed, ignore_errors=True)
        raise
    shutil.rmtree(backup, ignore_errors=True)
    shutil.rmtree(stage, ignore_errors=True)


def show_error(message):
    try:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror('ShareScout update', message, parent=root)
        root.destroy()
    except tk.TclError:
        pass


if __name__ == '__main__':
    try:
        if len(sys.argv) != 4: raise RuntimeError('The update could not be started.')
        apply(int(sys.argv[1]), sys.argv[2], sys.argv[3])
    except Exception as exc:
        show_error('ShareScout could not finish the update. Your files were kept.\n\n' + str(exc))
