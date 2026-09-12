# ============================================================================
#  TUPAN, MÁQUINA DE CHUVA — Build raiz (orquestra núcleo + studio)
#  ---------------------------------------------------------------------------
#  Uso local:      cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
#                  cmake --build build -j"$(nproc)"
#  Uso headless:   -DTUPAN_WITH_STUDIO=OFF -DTUPAN_WITH_SCRIPTING=OFF
#  Alvos principais: tupan_sim, tupan_tests, tupan_native (pybind),
#                    tupan_studio (Lua+ImGui+OpenGL), tupan_script (luaaa).
# ============================================================================
cmake_minimum_required(VERSION 3.25)
project(tupan LANGUAGES CXX VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# DIDÁTICA: concentra TODOS os artefatos (executáveis, .so do pybind, libs) na
# raiz de `build/`. Assim os scripts em `tools/` encontram `build/tupan_native*.so`
# e os READMEs documentam um único caminho, independentemente do subdiretório.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

option(TUPAN_WITH_PYBIND  "Construir o módulo Python (pybind11)"    ON)
option(TUPAN_WITH_STUDIO  "Construir o Tupan Studio (Lua+ImGui+GL)" ON)
option(TUPAN_WITH_SCRIPTING "Construir o runner Lua headless (luaaa)" ON)

# DIDÁTICA: habilita o CTest na RAIZ para que `ctest --test-dir build` enxergue
# os testes registrados nos subdiretórios (src/core).
enable_testing()

# O núcleo (src/core) define os alvos C++23, testes e pybind.
add_subdirectory(src/core)

# O studio é independente e opcional; só entra se as fontes existirem.
if(TUPAN_WITH_STUDIO AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/src/studio/CMakeLists.txt")
    add_subdirectory(src/studio)
elseif(TUPAN_WITH_STUDIO)
    message(STATUS "src/studio ausente — Tupan Studio pulado.")
endif()

# Runner headless em Lua (luaaa expõe o núcleo ao script) — sem janela.
if(TUPAN_WITH_SCRIPTING AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/src/scripting/CMakeLists.txt")
    add_subdirectory(src/scripting)
elseif(TUPAN_WITH_SCRIPTING)
    message(STATUS "src/scripting ausente — runner Lua pulado.")
endif()
