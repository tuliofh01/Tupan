#!/usr/bin/env bash
# ============================================================================
#  TUPAN, MÁQUINA DE CHUVA — Build nativo multiplataforma
#  ---------------------------------------------------------------------------
#  Uso:   ./build.sh [linux|windows|macos|all]
#    linux   → x86_64 nativo (+ aarch64 se cross-compiler presente)
#    windows → cross-compile com mingw-w64 (se instalado) ou script p/ MSVC
#    macos   → instruções/script p/ clang ( Apple Silicon/Intel)
#  Saída: ./bin/  (tupan_sim, tupan_gui, tupan_tests, tupan_native*.so)
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

TARGET="${1:-linux}"
BUILD="build"
mkdir -p bin

build_native() {
    echo ">> Configurando CMake ($BUILD)…"
    cmake -S . -B "$BUILD" -DCMAKE_BUILD_TYPE=Release "$@"
    echo ">> Compilando…"
    cmake --build "$BUILD" -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
    # Copia artefatos p/ bin/ (so com sufixo de plataforma no pybind).
    find "$BUILD" -maxdepth 1 -type f \( -name 'tupan_*' -o -name '*.so' \) -exec cp -v {} bin/ \;
    echo ">> Testes:"
    ctest --test-dir "$BUILD" --output-on-failure || true
}

case "$TARGET" in
    linux)
        build_native
        if command -v aarch64-linux-gnu-g++ >/dev/null 2>&1; then
            echo ">> Cross-compile aarch64 (ARM64)…"
            BUILD=build-aarch64 \
            cmake -S . -B build-aarch64 -DCMAKE_BUILD_TYPE=Release \
                  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
                  -DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++ \
                  -DTUPAN_WITH_GUI=OFF -DTUPAN_WITH_PYBIND=OFF
            cmake --build build-aarch64 -j"$(nproc)"
            find build-aarch64 -maxdepth 1 -name 'tupan_sim' -exec cp -v {} bin/tupan_sim-aarch64 \;
            find build-aarch64 -maxdepth 1 -name 'tupan_tests' -exec cp -v {} bin/tupan_tests-aarch64 \;
        else
            echo "!! aarch64-linux-gnu-g++ ausente — pulando ARM64."
        fi
        ;;
    windows)
        if command -v x86_64-w64-mingw32-g++ >/dev/null 2>&1; then
            echo ">> Cross-compile Windows x86_64 (mingw-w64)…"
            cmake -S . -B build-win -DCMAKE_BUILD_TYPE=Release \
                  -DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR=AMD64 \
                  -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
                  -DTUPAN_WITH_GUI=OFF -DTUPAN_WITH_PYBIND=OFF
            cmake --build build-win -j"$(nproc)"
            find build-win -maxdepth 1 -name 'tupan_sim.exe' -exec cp -v {} bin/ \;
        else
            cat <<'EOF'
>> mingw-w64 ausente. No Windows (PowerShell, MSVC 2022):
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release
   ctest --test-dir build -C Release
EOF
        fi
        ;;
    macos)
        cat <<'EOF'
>> macOS (clang, Apple Silicon/Intel):
   brew install cmake qt pybind11
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$(brew --prefix qt)"
   cmake --build build -j
   ctest --test-dir build --output-on-failure
EOF
        ;;
    all)
        build_native
        "$0" windows
        ;;
    *)
        echo "uso: $0 [linux|windows|macos|all]" >&2
        exit 2
        ;;
esac
echo ">> Concluído. Artefatos em: $(pwd)/bin/"
