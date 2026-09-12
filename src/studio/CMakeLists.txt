# ============================================================================
#  TUPAN STUDIO — Lua DSL + Dear ImGui + OpenGL 3.3
#  ---------------------------------------------------------------------------
#  Dependências: GLFW3, GLEW, Lua 5.4 (via pkg-config) + OpenGL.
#  Dear ImGui é baixado uma vez via FetchContent (não é empacotado).
#  A GUI Qt5 foi abandonada: este é o alvo gráfico do projeto.
# ============================================================================
find_package(OpenGL REQUIRED)
find_package(PkgConfig REQUIRED)

pkg_check_modules(GLFW REQUIRED IMPORTED_TARGET glfw3)
pkg_check_modules(GLEW REQUIRED IMPORTED_TARGET glew)
pkg_check_modules(LUA  REQUIRED IMPORTED_TARGET lua5.4)

# ---------------------------------------------------------------- ImGui ----
include(FetchContent)
FetchContent_Declare(imgui
    GIT_REPOSITORY https://github.com/ocornut/imgui.git
    GIT_TAG        v1.92.9b
    GIT_SHALLOW    TRUE)
# ----------------------------------------------------------------- sol2 ----
# Binding moderno Lua<->C++ (header-only). As janelas/menus do studio são
# descritos no DSL e lidos via sol2; lambdas C++ são expostas ao script.
FetchContent_Declare(sol2
    GIT_REPOSITORY https://github.com/ThePhD/sol2.git
    GIT_TAG        v3.5.0
    GIT_SHALLOW    TRUE)
if(POLICY CMP0169)
    cmake_policy(SET CMP0169 OLD)
endif()

FetchContent_GetProperties(imgui)
if(NOT imgui_POPULATED)
    FetchContent_Populate(imgui)
endif()
FetchContent_MakeAvailable(sol2)

add_library(imgui STATIC
    ${imgui_SOURCE_DIR}/imgui.cpp
    ${imgui_SOURCE_DIR}/imgui_draw.cpp
    ${imgui_SOURCE_DIR}/imgui_tables.cpp
    ${imgui_SOURCE_DIR}/imgui_widgets.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_glfw.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp)
target_include_directories(imgui PUBLIC
    ${imgui_SOURCE_DIR}
    ${imgui_SOURCE_DIR}/backends)
target_link_libraries(imgui PUBLIC PkgConfig::GLFW OpenGL::GL)

# ------------------------------------------------------------ tupan_studio --
add_executable(tupan_studio
    main.cpp
    scene.cpp
    lua_dsl.cpp)
target_include_directories(tupan_studio PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../core
    ${imgui_SOURCE_DIR}
    ${imgui_SOURCE_DIR}/backends)
target_link_libraries(tupan_studio PRIVATE
    imgui
    sol2::sol2
    PkgConfig::GLFW
    PkgConfig::GLEW
    PkgConfig::LUA
    OpenGL::GL)
target_compile_options(tupan_studio PRIVATE -Wall -Wextra -Wpedantic)
target_compile_definitions(tupan_studio PRIVATE
    TUPAN_STUDIO_DSL="${CMAKE_CURRENT_SOURCE_DIR}/assets/studio.lua")

message(STATUS "Tupan Studio: Lua + sol2 + Dear ImGui (${imgui_SOURCE_DIR}) + OpenGL.")
