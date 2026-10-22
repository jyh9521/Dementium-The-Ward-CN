#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python -X utf8 tools/build_probe.py rollback --output build/phase2
