from pathlib import Path
import io
import tarfile
import subprocess
import hashlib
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from app_info import VERSION
source = root
build = root / 'build/deb'
build.mkdir(parents=True, exist_ok=True)
files = {}
for path in sorted(source.glob('*.py')):
    files['usr/share/resource-mapper/' + path.name] = (path.read_bytes(), 0o644)
files['usr/share/icons/hicolor/128x128/apps/sharescout.png'] = ((source / 'sharescout.png').read_bytes(), 0o644)
files['usr/share/icons/hicolor/scalable/apps/sharescout.svg'] = ((source / 'sharescout.svg').read_bytes(), 0o644)
files['usr/share/resource-mapper/sharescout.png'] = ((source / 'sharescout.png').read_bytes(), 0o644)
files['usr/bin/resource-mapper'] = (b'#!/bin/sh\nexec /usr/bin/python3 /usr/share/resource-mapper/resource_mapper.py "$@"\n', 0o755)
files['usr/share/applications/resource-mapper.desktop'] = (b'[Desktop Entry]\nType=Application\nName=ShareScout\nComment=Find computers and connect shared folders\nExec=resource-mapper\nIcon=sharescout\nTerminal=false\nCategories=Network;FileManager;\n', 0o644)
for document in ('README.md', 'ROADMAP.md'):
    files['usr/share/doc/resource-mapper/' + document] = (source.joinpath(document).read_bytes(), 0o644)

def archive(path, entries):
    with tarfile.open(path, 'w:gz', format=tarfile.USTAR_FORMAT) as tar:
        dirs = set()
        for name in entries:
            parent = Path(name).parent
            while str(parent) != '.':
                dirs.add(str(parent)); parent = parent.parent
        for name in sorted(dirs):
            info = tarfile.TarInfo('./' + name); info.type = tarfile.DIRTYPE; info.mode = 0o755
            info.uid = info.gid = 0; info.uname = info.gname = 'root'; tar.addfile(info)
        for name, (data, mode) in entries.items():
            info = tarfile.TarInfo('./' + name); info.size = len(data); info.mode = mode
            info.uid = info.gid = 0; info.uname = info.gname = 'root'
            tar.addfile(info, io.BytesIO(data))

control = f'''Package: resource-mapper
Version: {VERSION}
Section: net
Priority: optional
Architecture: all
Maintainer: ShareScout <resource-mapper@localhost>
Installed-Size: {(sum(len(data) for data, mode in files.values()) + 1023) // 1024}
Depends: python3 (>= 3.8), python3-tk, python3-gi, smbclient, iproute2, gvfs-backends, libglib2.0-bin, libsecret-tools, rclone, fuse3
Description: Find computers and connect shared folders
 Automatically discover local IPv4 SMB file servers and browse their shares.
 Select a shared folder to save, connect and open it. Includes rclone cloud mounts.
'''
md5 = ''.join(hashlib.md5(data).hexdigest() + '  ' + name + '\n' for name, (data, _) in files.items())
archive(build / 'control.tar.gz', {'control': (control.encode(), 0o644), 'md5sums': (md5.encode(), 0o644)})
archive(build / 'data.tar.gz', files)
(build / 'debian-binary').write_bytes(b'2.0\n')
output = root / f'dist/resource-mapper_{VERSION}_all.deb'
output.parent.mkdir(parents=True, exist_ok=True)
if output.exists(): output.unlink()
subprocess.run(['ar', 'rcD', str(output), 'debian-binary', 'control.tar.gz', 'data.tar.gz'], cwd=build, check=True)
# Independently inspect the package members, control metadata, payload and modes.
names = subprocess.check_output(['ar', 't', str(output)], text=True).splitlines()
assert names == ['debian-binary', 'control.tar.gz', 'data.tar.gz']
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['ar', 'p', str(output), 'data.tar.gz'])), mode='r:gz') as tar:
    assert tar.getmember('./usr/bin/resource-mapper').mode == 0o755
    for name, (data, _) in files.items(): assert tar.extractfile('./' + name).read() == data
    desktop = build / 'resource-mapper.desktop'
    desktop.write_bytes(tar.extractfile('./usr/share/applications/resource-mapper.desktop').read())
subprocess.run(['desktop-file-validate', str(desktop)], check=True)
print('Debian package payload and desktop entry verified:', output.name)
