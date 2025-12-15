import urllib.request
import urllib.parse
import json
import os
import sys
from pathlib import Path

def main():
    branch = 'master'
    if '--nightly' in sys.argv:
        branch = 'nightly'

    repo_api = f'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/{branch}?recursive=1'
    raw_base = f'https://raw.githubusercontent.com/sihooleebd/noteworthy/{branch}/'

    print(f'Fetching file list from {branch}...')
    try:
        req = urllib.request.Request(repo_api, headers={'User-Agent': 'Noteworthy-Loader'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f'Error: {e}')
        return

    files = []
    for item in data.get('tree', []):
        if item.get('type') != 'blob':
            continue
        p = item['path']
        if p.startswith('noteworthy/') or p == 'noteworthy.py':
            files.append(p)

    print(f'Downloading {len(files)} files...')
    for p in files:
        target = Path(p)
        url = raw_base + urllib.parse.quote(p)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url) as r, open(target, 'wb') as f:
                f.write(r.read())
            print(f'Downloaded {p}')
        except Exception as e:
            print(f'Failed {p}: {e}')
    print('Complete.')

if __name__ == '__main__':
    main()
