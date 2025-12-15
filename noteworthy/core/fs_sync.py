import shutil
from pathlib import Path

DEFAULT_CONTENT_TEMPLATE = '#import "../../templates/templater.typ": *\n\nWrite your content here.'

def ensure_content_structure(hierarchy, base_dir=Path('content')):
    """
    Ensures that the filesystem matches the hierarchy structure for *existence*.
    Creates missing directories and files.
    
    Args:
        hierarchy (list): The hierarchy list of dicts.
        base_dir (Path): The root content directory.
        
    Returns:
        list: List of created file paths.
    """
    created = []
    base_dir.mkdir(parents=True, exist_ok=True)
    
    for ci, ch in enumerate(hierarchy):
        ch_dir = base_dir / str(ci)
        ch_dir.mkdir(exist_ok=True)
        
        for pi, pg in enumerate(ch.get('pages', [])):
            pg_file = ch_dir / f'{pi}.typ'
            if not pg_file.exists():
                pg_file.write_text(DEFAULT_CONTENT_TEMPLATE)
                created.append(str(pg_file))
                
    return created

def cleanup_extra_files(hierarchy, base_dir=Path('content')):
    """
    Removes files in content directory that are not in the hierarchy.
    WARNING: Destructive.
    """
    if not base_dir.exists():
        return []
        
    deleted = []
    
    # 1. Identify valid paths
    valid_paths = set()
    for ci, ch in enumerate(hierarchy):
        ch_dir = base_dir / str(ci)
        valid_paths.add(ch_dir)
        for pi, _ in enumerate(ch.get('pages', [])):
            valid_paths.add(ch_dir / f'{pi}.typ')
            
    # 2. Walk and delete
    for ch_dir in base_dir.iterdir():
        if ch_dir.is_dir() and ch_dir.name.isdigit():
            # Check files inside
            for f in ch_dir.glob('*.typ'):
                if f.stem.isdigit():
                    if f not in valid_paths:
                        f.unlink()
                        deleted.append(str(f))
            
            # Remove dir if empty or not in hierarchy (and empty after file deletion)
            if ch_dir not in valid_paths:
                # If we deleted all files, we can remove dir if empty
                if not any(ch_dir.iterdir()):
                    ch_dir.rmdir()
                    deleted.append(str(ch_dir))
            else:
                # Dir is valid, but maybe empty now? 
                # keep it if it maps to a chapter
                pass
                
    return deleted
