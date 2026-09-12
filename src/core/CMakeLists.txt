# ============================================================================
#  TUPAN, MÁQUINA DE CHUVA — Build nativo (C++23)
#  ---------------------------------------------------------------------------
#  Alvos:
#    tupan_sim    → CLI                (tupan_sim.cpp)
#    tupan_native → módulo Python      (tupan_pybind.cpp)[opcional: TUPAN_WITH_PYBIND]
#    tupan_tests  → testes unitários   (tupan_tests.cpp) [registrado no CTest]
#  Convenções modernas: -Wall -Wextra -Wpedantic, C++23, Release -O3.
# ============================================================================
cmake_minimum_required(VERSION 3.25)
project(tupan_native LANGUAGES CXX VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 23)                # C++23 (GCC 14+/Clang 17+)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)     # p/ clangd/linters

# ---------------------------------------------------------------
# Workaround didático: o caminho do repositório contém espaços
# ("Iot & PLCs/Tupan Water Maker"), e o passo POST_BUILD de strip
# do pybind11 não cita o caminho — quebrando o link do módulo.
# Neutralizamos o strip com `true` (no-op): a economia de tamanho é
# irrelevante aqui e a portabilidade do projeto importa mais.
# ---------------------------------------------------------------
if(UNIX)
    set(CMAKE_STRIP "/usr/bin/true" CACHE FILEPATH "Strip neutralizado (caminhos com espaços)" FORCE)
endif()

option(TUPAN_WITH_PYBIND "Construir o módulo Python"      ON)

# ---------------------------------------------------------------
# CLI — binário principal.
# ---------------------------------------------------------------
add_executable(tupan_sim tupan_sim.cpp)
target_include_directories(tupan_sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(tupan_sim PRIVATE -Wall -Wextra -Wpedantic)

# ---------------------------------------------------------------
# Testes — integrados ao CTest (ctest --test-dir build).
# ---------------------------------------------------------------
enable_testing()
add_executable(tupan_tests tupan_tests.cpp)
target_include_directories(tupan_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(tupan_tests PRIVATE -Wall -Wextra -Wpedantic)
add_test(NAME tupan_core_tests COMMAND tupan_tests)

# ---------------------------------------------------------------
# GUI Qt5 REMOVIDA — a interface gráfica é o Tupan Studio
# (src/studio: Lua DSL + Dear ImGui + OpenGL). Veja a opção TUPAN_WITH_STUDIO.
# ---------------------------------------------------------------

# ---------------------------------------------------------------
# Módulo Python — usa o pybind11 do ambiente (pip install pybind11).
# ---------------------------------------------------------------
if(TUPAN_WITH_PYBIND)
    find_package(pybind11 CONFIG QUIET)
    if(pybind11_FOUND)
        # NO_EXTRAS: evita o POST_BUILD de strip, que quebra em caminhos com
        # espaços/'&' (ex.: ".../Iot & PLCs/Tupan Water Maker/...").
        pybind11_add_module(tupan_native NO_EXTRAS ${CMAKE_CURRENT_SOURCE_DIR}/../bindings/tupan_pybind.cpp)
        target_include_directories(tupan_native PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
    else()
        message(STATUS "pybind11 não encontrado — módulo Python pulado (pip install pybind11).")
    endif()
endif()

# ---------------------------------------------------------------
# Módulo C++ (tupan.core) — demonstração de modules; alguns geradores
# ainda não suportam -fmodules-ts no CMake, por isso é opcional.
# ---------------------------------------------------------------
option(TUPAN_WITH_MODULES "Tentar compilar o módulo tupan.core" OFF)
if(TUPAN_WITH_MODULES)
    add_library(tupan_core_mod)
    target_sources(tupan_core_mod PRIVATE FILE_SET CXX_MODULES FILES tupan_core.cppm)
    target_include_directories(tupan_core_mod PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
    target_compile_options(tupan_core_mod PRIVATE -Wall -Wextra)
endif()
