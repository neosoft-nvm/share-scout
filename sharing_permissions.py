"""Detect and explicitly repair SELinux access for configured Samba FUSE shares."""
import configparser
import json
import os
from pathlib import Path
import subprocess
import sys

FLAG = 'samba_share_fusefs'


def tool(name):
    return next((str(Path(folder)/name) for folder in ('/usr/sbin','/usr/bin','/sbin','/bin')
                 if (Path(folder)/name).is_file() and os.access(Path(folder)/name,os.X_OK)),None)


def run(args, check=True):
    result=subprocess.run([tool(args[0]) or args[0],*args[1:]],capture_output=True,text=True,timeout=120)
    if check and result.returncode:
        raise RuntimeError('The sharing-permission check could not finish. Check the system sharing tools and retry.')
    return result


def is_fuse(folder):
    result=run(['findmnt','-n','-T',str(folder),'-o','FSTYPE'],check=False)
    types=result.stdout.strip().splitlines()
    return result.returncode==0 and any(value=='fuseblk' or value=='fuse' or value.startswith('fuse.') for value in types)


def configured_paths():
    if not tool('testparm'):
        return []
    result=run(['testparm','-s','--suppress-prompt'],check=False)
    if result.returncode:
        return []
    config=configparser.RawConfigParser(strict=False)
    config.read_string(result.stdout)
    paths=[]
    for section in config.sections():
        if section.casefold() in ('global','homes','printers','print$'):
            continue
        value=config.get(section,'path',fallback='').strip()
        available=config.get(section,'available',fallback='yes').casefold() not in ('no','false','0')
        if available and value.startswith('/') and '%' not in value and value not in paths:
            paths.append(value)
    return paths


def status(folder=None):
    if sys.platform!='linux' or not tool('getenforce') or not tool('getsebool'):
        return {'applicable':False,'enabled':True,'paths':[]}
    if run(['getenforce']).stdout.strip()=='Disabled':
        return {'applicable':False,'enabled':True,'paths':[]}
    paths=[str(folder)] if folder else configured_paths()
    affected=[path for path in paths if is_fuse(path)]
    if not affected:
        return {'applicable':False,'enabled':True,'paths':[]}
    result=run(['getsebool',FLAG],check=False)
    if result.returncode:
        raise RuntimeError('SELinux sharing permissions could not be checked.')
    return {'applicable':True,'enabled':result.stdout.strip().endswith('--> on'),'paths':affected}


def enable(folder, owner):
    import pwd
    if os.geteuid()!=0 or owner<=0:
        raise RuntimeError('Desktop administrator approval is required.')
    home=Path(pwd.getpwuid(owner).pw_dir).resolve()
    info=status(folder)
    if not info['applicable']:
        raise RuntimeError('No SELinux-protected NTFS/FUSE shared folder was found.')
    owned=[]
    for value in info['paths']:
        path=Path(value)
        # Only repair a caller-owned share or a caller-owned proposed folder.
        if path.is_dir() and path.resolve()==path and path.stat().st_uid==owner:
            if not folder or (path!=home and any(base in path.parents for base in (home,Path('/mnt'),Path('/media'),Path('/run/media'),Path('/srv/share-scout')))):
                owned.append(value)
    if not owned:
        raise RuntimeError('Choose a shared folder owned by the account requesting this repair.')
    if info['enabled']:
        return {'ok':True,'message':'NTFS/FUSE sharing permission is already enabled.'}
    try:
        run(['setsebool','-P',FLAG,'on'])
        if not status(folder)['enabled']:
            raise RuntimeError('The SELinux permission change could not be verified.')
    except Exception:
        run(['setsebool','-P',FLAG,'off'])
        raise
    return {'ok':True,'message':'Samba can now access configured NTFS/FUSE shares. Retry the connection from the other computer. SELinux remains enabled.'}


def main():
    try:
        if sys.argv[1:]!=['--admin']:
            raise RuntimeError('Use the ShareScout confirmation dialog for this repair.')
        payload=json.loads(sys.stdin.read(65536))
        if payload.get('confirmed') is not True:
            raise RuntimeError('Confirm the system-wide sharing permission before continuing.')
        folder=payload.get('folder')
        if folder is not None and (not isinstance(folder,str) or len(folder)>4096 or any(c in folder for c in '\r\n\x00')):
            raise ValueError('Choose a valid local folder.')
        response=enable(folder,int(os.environ.get('PKEXEC_UID','0')))
        print(json.dumps(response))
        return 0
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
        return 1


if __name__=='__main__':
    sys.exit(main())
