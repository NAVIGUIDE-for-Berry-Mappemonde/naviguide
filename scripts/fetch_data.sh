#!/usr/bin/env bash
# Preferred entry point — forwards to download_geodata.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/download_geodata.sh" "$@"
