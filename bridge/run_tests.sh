#!/usr/bin/env bash
# Run the WhatsApp bridge test suite. No network, no WhatsApp account, no key.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m pytest tests_bridge -q "$@"
