#!/bin/bash

VENV_DIR="clone-repos-env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install requirements
pip install -r clone-repos-requirements.txt

# Run the Python script
python clone_apache_repos.py

# Deactivate virtual environment
deactivate
