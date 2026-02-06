# Migration to uv run --script

## Changes Made

### 1. Updated `highlights.py`
- Added inline script metadata using PEP 723 format
- Changed shebang to `#!/usr/bin/env -S uv run --script`
- Dependencies (markdown) now declared inline
- Script is now self-contained and executable

### 2. Updated `apache_releases.py`
- Added inline script metadata using PEP 723 format
- Changed shebang to `#!/usr/bin/env -S uv run --script`
- Dependencies (requests) now declared inline
- Script is now self-contained and executable

### 3. Updated `clone_apache_repos.py`
- Added inline script metadata using PEP 723 format
- Changed shebang to `#!/usr/bin/env -S uv run --script`
- Dependencies (requests) now declared inline
- Script is now self-contained and executable

### 4. Deprecated Shell Scripts
- `run_highlights.sh` - no longer needed
- `run_releases.sh` - no longer needed
- `run_clone.sh` - no longer needed
- `uv` handles virtual environment creation automatically
- Dependencies are installed on first run

### 5. Updated README.md
- Removed references to shell wrapper scripts
- Updated all examples to use scripts directly
- Clarified that `uv` is the only prerequisite

## Benefits

1. **Simpler**: One file per script instead of shell script + Python script + requirements files
2. **Faster**: `uv` is significantly faster than traditional pip/venv
3. **Modern**: Uses PEP 723 inline script metadata standard
4. **Portable**: Scripts are self-contained with all dependencies declared inline
5. **Automatic**: No manual venv setup or activation needed

## Usage

Old way:
```bash
./run_clone.sh
./run_highlights.sh [options]
./run_releases.sh
```

New way:
```bash
./clone_apache_repos.py
./highlights.py [options]
./apache_releases.py
```

That's it! `uv` handles everything automatically.

## Cleanup (Optional)

You can now remove:
- `run_highlights.sh` (deprecated)
- `run_releases.sh` (deprecated)
- `run_clone.sh` (deprecated)
- `venv/` directory (if it exists)
- `clone-repos-env/` directory (if it exists)
- `requirements.txt` (dependencies now inline)
- `clone-repos-requirements.txt` (dependencies now inline)

The scripts will work exactly the same, just simpler and faster.
