# ============================================================================
#  TUPAN SCRIPTING — runner headless em Lua via luaaa (single-header)
#  ---------------------------------------------------------------------------
#  Diferente do studio (sol2 lê o DSL das janelas), aqui usamos **luaaa** para
#  o sentido inverso: expor o núcleo C++ ao Lua, permitindo scripts de
#  simulação sem janela. Ideal para lote, CI e ensino.
# ============================================================================
find_package(PkgConfig REQUIRED)
pkg_check_modules(LUA REQUIRED IMPORTED_TARGET lua5.4)

include(FetchContent)
FetchContent_Declare(luaaa
    GIT_REPOSITORY https://github.com/gengyong/luaaa.git
    GIT_TAG        master
    GIT_SHALLOW    TRUE)
if(POLICY CMP0169)
    cmake_policy(SET CMP0169 OLD)
endif()
FetchContent_GetProperties(luaaa)
if(NOT luaaa_POPULATED)
    FetchContent_Populate(luaaa)
endif()

add_executable(tupan_script main.cpp)
target_include_directories(tupan_script PRIVATE
    ${luaaa_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../core)
target_link_libraries(tupan_script PRIVATE PkgConfig::LUA)
target_compile_options(tupan_script PRIVATE -Wall -Wextra -Wpedantic)
target_compile_definitions(tupan_script PRIVATE
    TUPAN_SCRIPT_DEFAULT="${CMAKE_CURRENT_SOURCE_DIR}/scripts/ciclo.lua")

message(STATUS "Tupan Scripting: luaaa em ${luaaa_SOURCE_DIR}")
