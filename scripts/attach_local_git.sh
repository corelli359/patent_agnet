#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_GIT_DIR="${PATENT_AGNET_GIT_DIR:-${HOME}/.codex/memories/patent_agnet.gitdir}"
GIT_ENTRY="${ROOT_DIR}/.git"

if [[ ! -d "${EXTERNAL_GIT_DIR}" ]]; then
  echo "外置 Git 目录不存在: ${EXTERNAL_GIT_DIR}" >&2
  exit 1
fi

if [[ -d "${GIT_ENTRY}" || -f "${GIT_ENTRY}" ]]; then
  BACKUP_PATH="${ROOT_DIR}/.git.sandbox-backup.$(date +%Y%m%d%H%M%S)"
  mv "${GIT_ENTRY}" "${BACKUP_PATH}"
  echo "已备份当前 .git 到: ${BACKUP_PATH}"
fi

printf 'gitdir: %s\n' "${EXTERNAL_GIT_DIR}" > "${GIT_ENTRY}"

git -C "${ROOT_DIR}" status --short >/dev/null

echo "已切换为外置 Git 目录:"
echo "  ${EXTERNAL_GIT_DIR}"
echo "现在可以直接在仓库根目录使用 git status / git pull / git push"
