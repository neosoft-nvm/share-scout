"""Read the published source version without downloading or executing an update."""
import ast
import base64
import json
import re
from urllib.request import Request, urlopen
from app_info import VERSION

REPOSITORY = 'https://github.com/neosoft-nvm/share-scout'
VERSION_URL = 'https://api.github.com/repos/neosoft-nvm/share-scout/contents/app_info.py?ref=main'
SOURCE_ZIP = REPOSITORY + '/archive/refs/heads/main.zip'


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('The published version format was not recognized.')
    return tuple(int(part) for part in value.split('.'))


def source_version(source):
    # Parse a literal constant; never import or execute downloaded Python.
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets):
            value = ast.literal_eval(node.value); version_tuple(value); return value
    raise ValueError('GitHub did not provide a version number.')


def check(installed=VERSION):
    version_tuple(installed)
    request = Request(VERSION_URL, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'ShareScout/' + installed, 'Cache-Control': 'no-cache'})
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read(65537)
        if len(payload) > 65536: raise ValueError('The version response was unexpectedly large.')
        data = json.loads(payload)
        if data.get('encoding') != 'base64': raise ValueError('The version response was not recognized.')
        source = base64.b64decode(data['content']).decode('utf-8')
        latest = source_version(source)
        return {'installed': installed, 'latest': latest, 'newer': version_tuple(latest) > version_tuple(installed)}
    except Exception as exc:
        raise RuntimeError('Could not check GitHub for updates. Check your internet connection and try again.\n\n' + str(exc)) from exc
