#!/bin/bash
# Wrapper script for running Apache Highlights from cron

cd "/home/rbowen/devel/apache/highlights"
source "/home/rbowen/devel/apache/highlights/venv/bin/activate"
python3 "/home/rbowen/devel/apache/highlights/highlights.py" "$@"
