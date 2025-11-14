#!/bin/bash

# Create virtual environment for Mastodon posting
python3 -m venv mastodon_venv

# Activate virtual environment
source mastodon_venv/bin/activate

# Install Mastodon.py
pip install Mastodon.py

echo "Virtual environment created and Mastodon.py installed."
echo "Run 'source mastodon_venv/bin/activate' to activate the environment."
