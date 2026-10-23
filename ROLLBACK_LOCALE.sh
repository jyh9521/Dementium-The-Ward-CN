#!/usr/bin/env bash
set -euo pipefail
# Restores only a separate build/rollback-sample; keeps the modified manual sample.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$ROOT/tools/build_locale.py" ]]; then
  PROJECT="$ROOT"
  OUTPUT="${1:-$ROOT/build/full}"
else
  PROJECT="$(cd -- "$ROOT/../.." && pwd)"
  OUTPUT="${1:-$ROOT}"
fi
"${PYTHON:-python}" -X utf8 "$PROJECT/tools/build_locale.py" rollback --output "$OUTPUT"
