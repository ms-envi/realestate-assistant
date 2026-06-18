#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
set -a
source .env
set +a
/usr/bin/python3 main.py
