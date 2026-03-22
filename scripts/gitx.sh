#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_GIT_DIR="${PATENT_AGNET_GIT_DIR:-${HOME}/.codex/memories/patent_agnet.gitdir}"

if [[ ! -d "${EXTERNAL_GIT_DIR}" ]]; then
  echo "外置 Git 目录不存在: ${EXTERNAL_GIT_DIR}" >&2
  exit 1
fi

exec env \
  GIT_DIR="${EXTERNAL_GIT_DIR}" \
  GIT_WORK_TREE="${ROOT_DIR}" \
  git "$@"
