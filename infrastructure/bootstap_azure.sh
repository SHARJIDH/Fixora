#!/usr/bin/env bash
set -euo pipefail

# Backward-compatible wrapper for common typo.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/bootstrap_azure.sh" "$@"
