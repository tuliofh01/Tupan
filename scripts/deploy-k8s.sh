#!/usr/bin/env bash
# ============================================================================
#  TUPAN — deploy no Kubernetes (kubectl + kustomize opcional)
#  ---------------------------------------------------------------------------
#  Uso:
#    scripts/deploy-k8s.sh --registry ghcr.io/tuliofh --tag 0.1.0
#                          [--kubeconfig ~/.kube/config] [--dry-run]
#  Requer: kubectl (e opcionalmente kustomize).
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${ROOT_DIR}/deploy/k8s"
REGISTRY="ghcr.io/tuliofh"
TAG="latest"
KUBECONFIG_ARG=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --registry) REGISTRY="$2"; shift 2 ;;
        --tag) TAG="$2"; shift 2 ;;
        --kubeconfig) KUBECONFIG_ARG="$2"; shift 2 ;;
        --dry-run) DRY_RUN="--dry-run=client"; shift ;;
        --help) echo "uso: $0 [--registry REG] [--tag T] [--kubeconfig K] [--dry-run]"; exit 0 ;;
        *) echo "opção desconhecida: $1" >&2; exit 1 ;;
    esac
done

command -v kubectl >/dev/null || { echo "[ERROR] kubectl não encontrado." >&2; exit 1; }
KUBECTL=(kubectl)
[[ -n "${KUBECONFIG_ARG}" ]] && KUBECTL+=(--kubeconfig "${KUBECONFIG_ARG}")

IMAGE="${REGISTRY}/tupan-web:${TAG}"
echo "[K8S] aplicando namespace/recursos (imagem: ${IMAGE})"

"${KUBECTL[@]}" apply ${DRY_RUN} -f "${K8S_DIR}/namespace.yaml"
"${KUBECTL[@]}" apply ${DRY_RUN} -f "${K8S_DIR}/configmap.yaml"

# Ajusta a imagem no manifesto e aplica (sem depender de kustomize).
TMP="$(mktemp)"
sed "s|REGISTRY/tupan-web:TAG|${IMAGE}|" "${K8S_DIR}/deployment.yaml" > "${TMP}"
"${KUBECTL[@]}" apply ${DRY_RUN} -f "${TMP}"
rm -f "${TMP}"

for f in service.yaml ingress.yaml hpa.yaml; do
    "${KUBECTL[@]}" apply ${DRY_RUN} -f "${K8S_DIR}/${f}"
done

if [[ -z "${DRY_RUN}" ]]; then
    echo "[K8S] aguardando rollout..."
    "${KUBECTL[@]}" -n tupan rollout status deployment/tupan-web --timeout=120s
fi
echo "[OK] deploy concluído (imagem ${IMAGE})."
