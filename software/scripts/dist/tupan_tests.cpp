// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Testes unitários do núcleo nativo (C++23)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: mini-framework de testes à mão (sem deps externas):
//    • Cada caso registra PASS/FAIL com mensagem em PT-BR;
//    • main() devolve o nº de falhas (0 = sucesso p/ CTest/CI).
//  Execute com:  ctest --test-dir build --output-on-failure
//  Física testada: NOVO CICLO (sorção noturna + destilação diurna, sem
//  compressor) — ver tupan_core.hpp.
// ============================================================================
#include "tupan_core.hpp"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

// DIDÁTICA: `using` dentro do namespace anônimo — helpers enxergam os tipos
// do núcleo sem poluir o escopo global do binário de testes.
using namespace tupan;

bool near(Real a, Real b, Real tol) { return std::fabs(a - b) <= tol; }

// ---------------------------------------------------------------------------
// MINI-FRAMEWORK — relatório RAII: vive na stack, imprime no destrutor.
// ---------------------------------------------------------------------------
struct TestReport {
    struct Entry { std::string name; bool ok; std::string detail; };
    std::vector<Entry> entries;
    int failures = 0;

    // Default no 3º parâmetro: chamadas de 2 ou 3 argumentos.
    void add(const std::string& name, bool ok, const std::string& detail = "") {
        entries.push_back({name, ok, detail});
        if (!ok) ++failures;
        std::printf("[%s] %s%s%s\n", ok ? "PASS" : "FAIL", name.c_str(),
                    detail.empty() ? "" : " — ", detail.c_str());
    }
    ~TestReport() {
        std::printf("\n== Resumo: %zu testes, %d falha(s) ==\n", entries.size(), failures);
    }
};

} // namespace

int main() {
    using namespace tupan;
    TestReport rep;

    // -------------------------------------------------------------------------
    // 1) Psicrometria (fase de SORÇÃO) — referências da fórmula de Magnus.
    //    ρ_v(0 °C) ≈ 4,85 g/m³  ·  ρ_v(30 °C) ≈ 30,3 g/m³
    // -------------------------------------------------------------------------
    {
        const Real r0  = saturation_vapor_density(0.0);
        const Real r30 = saturation_vapor_density(30.0);
        rep.add("psicrometria: rho_v(0°C)≈4,85", near(r0, 4.85, 0.05), "obtido " + std::to_string(r0));
        rep.add("psicrometria: rho_v(30°C)≈30,3", near(r30, 30.3, 0.15), "obtido " + std::to_string(r30));
    }

    // -------------------------------------------------------------------------
    // 2) SORÇÃO noturna — limites físicos do leito e do ar.
    // -------------------------------------------------------------------------
    {
        rep.add("sorção: vazão 0 ⇒ captação 0", sorption_intake(8.0, 65, 24, 0.0, 0.85) == 0.0);
        rep.add("sorção: eficiência 0 ⇒ captação 0", sorption_intake(8.0, 65, 24, 25.0, 0.0) == 0.0);
        // Teto de saturação: M·q = 2,0 kg (padrão) — nunca ultrapassa.
        rep.add("sorção: nunca excede M·q (2,0 kg)",
                sorption_intake(24.0, 95, 30, 40.0, 1.0) <= constants().desiccant_mass_kg
                    * constants().sorption_capacity + 1e-9);
        // Monotonicidade: mais horas ⇒ captação igual ou maior.
        const Real h4  = sorption_intake(4.0, 65, 24, 25.0, 0.85);
        const Real h12 = sorption_intake(12.0, 65, 24, 25.0, 0.85);
        rep.add("sorção: monotônica em horas", h12 >= h4);
        // Valor nominal didático: 8 h @ UR65/24 °C/25 m³/h/η0,85 ∈ (0,2; 1,5) kg.
        const Real nom = sorption_intake(8.0, 65, 24, 25.0, 0.85);
        rep.add("sorção: nominal 8h ∈ (0,2; 1,5) kg", nom > 0.2 && nom < 1.5,
                "obtido " + std::to_string(nom));
    }

    // -------------------------------------------------------------------------
    // 3) DESTILAÇÃO diurna — energia limita; temperatura libera.
    // -------------------------------------------------------------------------
    {
        rep.add("destilação: 0 h ⇒ 0 L", distillation_output(0.0, 1.0, 120.0) == 0.0);
        rep.add("destilação: 0 kg ⇒ 0 L", distillation_output(6.0, 0.0, 120.0) == 0.0);
        rep.add("destilação: T<80 °C ⇒ não libera", distillation_output(6.0, 1.0, 70.0) == 0.0);
        // A energia limita: 250 W × 6 h = 1,5 kWh = 4860 kJ úteis; vaporizar
        // 1 kg precisa ~2196 kJ ⇒ 1 kg libera, mas 5 kg não.
        const Real l1 = distillation_output(6.0, 1.0, 120.0);
        const Real l5 = distillation_output(6.0, 5.0, 120.0);
        rep.add("destilação: 1 kg libera ~0,9 L (η 0,92)", near(l1, 0.92, 0.05),
                "obtido " + std::to_string(l1));
        rep.add("destilação: 5 kg é limitado por energia (≤ 2,2 L)", l5 <= 2.2 && l5 > l1,
                "obtido " + std::to_string(l5));
    }

    // -------------------------------------------------------------------------
    // 4) Ciclo completo — coerência e contas ambientais.
    // -------------------------------------------------------------------------
    {
        const auto cb = full_cycle(8.0, 6.0, 65.0, 24.0, 25.0, 0.85, 120.0);
        rep.add("ciclo: destilado ≤ sorvido", cb.distilled_l <= cb.water_kg_sorbed + 1e-9);
        rep.add("ciclo: energia > 0", cb.energy_kj_total > 0.0);
        rep.add("ciclo: L/kWh > 0", cb.liters_per_kwh > 0.0,
                "L/kWh " + std::to_string(cb.liters_per_kwh));
        rep.add("ciclo: 0 h noite ⇒ 0 L",
                full_cycle(0.0, 6.0, 65, 24, 25, 0.85, 120).distilled_l == 0.0);
    }

    // -------------------------------------------------------------------------
    // 5) Conceitos/templates — clamp01 numérico.
    // -------------------------------------------------------------------------
    {
        rep.add("conceito: clamp01(1.7)==1.0", clamp01(1.7) == 1.0);
        rep.add("conceito: clamp01(-3)==0.0", clamp01(-3) == 0.0);
        rep.add("conceito: clamp01(0.85)==0.85", clamp01(0.85) == 0.85);
    }

    // -------------------------------------------------------------------------
    // 6) Estocasticidade determinística — mesmo seed ⇒ mesmo valor.
    // -------------------------------------------------------------------------
    {
        TupanModel m;
        const Liters a = m.calculate_output(8.0, 6.0, 7);
        const Liters b = m.calculate_output(8.0, 6.0, 7);
        rep.add("RNG: mesmo seed ⇒ saída idêntica", a == b);
        TupanModel seco{{65, 24, 1013, 25, 0.85, 120}, 0.0}; // noise = 0
        const auto cb = full_cycle(8.0, 6.0, 65, 24, 25, 0.85, 120);
        rep.add("RNG: noise 0 ⇒ igual ao determinístico",
                near(seco.calculate_output(8.0, 6.0, 99), cb.distilled_l, 1e-12));
    }

    // -------------------------------------------------------------------------
    // 7) Modelo de ML — aderência à física do novo ciclo.
    // -------------------------------------------------------------------------
    {
        MLPredictor ml;
        Real rmse = 0.0, r2 = 0.0;
        ml.accuracy(123, 100, rmse, r2);
        rep.add("ML: R² > 0,90", r2 > 0.90, "R²=" + std::to_string(r2));
        // A física tem kinks (cortes max/min) — grau 2 aproxima com margem.
        rep.add("ML: RMSE < 0,10 L", rmse < 0.10, "RMSE=" + std::to_string(rmse));
    }

    // -------------------------------------------------------------------------
    // 8) Simulator — frota, ciclos, IDs e integração do binlog.
    // -------------------------------------------------------------------------
    {
        Simulator s;
        const Id id1 = s.add_tupan();
        const Id id2 = s.add_tupan();
        rep.add("simulador: IDs sequenciais", id1 == 1 && id2 == 2);
        s.remove_tupan(id1);
        rep.add("simulador: remoção reflete no count", s.count() == 1);

        auto res = s.run_cycle(8.0, 6.0, 42);
        rep.add("simulador: ciclo cobre a frota", res.size() == 1);
        rep.add("simulador: status coerente com output",
                res[0].status == ((res[0].output_liters > 0.0) ? "producing" : "idle"));
        rep.add("simulador: ID inexistente ⇒ previsão 0.0",
                s.predict_output(777, 8.0, 6.0) == 0.0);

        // Binlog não-crítico: deve criar arquivo e escrever registro.
        std::remove("/tmp/tupan_test.bin");
        s.attach_logger("/tmp/tupan_test.bin");
        s.blog(LogLevel::ROUTINE, "test", "rotina de verificação");
        s.blog(LogLevel::WARN, "test", "aviso não-crítico");
        std::FILE* f = std::fopen("/tmp/tupan_test.bin", "rb");
        rep.add("binlog: arquivo criado e não vazio", f != nullptr);
        if (f) {
            std::fseek(f, 0, SEEK_END);
            rep.add("binlog: 2 registros escritos (> 2 B)", std::ftell(f) > 2);
            std::fclose(f);
        }
    }

    // -------------------------------------------------------------------------
    // 9) Monte Carlo paralelo — determinismo, ordem e média.
    // -------------------------------------------------------------------------
    {
        Simulator s;
        // DIDÁTICA: o determinístico de referência DEVE usar os MESMOS valores
        // do ambiente (cópia local no MC) — daí fixar UR e temperatura aqui.
        s.env().relative_humidity = 70.0;
        s.env().temperature       = 24.0;
        const auto mc1 = s.monte_carlo(20000, 8.0, 6.0, 42);
        const auto mc2 = s.monte_carlo(20000, 8.0, 6.0, 42);
        rep.add("Monte Carlo: determinístico entre chamadas",
                mc1.mean == mc2.mean && mc1.p50 == mc2.p50);
        rep.add("Monte Carlo: p05 ≤ p50 ≤ p95",
                mc1.p05 <= mc1.p50 && mc1.p50 <= mc1.p95);
        const auto det = full_cycle(8.0, 6.0, 70, 24, 25, 0.85, 120);
        rep.add("Monte Carlo: média ≈ determinístico (±ruído)",
                near(mc1.mean, det.distilled_l, 0.02 * det.distilled_l + 1e-6),
                "média=" + std::to_string(mc1.mean));
        rep.add("Monte Carlo: runs=0 ⇒ struct zerada", s.monte_carlo(0, 8, 6).mean == 0.0);
    }

    // -------------------------------------------------------------------------
    // 10) Previsão p/ frota — condição úmida (UR 80 %) deve prever > 0.
    // -------------------------------------------------------------------------
    {
        Simulator s;
        const Id id = s.add_tupan();
        s.env().relative_humidity = 80.0;
        rep.add("previsão: unidade ativa > 0 L", s.predict_output(id, 8.0, 6.0) > 0.0);
    }

    return rep.failures == 0 ? 0 : 1;
}
