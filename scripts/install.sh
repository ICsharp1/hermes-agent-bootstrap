#!/usr/bin/env bash
set -euo pipefail

HERMES_DIR="${HOME}/.hermes"
SCRIPTS_DIR="${HERMES_DIR}/scripts"
BIN_DIR="${HERMES_DIR}/bin"
SKILLS_DIR="${HERMES_DIR}/skills"
STATE_DIR="${HERMES_DIR}/state"

echo "=== Hermes Agent Bootstrap Installer ==="

# 1. Directory creation
mkdir -p "${SCRIPTS_DIR}" "${BIN_DIR}" "${STATE_DIR}" "${SKILLS_DIR}/research/feasibility-check"

# 2. Copy scripts
SCRIPT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_SRC}/day_plans.py" "${SCRIPTS_DIR}/"
cp "${SCRIPT_SRC}/rsvp_watch.py" "${SCRIPTS_DIR}/"
cp "${SCRIPT_SRC}/email_watch.py" "${SCRIPTS_DIR}/"
cp "${SCRIPT_SRC}/fix_epub.py" "${SCRIPTS_DIR}/"
chmod +x "${SCRIPTS_DIR}"/*.py

# 3. Copy binary wrapper
cp "${SCRIPT_SRC}/gws2" "${BIN_DIR}/"
chmod +x "${BIN_DIR}/gws2"

# 4. Copy custom skills
REPO_ROOT="$(cd "${SCRIPT_SRC}/.." && pwd)"
if [ -d "${REPO_ROOT}/skills/feasibility-check" ]; then
  cp -r "${REPO_ROOT}/skills/feasibility-check"/* "${SKILLS_DIR}/research/feasibility-check/"
  echo "✓ Installed skill: feasibility-check"
fi

# 5. Check PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
  echo "Notice: Add ${BIN_DIR} to your PATH in ~/.bashrc or ~/.profile:"
  echo "  export PATH=\"${BIN_DIR}:\$PATH\""
fi

echo "✓ Scripts and tools installed successfully to ${HERMES_DIR}"
