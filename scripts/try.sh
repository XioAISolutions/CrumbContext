#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT="${1:-proof}"

"$PYTHON_BIN" -m pip install -e '.[dev]'
"$PYTHON_BIN" -m pytest
crumbcontext benchmark --out "$OUT"

echo
echo "Proof created: $ROOT/$OUT/report.html"
echo "Share card:   $ROOT/$OUT/share-card.svg"

case "$(uname -s)" in
  Darwin) open "$OUT/report.html" >/dev/null 2>&1 || true ;;
  Linux) command -v xdg-open >/dev/null && xdg-open "$OUT/report.html" >/dev/null 2>&1 || true ;;
esac
