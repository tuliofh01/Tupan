#!/usr/bin/env bash
# ============================================================================
#  TUPAN — Build do executável standalone do serviço web (PyInstaller)
#  ---------------------------------------------------------------------------
#  Gera dist/standalone/tupan-web: um ÚNICO arquivo que roda o simulador web
#  sem exigir Python instalado no destino (Linux/Windows/macOS conforme o host).
#  Uso: scripts/build-standalone.sh
#  Requer: pip install pyinstaller (+ flask; waitress é opcional/produção).
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PY="${PYTHON:-python3}"

if ! "${PY}" -c "import PyInstaller" >/dev/null 2>&1; then
    echo "[erro] PyInstaller ausente. Instale com: ${PY} -m pip install pyinstaller" >&2
    exit 1
fi
if ! "${PY}" -c "import flask" >/dev/null 2>&1; then
    echo "[erro] Flask ausente. Instale com: ${PY} -m pip install -r requirements.txt" >&2
    exit 1
fi

if ! ls build/tupan_native* >/dev/null 2>&1; then
    echo "[aviso] módulo nativo não encontrado em build/ — o binário usará o fallback Python."
    echo "        compile antes com: cmake -S . -B build && cmake --build build"
fi

echo "[standalone] gerando dist/standalone/tupan-web ..."
"${PY}" -m PyInstaller --noconfirm --clean \
    --distpath "${ROOT}/dist/standalone" \
    --workpath "${ROOT}/build/pyinstaller" \
    "${ROOT}/packaging/tupan-web.spec"

echo "[ok] executável: ${ROOT}/dist/standalone/tupan-web"
echo "     teste:      ${ROOT}/dist/standalone/tupan-web   (http://127.0.0.1:5000)"
