#!/bin/bash
# Install the Splitwise MCP server into <dir> (default ~/Bahikhaata/splitwise-mcp), apply the known startup fix,
# and create an empty .env for the user to fill in. Safe to re-run.
# usage: install_splitwise_mcp.sh [dir]
set -euo pipefail
DIR="${1:-$HOME/Bahikhaata/splitwise-mcp}"
REPO="https://github.com/tarunn2799/splitwise-mcp"

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3,10))'; then PY="$(command -v "$c")"; break; fi
done
[ -n "$PY" ] || { echo "NEED_PYTHON: install Python 3.10+ (https://www.python.org/downloads/ or 'brew install python@3.12')"; exit 2; }
command -v git >/dev/null || { echo "NEED_GIT: run 'xcode-select --install' and try again"; exit 2; }

if [ ! -d "$DIR/.git" ]; then git clone --quiet "$REPO" "$DIR"; fi
cd "$DIR"

# Upstream wraps server.run() in asyncio.run(), which crashes on start. FastMCP's run() manages its own loop.
M=src/splitwise_mcp_server/__main__.py
if grep -q 'asyncio.run(server.run' "$M"; then
  "$PY" - "$M" <<'EOF'
import re, sys
p = sys.argv[1]; s = open(p).read()
s = re.sub(r'asyncio\.run\((server\.run\([^)]*\))\)', r'\1', s)
s = s.replace('import asyncio\n', '', 1)
open(p, 'w').write(s)
EOF
  echo "PATCHED: server.run() fix applied"
fi

[ -x venv/bin/python ] || "$PY" -m venv venv
venv/bin/pip install --quiet --upgrade pip >/dev/null
venv/bin/pip install --quiet -e .

if [ ! -f .env ]; then
  umask 077
  cat > .env <<'EOF'
# Paste your Splitwise keys from https://secure.splitwise.com/apps after the = signs. No quotes, no spaces.
# This file stays on your computer. Never paste these keys into a chat.
SPLITWISE_OAUTH_CONSUMER_KEY=
SPLITWISE_OAUTH_CONSUMER_SECRET=
SPLITWISE_API_KEY=
EOF
fi
chmod 600 .env
grep -qx '.env' .gitignore 2>/dev/null || echo '.env' >> .gitignore
echo "OK: installed at $DIR (python: $DIR/venv/bin/python)"
