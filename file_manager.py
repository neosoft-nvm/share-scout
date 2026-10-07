"""Install per-user sharing actions using native file-manager extension formats."""
import os
from pathlib import Path
import shlex
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

LABEL = 'Share with ShareScout'
ACTION_ID = 'sharescout-share-folder'


def desktop_quote(value):
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'): value = value.replace(char, '\\' + char)
    # Desktop key values decode backslashes before parsing Exec.
    return '"' + value.replace('\\', '\\\\') + '"'


def write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink(): raise ValueError('Refusing to replace symbolic-link integration file: ' + str(path))
    if not path.exists() or path.read_text() != content: path.write_text(content)
    path.chmod(mode)


def install(app_dir=None, home=None, environ=None):
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    data = Path(environ.get('XDG_DATA_HOME') or home / '.local/share')
    config = Path(environ.get('XDG_CONFIG_HOME') or home / '.config')
    app_dir = Path(app_dir or Path(__file__).parent).resolve()
    launcher = data / 'sharescout/share-folder'
    command = 'exec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(app_dir / 'folder_share.py')) + ' "$@"\n'
    write(launcher, '#!/bin/sh\n' + command, 0o755)
    quoted = desktop_quote(launcher)
    installed = []; errors = []
    def attempt(name, task):
        try: task(); installed.append(name)
        except Exception as exc: errors.append(name + ': ' + str(exc))
    service = ('[Desktop Entry]\nType=Service\nMimeType=inode/directory;\nActions=share;\n'
               'X-KDE-Protocols=file\nX-KDE-RequiredNumberOfUrls=1\n'
               'X-KDE-Priority=TopLevel\n\n[Desktop Action share]\n'
               f'Name={LABEL}\nIcon=folder-remote\nExec={quoted} %f\n')
    attempt('Dolphin', lambda: write(data / 'kio/servicemenus/sharescout.desktop', service, 0o755))
    # Legacy KDE 5 installs still use this location and extra service key.
    attempt('Dolphin (legacy)', lambda: write(data / 'kservices5/ServiceMenus/sharescout.desktop', service.replace('Type=Service\n', 'Type=Service\nServiceTypes=KonqPopupMenu/Plugin\n'), 0o755))
    for manager, variable in [('nautilus', 'NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'), ('caja', 'CAJA_SCRIPT_SELECTED_FILE_PATHS')]:
        # File managers supply absolute selection paths in the environment. Avoid shell expansion of those paths.
        script = '#!/bin/sh\n' + 'exec ' + shlex.quote(str(launcher)) + ' --from-file-manager\n'
        attempt(manager.capitalize(), lambda manager=manager, script=script: write(data / manager / 'scripts' / LABEL, script, 0o755))
    nemo = ('[Nemo Action]\nActive=true\n' + f'Name={LABEL}\nComment=Share this folder with your other devices\n'
            f'Exec={quoted} %F\nSelection=s\nExtensions=dir;\nUriScheme=file\nQuote=double\nIcon-Name=folder-remote\n')
    attempt('Nemo', lambda: write(data / 'nemo/actions/sharescout.nemo_action', nemo))
    def thunar():
        path = config / 'Thunar/uca.xml'
        if path.is_symlink(): raise ValueError('Custom actions file is a symbolic link; add the action manually.')
        if path.exists():
            tree = ET.parse(path); root = tree.getroot()
            if root.tag != 'actions': raise ValueError('Unrecognized custom actions file; existing actions were kept.')
        else: root = ET.Element('actions'); tree = ET.ElementTree(root)
        current = next((action for action in root.findall('action') if action.findtext('unique-id') == ACTION_ID), None)
        action = ET.Element('action')
        for key, value in [('icon', 'folder-remote'), ('name', LABEL), ('unique-id', ACTION_ID),
                           ('command', shlex.quote(str(launcher)).replace('%', '%%') + ' %f'),
                           ('description', 'Share this folder with your other devices'), ('patterns', '*'), ('directories', '')]:
            ET.SubElement(action, key).text = value
        if current is not None and ET.tostring(current) == ET.tostring(action): return
        if current is not None: root.remove(current)
        root.append(action)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists(): shutil.copy2(path, path.with_name('uca.xml.sharescout-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak'))
        # Atomic replacement; never discard the user's other custom actions.
        temp = path.with_name('uca.xml.sharescout.tmp')
        if temp.exists() or temp.is_symlink(): raise ValueError('An unfinished actions update exists; existing actions were kept.')
        try:
            tree.write(temp, encoding='utf-8', xml_declaration=True)
            temp.replace(path)
        finally: temp.unlink(missing_ok=True)
    attempt('Thunar', thunar)
    shortcut = '[Desktop Entry]\nType=Application\nName=ShareScout — Share a folder\nComment=Create a protected network share\n' + f'Exec={quoted}\nIcon=folder-remote\nTerminal=false\nCategories=Network;FileManager;\n'
    attempt('Application menu', lambda: write(data / 'applications/sharescout-share.desktop', shortcut))
    return {'installed': installed, 'errors': errors}


if __name__ == '__main__':
    result = install(sys.argv[1] if len(sys.argv) > 1 else None)
    print('ShareScout folder-sharing shortcuts:', ', '.join(result['installed']))
    for error in result['errors']: print('Shortcut could not be installed:', error)
    print('Reopen your file manager to load new actions. In Files/Nautilus and Caja, use the Scripts submenu.')
