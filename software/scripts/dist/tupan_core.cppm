// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Wrapper de MÓDULO C++ (tupan.core)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: a lógica única vive em tupan_core.hpp (header-only). Este módulo
//  a re-exporta como `tupan.core`, demonstrando coexistência header/module:
//    • O fragmento global (antes de `export module`) inclui o header legado;
//    • `export using` re-expõe os símbolos da biblioteca no escopo do módulo;
//    • Consumidores modernos fazem apenas:  import tupan.core;
//  Compilação (GCC 14+): g++ -std=c++23 -fmodules-ts ... (ver CMakeLists.txt)
// ============================================================================
module;
#include "tupan_core.hpp"

export module tupan.core;

// Re-exportação de tipos e funções da biblioteca.
export namespace tupan {
    using tupan::Environment;
    using tupan::TupanModel;
    using tupan::TupanUnit;
    using tupan::MonteCarloStats;
    using tupan::Simulator;
    using tupan::MLPredictor;
    using tupan::saturation_vapor_density;
    using tupan::theoretical_output;
    using tupan::clamp01;
}
