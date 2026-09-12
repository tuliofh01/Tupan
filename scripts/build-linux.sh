#!/usr/bin/env bash
# ============================================================================
#  TUPAN, MÁQUINA DE CHUVA — Build Script Linux (Ubuntu/Debian/Arch)
#  ---------------------------------------------------------------------------
#  Uso: scripts/build-linux.sh [--prefix DIR] [--package] [--clean] [--no-gui]
#  Saída:
#    build/                      → artefatos CMake (inclui tupan_native*.so)
#    dist/linux-x86_64/bin/      → tupan_sim, tupan_studio, tupan_tests, .so
#    dist/packages/*.tar.gz|.deb → com --package
#  Requer: cmake, g++, make, pybind11 (pip) e, p/ o studio, GLFW/GLEW/Lua.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}"
BUILD_DIR="${ROOT_DIR}/build"
DIST_DIR="${ROOT_DIR}/dist/linux-x86_64"
PREFIX="/usr/local"
PACKAGE=false
CLEAN=false
WITH_STUDIO=ON

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[BUILD]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat <<EOF
Uso: $0 [opções]
  --prefix DIR   Prefixo de instalação (default: /usr/local)
  --package      Gerar .tar.gz e .deb (se dpkg-deb disponível)
  --clean        Limpar build/ e dist/ antes de compilar
  --no-studio    Não construir o Tupan Studio (Lua+ImGui+OpenGL)
  --help         Esta ajuda
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --prefix) PREFIX="$2"; shift 2 ;;
        --package) PACKAGE=true; shift ;;
        --clean) CLEAN=true; shift ;;
        --no-studio) WITH_STUDIO=OFF; shift ;;
        --help) usage; exit 0 ;;
        *) err "Opção desconhecida: $1"; usage; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Dependências (build essencial; pybind11/studio avisam, não abortam)
# ---------------------------------------------------------------------------
log "Verificando dependências..."
MISSING=()
command -v cmake >/dev/null || MISSING+=("cmake")
command -v g++   >/dev/null || MISSING+=("g++")
command -v make  >/dev/null || MISSING+=("make")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    err "Dependências essenciais faltando: ${MISSING[*]}"
    echo "  Ubuntu/Debian: sudo apt install ${MISSING[*]}"
    echo "  Arch:          sudo pacman -S ${MISSING[*]}"
    exit 1
fi
python3 -c "import pybind11" 2>/dev/null || warn "pybind11 ausente (pip install pybind11) — módulo Python será pulado."
pkg-config --exists glfw3 2>/dev/null || warn "GLFW3 ausente — Tupan Studio será pulado (use --no-studio)."
ok "Verificação concluída"

[[ "$CLEAN" == true ]] && { log "Limpando..."; rm -rf "${BUILD_DIR}" "${DIST_DIR}"; }

# ---------------------------------------------------------------------------
# CMake + build + testes
# ---------------------------------------------------------------------------
log "Configurando CMake (fonte: raiz, build: build/)..."
cmake -S "${SOURCE_DIR}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
    -DTUPAN_WITH_STUDIO="${WITH_STUDIO}" \
    -DTUPAN_WITH_PYBIND=ON

log "Compilando ($(nproc) jobs)..."
cmake --build "${BUILD_DIR}" -j"$(nproc)"

log "Executando testes..."
ctest --test-dir "${BUILD_DIR}" --output-on-failure

# ---------------------------------------------------------------------------
# Empacota binários em dist/
# ---------------------------------------------------------------------------
log "Organizando ${DIST_DIR}..."
mkdir -p "${DIST_DIR}/bin" "${DIST_DIR}/share/tupan"
find "${BUILD_DIR}" -maxdepth 1 -type f \( -name 'tupan_sim' -o -name 'tupan_studio' \
    -o -name 'tupan_script' -o -name 'tupan_tests' -o -name 'tupan_native*.so' \) -exec cp -f {} "${DIST_DIR}/bin/" \;
cp -f "${SOURCE_DIR}/src/core/tupan_constants.json" "${DIST_DIR}/share/tupan/"

# Pacote Python importável (tupan/__init__.py + .so)
PY_SO="$(find "${DIST_DIR}/bin" -maxdepth 1 -name 'tupan_native*.so' | head -1 || true)"
if [[ -n "${PY_SO}" ]]; then
    PY_PKG="${DIST_DIR}/python/tupan"
    mkdir -p "${PY_PKG}"
    cp -f "${PY_SO}" "${PY_PKG}/_tupan_native.so"
    cat > "${PY_PKG}/__init__.py" <<'PYEOF'
"""Tupan, Máquina de Chuva — binding nativo Python (pybind11)."""
from ._tupan_native import *
__version__ = "0.1.0"
__all__ = [n for n in dir() if not n.startswith("_")]
PYEOF
    ok "Pacote Python: ${DIST_DIR}/python/tupan"
fi

# ---------------------------------------------------------------------------
# Empacotamento opcional
# ---------------------------------------------------------------------------
if [[ "$PACKAGE" == true ]]; then
    VERSION="0.1.0"; ARCH="$(uname -m)"; PKG_DIR="${ROOT_DIR}/dist/packages"
    mkdir -p "${PKG_DIR}"
    tar -czf "${PKG_DIR}/tupan-${VERSION}-linux-${ARCH}.tar.gz" -C "${DIST_DIR}" .
    ok "Pacote: ${PKG_DIR}/tupan-${VERSION}-linux-${ARCH}.tar.gz"

    if command -v dpkg-deb >/dev/null; then
        DEB_ROOT="${ROOT_DIR}/dist/deb"; rm -rf "${DEB_ROOT}"
        mkdir -p "${DEB_ROOT}/DEBIAN" "${DEB_ROOT}${PREFIX}/bin" "${DEB_ROOT}${PREFIX}/share/tupan"
        cp -f "${DIST_DIR}/bin/"* "${DEB_ROOT}${PREFIX}/bin/" 2>/dev/null || true
        cp -f "${DIST_DIR}/share/tupan/tupan_constants.json" "${DEB_ROOT}${PREFIX}/share/tupan/"
        cat > "${DEB_ROOT}/DEBIAN/control" <<DEBEOF
Package: tupan
Version: ${VERSION}
Section: science
Priority: optional
Architecture: ${ARCH}
Maintainer: Túlio Ferreira Horta <tulio.horta@pucmg.edu.br>
Description: Tupan, Maquina de Chuva — simulador atmosferico de agua
 Nucleo C++23 (sorcao CaCl2 + destilacao + pos-tratamento), binding
 Python (pybind11), CLI, testes e Tupan Studio.
DEBEOF
        dpkg-deb --build "${DEB_ROOT}" "${PKG_DIR}/tupan_${VERSION}-1_${ARCH}.deb"
        ok "Pacote: ${PKG_DIR}/tupan_${VERSION}-1_${ARCH}.deb"
    else
        warn "dpkg-deb ausente — pulando .deb"
    fi
fi

ok "Build Linux concluído!"
echo "Binários : ${DIST_DIR}/bin/"
echo "Módulo   : ${BUILD_DIR}/tupan_native*.so (usado pelos scripts em tools/)"
echo "  tupan_sim    — CLI de simulação"
echo "  tupan_studio — UI Lua+sol2+ImGui+OpenGL (cena 3D interativa)"
echo "  tupan_script — runner headless em Lua (luaaa)"
echo "  tupan_native — Módulo Python (pybind11)"
echo "  tupan_tests  — Testes unitários (CTest)"
