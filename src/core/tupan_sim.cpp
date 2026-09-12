// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — CLI nativo (tupan_sim)
//  ---------------------------------------------------------------------------
//  Uso:
//    tupan_sim --night 8 --day 6 --runs 50000 [--ur 65] [--temp 24]
//              [--fluxo 25] [--efic 0.85] [--aquec 120] [--json] [--log tupan.bin]
//  Saída: kg sorvidos, litros destilados, percentis Monte Carlo e ML.
// ============================================================================
#include "tupan_core.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

using namespace tupan; // CLI simples: aliases do núcleo visíveis no arquivo todo

namespace {

struct Opts {
    Real night = 8.0, day = 6.0;
    int  runs = 20000;
    Real ur = 65.0, temp = 24.0, fluxo = 25.0, efic = 0.85, aquec = 120.0;
    bool json = false;
    std::string log_path;
};

[[nodiscard]] Opts parse(int argc, char** argv) {
    Opts o;
    auto val = [&](int& i) { return std::string(argv[static_cast<std::size_t>(++i)]); };
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[static_cast<std::size_t>(i)];
        if (a == "--night")   o.night = std::stod(val(i));
        else if (a == "--day")     o.day   = std::stod(val(i));
        else if (a == "--runs")    o.runs  = std::stoi(val(i));
        else if (a == "--ur")      o.ur    = std::stod(val(i));
        else if (a == "--temp")    o.temp  = std::stod(val(i));
        else if (a == "--fluxo")   o.fluxo = std::stod(val(i));
        else if (a == "--efic")    o.efic  = std::stod(val(i));
        else if (a == "--aquec")   o.aquec = std::stod(val(i));
        else if (a == "--json")    o.json  = true;
        else if (a == "--log")     o.log_path = val(i);
        else if (a == "--help") {
            std::puts("uso: tupan_sim [--night h] [--day h] [--runs N] [--ur %] [--temp °C] "
                      "[--fluxo m³/h] [--efic 0..1] [--aquec °C] [--json] [--log arquivo.bin]");
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
    e.heater_temp_c     = o.aquec;

    // Binlog não-crítico: rotinas e avisos vão p/ arquivo binário.
    if (!o.log_path.empty()) {
        sim.attach_logger(o.log_path);
        sim.blog(LogLevel::INFO, "cli", "simulação iniciada");
    }

    const auto mc  = sim.monte_carlo(o.runs, o.night, o.day, 42ULL);
    const auto det = full_cycle(o.night, o.day, o.ur, o.temp, o.fluxo, o.efic, o.aquec);
    double rmse = 0.0, r2 = 0.0;
    sim.ml_accuracy(rmse, r2);
    const double ml = sim.predict_output(sim.add_tupan(), o.night, o.day);

    if (o.json) {
        std::printf("{\"noite_h\":%.2f,\"dia_h\":%.2f,\"sorvido_kg\":%.4f,\"destilado_l\":%.4f,"
                    "\"potavel_l\":%.4f,\"ca_mg_l\":%.1f,\"mg_mg_l\":%.1f,\"bacia_cheia\":%s,"
                    "\"mc\":{\"media\":%.4f,\"p05\":%.4f,\"p50\":%.4f,\"p95\":%.4f},"
                    "\"ml\":%.4f,\"rmse\":%.6f,\"r2\":%.4f,\"l_por_kwh\":%.3f}\n",
                    o.night, o.day, det.water_kg_sorbed, det.distilled_l,
                    det.potable_l, det.ca_mg_l, det.mg_mg_l,
                    det.basin_full ? "true" : "false",
                    mc.mean, mc.p05, mc.p50, mc.p95, ml, rmse, r2, det.liters_per_kwh);
    } else {
        std::printf("Tupan, Máquina de Chuva — simulação nativa (sorção → solenoide → vidraria → filtro+UV → bacia)\n");
        std::printf("  noite: UR %.0f%% | %.0f °C | %.0f m³/h | η %.2f → %.2f kg sorvidos no leito\n",
                    o.ur, o.temp, o.fluxo, o.efic, det.water_kg_sorbed);
        std::printf("  dia  : solenoide %.0f °C → %.2f L destilados na vidraria\n",
                    o.aquec, det.distilled_l);
        std::printf("  pós  : filtro mineralizante (Ca %.0f/Mg %.0f mg/L) + UV-C → %.2f L na bacia%s\n",
                    det.ca_mg_l, det.mg_mg_l, det.potable_l,
                    det.basin_full ? " [bacia cheia]" : "");
        std::printf("  Monte Carlo (%d corridas): média %.3f L | p05 %.3f | p50 %.3f | p95 %.3f\n",
                    o.runs, mc.mean, mc.p05, mc.p50, mc.p95);
        std::printf("  ML grau 2  : %.3f L (RMSE %.4f, R² %.3f) | conta: %.2f L/kWh\n",
                    ml, rmse, r2, det.liters_per_kwh);
    }
    if (!o.log_path.empty())
        sim.blog(LogLevel::INFO, "cli", "simulação concluída");
    return 0;
}
