// ============================================================================
//  TUPAN SCRIPTING — runner headless (luaaa)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: aqui o Lua "chama" o C++. Expomos funções do núcleo (tupan_core.hpp)
//  como um módulo `tupan` usando luaaa (binding single-header, sem boilerplate).
//  Assim qualquer script Lua calcula ciclos reais sem recompilar o programa:
//
//      print(tupan.potavel(8, 6, 68, 24))   --> litros potáveis no ciclo padrão
//
//  Uso: tupan_script [arquivo.lua]   (sem argumento, roda scripts/ciclo.lua)
// ============================================================================
#include "luaaa.hpp"
#include "tupan_core.hpp"

#include <cstdio>
#include <string>

#ifndef TUPAN_SCRIPT_DEFAULT
#define TUPAN_SCRIPT_DEFAULT "ciclo.lua"
#endif

namespace {

// Vazão das ventoinhas e eficiência padrão do projeto (iguais à CLI).
constexpr double kFanFlow = 25.0;
constexpr double kEfficiency = 0.85;
constexpr double kHeaterC = 120.0;

[[nodiscard]] double potavel(double noite, double dia, double ur, double temp) noexcept {
    return static_cast<double>(
        tupan::full_cycle(noite, dia, ur, temp, kFanFlow, kEfficiency, kHeaterC).potable_l);
}
[[nodiscard]] double energia_kwh(double noite, double dia, double ur, double temp) noexcept {
    return static_cast<double>(
        tupan::full_cycle(noite, dia, ur, temp, kFanFlow, kEfficiency, kHeaterC).energy_kj_total / 3.6e6);
}
[[nodiscard]] double l_por_kwh(double noite, double dia, double ur, double temp) noexcept {
    return static_cast<double>(
        tupan::full_cycle(noite, dia, ur, temp, kFanFlow, kEfficiency, kHeaterC).liters_per_kwh);
}

}  // namespace

int main(int argc, char** argv) {
    lua_State* L = luaL_newstate();
    luaL_openlibs(L);

    // Módulo `tupan`: constantes + funções lambdas do núcleo (luaaa converte).
    luaaa::LuaModule(L, "tupan")
        .def("version", std::string("0.1.0"))
        .def("fan_flow", kFanFlow)
        .def("efficiency", kEfficiency)
        .fun("potavel", [](double n, double d, double u, double t) { return potavel(n, d, u, t); })
        .fun("energia_kwh", [](double n, double d, double u, double t) { return energia_kwh(n, d, u, t); })
        .fun("l_por_kwh", [](double n, double d, double u, double t) { return l_por_kwh(n, d, u, t); })
        .fun("sorvido", [](double n, double u, double t) {
            return static_cast<double>(tupan::sorption_intake(n, u, t, kFanFlow, kEfficiency));
        });

    const char* script = (argc > 1) ? argv[1] : TUPAN_SCRIPT_DEFAULT;
    if (luaL_dofile(L, script) != LUA_OK) {
        const char* err = lua_tostring(L, -1);
        std::fprintf(stderr, "Erro no script Lua: %s\n", err ? err : "?");
        lua_close(L);
        return 1;
    }
    lua_close(L);
    return 0;
}
