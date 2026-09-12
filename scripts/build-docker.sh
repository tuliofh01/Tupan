#!/usr/bin/env bash
# ============================================================================
#  TUPAN — build/push da imagem Docker (core | web | studio)
#  ---------------------------------------------------------------------------
#  Uso:
#    scripts/build-docker.sh [--target web|core] [--tag 0.1.0]
#                            [--registry ghcr.io/usuario] [--push]
#  Exemplos:
#    scripts/build-docker.sh --target web --tag dev
#    scripts/build-docker.sh --target core --registry registry.example.com/tupan --push
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="web"
TAG="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo dev)"
REGISTRY=""
PUSH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --target) TARGET="$2"; shift 2 ;;
        --tag) TAG="$2"; shift 2 ;;
        --registry) REGISTRY="$2"; shift 2 ;;
        --push) PUSH=true; shift ;;
        --help)
            echo "uso: $0 [--target web|core] [--tag T] [--registry REG] [--push]"; exit 0 ;;
        *) echo "opção desconhecida: $1" >&2; exit 1 ;;
    esac
done

command -v docker >/dev/null || { echo "[ERROR] docker não encontrado." >&2; exit 1; }

NAME="tupan-${TARGET}"
IMAGE="${NAME}:${TAG}"
TAGGED="${REGISTRY:+${REGISTRY}/}${IMAGE}"

echo "[DOCKER] build target=${TARGET} tag=${TAG}"
docker build -f "${ROOT_DIR}/docker/Dockerfile" --target "${TARGET}" \
    -t "${IMAGE}" "${ROOT_DIR}"
[[ -n "${REGISTRY}" ]] && docker tag "${IMAGE}" "${TAGGED}"

if [[ "${PUSH}" == true ]]; then
    [[ -z "${REGISTRY}" ]] && { echo "[ERROR] --push requer --registry." >&2; exit 1; }
    echo "[DOCKER] push ${TAGGED}"
    docker push "${TAGGED}"
fi

echo "[OK] imagem: ${TAGGED:-${IMAGE}}"
