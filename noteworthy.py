#!/usr/bin/env python3
import sys
import os
import json
import urllib.request
import urllib.parse
import shutil
from pathlib import Path

# ... (rest of imports)

# ... (bootstrap function)

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
            if Path('noteworthy').exists():
                shutil.rmtree('noteworthy')
            if Path('templates').exists():
                shutil.rmtree('templates')
                
        print(f"Updating/Installing Noteworthy from branch: {branch}")
        if not bootstrap(branch):
            print("Update failed or incomplete.")
            if not Path('noteworthy').exists():
                sys.exit(1)
        else:
            print("Update complete.")

    try:
        from noteworthy.__main__ import main
    except ImportError:
        # Fallback for local development or if just installed
        sys.path.append(str(Path(__file__).parent))
        from noteworthy.__main__ import main

    main()
