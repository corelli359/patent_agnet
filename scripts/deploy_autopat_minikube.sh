#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="autopat"
LLMSAFE_NAMESPACE="llmsafe"
MINIKUBE_HOME_DIR="${ROOT_DIR}/.minikube"
HOST_MOUNT_SOURCE="/Users"
MOUNT_TARGET="/minikube-users"
NODE_REPO_PATH="${MOUNT_TARGET}/${ROOT_DIR#${HOST_MOUNT_SOURCE}/}"
MOUNT_LOG="/tmp/autopat-minikube-mount.log"
MOUNT_PID_FILE="/tmp/autopat-minikube-mount.pid"
MANIFEST_TEMPLATE="${ROOT_DIR}/deploy/k8s/autopat/autopat.yaml"

require_supported_repo_path() {
  if [[ "${ROOT_DIR}" != "${HOST_MOUNT_SOURCE}/"* ]]; then
    echo "当前仓库路径不在 ${HOST_MOUNT_SOURCE} 下，无法复用 minikube 挂载方案: ${ROOT_DIR}" >&2
    exit 1
  fi
}

ensure_minikube_context() {
  local context
  context="$(kubectl config current-context)"
  if [[ "${context}" != "minikube" ]]; then
    echo "当前 kubectl context 不是 minikube: ${context}" >&2
    exit 1
  fi
}

ensure_ingress_addon() {
  if minikube addons list | grep -F "| ingress" | grep -F "enabled" >/dev/null 2>&1; then
    return
  fi

  minikube addons enable ingress >/dev/null
}

load_env_file() {
  local env_file=""

  if [[ -f "${ROOT_DIR}/.env.autopat" ]]; then
    env_file="${ROOT_DIR}/.env.autopat"
  elif [[ -f "${ROOT_DIR}/.env" ]]; then
    env_file="${ROOT_DIR}/.env"
  fi

  if [[ -z "${env_file}" ]]; then
    return
  fi

  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
}

prepare_runtime_dirs() {
  mkdir -p \
    "${ROOT_DIR}/data/cache" \
    "${ROOT_DIR}/data/runtime/k8s/pip-cache" \
    "${ROOT_DIR}/data/runtime/k8s/npm-cache" \
    "${ROOT_DIR}/data/vector_db/chroma" \
    "${ROOT_DIR}/logs"
}

prepare_minikube_home() {
  mkdir -p \
    "${MINIKUBE_HOME_DIR}/profiles/minikube" \
    "${MINIKUBE_HOME_DIR}/machines/minikube" \
    "${MINIKUBE_HOME_DIR}/certs" \
    "${MINIKUBE_HOME_DIR}/config"

  cp /Users/corelli/.minikube/config/config.json "${MINIKUBE_HOME_DIR}/config/"
  cp /Users/corelli/.minikube/ca.crt "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/ca.pem "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/cert.pem "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/key.pem "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/ca.key "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/proxy-client-ca.crt "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/proxy-client-ca.key "${MINIKUBE_HOME_DIR}/"
  cp /Users/corelli/.minikube/profiles/minikube/config.json "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/profiles/minikube/client.crt "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/profiles/minikube/client.key "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/profiles/minikube/apiserver.crt "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/profiles/minikube/apiserver.key "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/profiles/minikube/proxy-client.crt "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/profiles/minikube/proxy-client.key "${MINIKUBE_HOME_DIR}/profiles/minikube/"
  cp /Users/corelli/.minikube/machines/minikube/config.json "${MINIKUBE_HOME_DIR}/machines/minikube/"
  cp /Users/corelli/.minikube/machines/minikube/id_rsa "${MINIKUBE_HOME_DIR}/machines/minikube/"
  cp /Users/corelli/.minikube/machines/minikube/id_rsa.pub "${MINIKUBE_HOME_DIR}/machines/minikube/"
  rm -f "${MINIKUBE_HOME_DIR}/profiles/minikube/.mount-process"
}

ensure_mount() {
  if minikube ssh -- "test -d ${NODE_REPO_PATH}/backend" >/dev/null 2>&1; then
    return
  fi

  if ! grep -q "挂载到虚拟机中作为 ${MOUNT_TARGET}" "${MOUNT_LOG}" 2>/dev/null; then
    nohup env MINIKUBE_HOME="${MINIKUBE_HOME_DIR}" \
      minikube mount "${HOST_MOUNT_SOURCE}:${MOUNT_TARGET}" >"${MOUNT_LOG}" 2>&1 &
    echo $! > "${MOUNT_PID_FILE}"
  fi

  for _ in $(seq 1 30); do
    if minikube ssh -- "test -d ${NODE_REPO_PATH}/backend" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done

  echo "minikube 挂载未就绪，请检查 ${MOUNT_LOG}" >&2
  exit 1
}

stop_llmsafe() {
  if ! kubectl get namespace "${LLMSAFE_NAMESPACE}" >/dev/null 2>&1; then
    return
  fi

  kubectl scale deployment --all --replicas=0 -n "${LLMSAFE_NAMESPACE}" >/dev/null 2>&1 || true
  kubectl scale statefulset --all --replicas=0 -n "${LLMSAFE_NAMESPACE}" >/dev/null 2>&1 || true
  kubectl delete pod --all -n "${LLMSAFE_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
  kubectl delete ingress --all -n "${LLMSAFE_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
}

apply_secret() {
  local tmp_env
  tmp_env="$(mktemp)"

  echo "DEFAULT_LLM_PROVIDER=${DEFAULT_LLM_PROVIDER:-gemini}" > "${tmp_env}"
  echo "ENVIRONMENT=${ENVIRONMENT:-development}" >> "${tmp_env}"
  echo "LOG_LEVEL=${LOG_LEVEL:-INFO}" >> "${tmp_env}"
  echo "CHROMA_PERSIST_DIR=${CHROMA_PERSIST_DIR:-data/vector_db/chroma}" >> "${tmp_env}"
  echo "GOOGLE_PATENTS_DELAY=${GOOGLE_PATENTS_DELAY:-1.0}" >> "${tmp_env}"

  for key in \
    DEEPSEEK_API_KEY \
    GEMINI_API_KEY \
    CLAUDE_API_KEY \
    MYSQL_HOST \
    MYSQL_PORT \
    MYSQL_USER \
    MYSQL_PASSWORD \
    MYSQL_DATABASE; do
    if [[ -n "${!key:-}" ]]; then
      printf '%s=%s\n' "${key}" "${!key}" >> "${tmp_env}"
    fi
  done

  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl delete secret autopat-env -n "${NAMESPACE}" --ignore-not-found >/dev/null
  kubectl create secret generic autopat-env -n "${NAMESPACE}" --from-env-file="${tmp_env}" >/dev/null
  rm -f "${tmp_env}"
}

deploy_autopat() {
  local tmp_manifest
  tmp_manifest="$(mktemp)"

  sed "s|__NODE_REPO_PATH__|${NODE_REPO_PATH}|g" "${MANIFEST_TEMPLATE}" > "${tmp_manifest}"
  kubectl apply -f "${tmp_manifest}" >/dev/null
  rm -f "${tmp_manifest}"

  kubectl rollout restart deployment/autopat-backend -n "${NAMESPACE}" >/dev/null
  kubectl rollout restart deployment/autopat-frontend -n "${NAMESPACE}" >/dev/null
  kubectl rollout status deployment/autopat-backend -n "${NAMESPACE}" --timeout=20m
  kubectl rollout status deployment/autopat-frontend -n "${NAMESPACE}" --timeout=20m
}

print_summary() {
  local ingress_host
  ingress_host="$(
    kubectl get svc ingress-nginx-controller -n ingress-nginx \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true
  )"

  if [[ -z "${ingress_host}" || "${ingress_host}" == "<pending>" ]]; then
    ingress_host="$(minikube ip)"
  fi

  echo "autopat 已部署完成"
  echo "访问地址: http://${ingress_host}/"
  echo "健康检查: http://${ingress_host}/api/v1/health"
  echo "命名空间: ${NAMESPACE}"
  echo "仓库挂载: ${ROOT_DIR} -> ${NODE_REPO_PATH}"
}

require_supported_repo_path
ensure_minikube_context
ensure_ingress_addon
load_env_file
prepare_runtime_dirs
prepare_minikube_home
ensure_mount
stop_llmsafe
apply_secret
deploy_autopat
print_summary
