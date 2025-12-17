#!/usr/bin/env python3
import sys
import os
import json
import urllib.request
import urllib.parse
import shutil
from pathlib import Path

# ... (rest of imports)

def bootstrap(branch='master'):
    repo_api = f'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/{branch}?recursive=1'
    raw_base = f'https://raw.githubusercontent.com/sihooleebd/noteworthy/{branch}/'

    print(f'Fetching file list from {branch}...')
    try:
        req = urllib.request.Request(repo_api, headers={'User-Agent': 'Noteworthy-Loader'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f'Error fetching file list: {e}')
        return False

    files = []
    for item in data.get('tree', []):
        if item.get('type') != 'blob':
            continue
        p = item['path']
        if p.startswith('noteworthy/') or p.startswith('templates/') or p == 'noteworthy.py':
            # Changes for the user request: "JUST BRING THE SCHEMES"
            # We want to skip the default config/hierarchy/preface so we don't load the "tutor" content.
            # But we must ensure schemes.json is still downloaded.
            if p.startswith('templates/config/') and not p.endswith('schemes.json'):
                continue
            files.append(p)

    print(f'Downloading {len(files)} files...')
    success_count = 0
    for p in files:
        target = Path(p)
        url = raw_base + urllib.parse.quote(p)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url) as r, open(target, 'wb') as f:
                f.write(r.read())
            print(f'Downloaded {p}')
            success_count += 1
        except Exception as e:
            print(f'Failed {p}: {e}')
            
    return success_count > 0

if __name__ == "__main__":
    do_install = False
    branch = 'master'
    force = False
    
    # Parse flags
    if '--force-update-nightly' in sys.argv:
        do_install = True
        branch = 'nightly'
        force = True
        sys.argv.remove('--force-update-nightly')
    elif '--force-update' in sys.argv:
        do_install = True
        branch = 'master'
        force = True
        sys.argv.remove('--force-update')
    elif '--load-nightly' in sys.argv:
        do_install = True
        branch = 'nightly'
        sys.argv.remove('--load-nightly')
    elif '--load' in sys.argv:
        do_install = True
        sys.argv.remove('--load')
        
    # Auto-install if missing package
    if not Path('noteworthy').exists():
        do_install = True
        print("Noteworthy folder not found. Initiating download...")
        
    if do_install:
        if force:
            print("Force updating: Removing existing directories...")
            
            # Backup config files
            backups = []
            files_to_save = ['config.json', 'hierarchy.json', 'preface.typ']
            for fname in files_to_save:
                src = Path(f'templates/config/{fname}')
                if src.exists():
                    dst = Path(f'{fname}.bak')
                    try:
                        shutil.copy2(src, dst)
                        backups.append((dst, src))
                        print(f"Backed up {fname}")
                    except Exception as e:
                        print(f"Warning: Failed to backup {fname}: {e}")

            if Path('noteworthy').exists():
                shutil.rmtree('noteworthy')
            if Path('templates').exists():
                shutil.rmtree('templates')
                
        print(f"Updating/Installing Noteworthy from branch: {branch}")
        
        success = bootstrap(branch)
        
        # Restore backups regardless of success (to save user data)
        # If bootstrap successful, it overwrites defaults. If failed, it restores what it can.
        if force and backups:
            print("Restoring configuration files...")
            for dst, src in backups:
                try:
                    if dst.exists():
                        src.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst), str(src))
                        print(f"Restored {src.name}")
                except Exception as e:
                    print(f"Error restoring {src.name} (backup at {dst}): {e}")

        if not success:
            print("Update failed or incomplete.")
            if not Path('noteworthy').exists():
                sys.exit(1)
        else:
            print("Update complete.")
            
        # Avoid running main if we just updated and main is potentially old/new mix? 
        # Actually standard flow falls through. But we modified logic flow slightly.
        # Original code had if not bootstrap: ... else: print.
        # I refactored to check success variable.


    # Ensure preface.typ exists to prevent build errors, but keep it empty
    preface_path = Path('templates/config/preface.typ')
    if Path('templates/config').exists() and not preface_path.exists():
        try:
            preface_path.write_text('')
            print("Created empty preface.typ")
        except Exception as e:
            print(f"Warning: Could not create default preface: {e}")

    try:
        from noteworthy.__main__ import main
    except ImportError:
        # Fallback for local development or if just installed
        sys.path.append(str(Path(__file__).parent))
        from noteworthy.__main__ import main

    main()
