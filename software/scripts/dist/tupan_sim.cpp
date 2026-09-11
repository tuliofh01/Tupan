// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — CLI nativo (tupan_sim)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: binário de linha de comando que usa o núcleo header-only.
//  Uso:
//    tupan_sim --hours 8 --runs 50000 [--ur 65] [--temp 30] [--fluxo 25]
//              [--serp 8] [--efic 0.85] [--json]
//  Saída: produção média, percentis Monte Carlo e métricas do modelo ML.
// ============================================================================
#include "tupan_core.hpp"

#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <string>

namespace {

// Converte argv "chave valor" em parâmetros — struct simples de configuração.
struct Opts {
    double hours = 1.0;
    int    runs  = 20000;
    double ur = 60.0, temp = 28.0, fluxo = 25.0, efic = 0.85, serp = 8.0;
    bool   json = false;
};

[[nodiscard]] Opts parse(int argc, char** argv) {
    Opts o;
    auto val = [&](int& i) { return std::string(argv[static_cast<std::size_t>(++i)]); };
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[static_cast<std::size_t>(i)];
        if (a == "--hours" || a == "-h") o.hours = std::stod(val(i));
        else if (a == "--runs")          o.runs  = std::stoi(val(i));
        else if (a == "--ur")            o.ur    = std::stod(val(i));
        else if (a == "--temp")          o.temp  = std::stod(val(i));
        else if (a == "--fluxo")         o.fluxo = std::stod(val(i));
        else if (a == "--efic")          o.efic  = std::stod(val(i));
        else if (a == "--serp")          o.serp  = std::stod(val(i));
        else if (a == "--json")          o.json  = true;
        else if (a == "--help") {
            std::puts("uso: tupan_sim [--hours H] [--runs N] [--ur %] [--temp °C] "
                      "[--fluxo m3/h] [--efic 0..1] [--serp °C] [--json]");
            std::exit(0);
        }
    }
    return o;
}

} // namespace

int main(int argc, char** argv) {
    using namespace tupan;
    const Opts o = parse(argc, argv);

    Simulator sim;
    Environment& e = sim.env();
    e.relative_humidity = o.ur;
    e.temperature       = o.temp;
    e.fan_flow          = o.fluxo;
    e.efficiency        = o.efic;
    e.coil_temperature  = o.serp;

    const auto mc = sim.monte_carlo(o.runs, o.hours, 42ULL);
    double rmse = 0.0, r2 = 0.0;
    sim.ml_accuracy(rmse, r2);
    const double ml = sim.predict_output(sim.add_tupan(), o.hours);

    if (o.json) {
        std::printf("{\"horas\":%.2f,\"mc\":{\"media\":%.4f,\"p05\":%.4f,\"p50\":%.4f,\"p95\":%.4f},"
                    "\"ml\":%.4f,\"rmse\":%.6f,\"r2\":%.4f}\n",
                    o.hours, mc.mean, mc.p05, mc.p50, mc.p95, ml, rmse, r2);
    } else {
        std::printf("Tupan, Máquina de Chuva — simulação nativa\n");
        std::printf("  condições : UR %.0f%% | %.0f °C | %.0f m³/h | η %.2f | serpentina %.0f °C\n",
                    o.ur, o.temp, o.fluxo, o.efic, o.serp);
        std::printf("  Monte Carlo (%d corridas, %.1f h):\n", o.runs, o.hours);
        std::printf("    média %.3f L | p05 %.3f | p50 %.3f | p95 %.3f L\n",
                    mc.mean, mc.p05, mc.p50, mc.p95);
        std::printf("  ML grau 2 : %.3f L (RMSE %.4f, R² %.3f)\n", ml, rmse, r2);
    }
    return 0;
}
