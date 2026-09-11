// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Testes unitários do núcleo nativo (C++23)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: usamos um mini-framework de testes escrito à mão (sem dependências
//  externas) para mostrar como um "assert" bem armado vira um framework:
//    • Cada caso registra PASS/FAIL com mensagem em PT-BR;
//    • main() devolve o nº de falhas (0 = sucesso p/ CTest/CI).
//  Execute com:  ctest --test-dir build --output-on-failure
// ============================================================================
#include "tupan_core.hpp"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

// ---------------------------------------------------------------------------
// MINI-FRAMEWORK — armazena resultados e imprime relatório.
// RAII: o vetor vive na stack e o relatório é impresso no destrutor.
// ---------------------------------------------------------------------------
struct TestReport {
    struct Entry { std::string name; bool ok; std::string detail; };
    std::vector<Entry> entries;
    int failures = 0;

    void add(const std::string& name, bool ok, const std::string& detail) {
        entries.push_back({name, ok, detail});
        if (!ok) ++failures;
        std::printf("[%s] %s%s%s\n", ok ? "PASS" : "FAIL", name.c_str(),
                    detail.empty() ? "" : " — ", detail.c_str());
    }
    ~TestReport() {
        std::printf("\n== Resumo: %zu testes, %d falha(s) ==\n",
                    entries.size(), failures);
    }
};

// Comparação de doubles com tolerância absoluta.
bool near(double a, double b, double tol) { return std::fabs(a - b) <= tol; }

} // namespace

int main() {
    using namespace tupan;
    TestReport rep;

    // -------------------------------------------------------------------------
    // 1) Psicrometria — valores de referência da fórmula de Magnus.
    //    ρ_v(0 °C)  ≈ 4,85 g/m³   ρ_v(30 °C) ≈ 30,3 g/m³
    // -------------------------------------------------------------------------
    {
        const double r0 = saturation_vapor_density(0.0);
        const double r30 = saturation_vapor_density(30.0);
        rep.add("psicrometria: rho_v(0°C)≈4,85", near(r0, 4.85, 0.05),
                "obtido " + std::to_string(r0));
        rep.add("psicrometria: rho_v(30°C)≈30,3", near(r30, 30.3, 0.15),
                "obtido " + std::to_string(r30));
    }

    // -------------------------------------------------------------------------
    // 2) Saída teórica — casos-limite físicos.
    // -------------------------------------------------------------------------
    {
        rep.add("física: vazão 0 ⇒ produção 0",
                theoretical_output(1.0, 60, 28, 0.0, 0.85, 8.0) == 0.0);
        rep.add("física: eficiência 0 ⇒ produção 0",
                theoretical_output(1.0, 60, 28, 25.0, 0.0, 8.0) == 0.0);
        rep.add("física: ar mais seco que serpentina ⇒ produção 0",
                theoretical_output(1.0, 5, 10, 25.0, 0.85, 20.0) == 0.0);
        // Ponto de verificação do relatório: ~0,171 L/h @ UR60%/28 °C/25 m³/h.
        const double ref = theoretical_output(1.0, 60, 28, 25.0, 0.85, 8.0);
        rep.add("física: ponto nominal ≈ 0,171 L", near(ref, 0.171, 0.01),
                "obtido " + std::to_string(ref));
        // Linearidade em horas: 2 h ⇒ 2× produção (mesmo regime estacionário).
        const double d2 = theoretical_output(2.0, 60, 28, 25.0, 0.85, 8.0);
        rep.add("física: linearidade em horas (2h = 2×)", near(d2, 2.0 * ref, 1e-9));
    }

    // -------------------------------------------------------------------------
    // 3) Conceitos/templates — clamp01 restringido a tipos numéricos.
    // -------------------------------------------------------------------------
    {
        rep.add("conceito: clamp01(1.7)==1.0", clamp01(1.7) == 1.0);
        rep.add("conceito: clamp01(-3)==0.0", clamp01(-3) == 0.0);
        rep.add("conceito: clamp01(0.85)==0.85", clamp01(0.85) == 0.85);
    }

    // -------------------------------------------------------------------------
    // 4) Estocasticidade determinística — mesmo seed ⇒ mesmo valor.
    // -------------------------------------------------------------------------
    {
        TupanModel m;
        const double a = m.calculate_output(1.0, 7);
        const double b = m.calculate_output(1.0, 7);
        rep.add("RNG: mesmo seed ⇒ saída idêntica", a == b);
        TupanModel seco{{60, 28, 1013, 25, 0.85, 8.0}, 0.0}; // noise = 0
        rep.add("RNG: noise 0 ⇒ igual ao teórico",
                near(seco.calculate_output(1.0, 99),
                     theoretical_output(1.0, 60, 28, 25.0, 0.85, 8.0), 1e-12));
    }

    // -------------------------------------------------------------------------
    // 5) Modelo de ML — acurácia e aderência ao modelo físico.
    //    O regressor polinomial de grau 2 deve explicar uma função suave
    //    quase perfeitamente (R² > 0,9) e errar < 5 % nos pontos de teste.
    // -------------------------------------------------------------------------
    {
        MLPredictor ml;
        double rmse = 0.0, r2 = 0.0;
        ml.accuracy(123, 100, rmse, r2);
        rep.add("ML: R² > 0,90", r2 > 0.90, "R²=" + std::to_string(r2));
        rep.add("ML: RMSE < 0,02 L", rmse < 0.02, "RMSE=" + std::to_string(rmse));

        const std::array<double, 6> ponto{65.0, 30.0, 1013.0, 25.0, 0.85, 8.0};
        const double fisica = theoretical_output(1.0, 65, 30, 25.0, 0.85, 8.0);
        const double previsto = ml.predict(ponto);
        const double erro = std::fabs(previsto - fisica) / std::max(fisica, 1e-9);
        rep.add("ML: erro relativo < 5 % no ponto nominal", erro < 0.05,
                "física=" + std::to_string(fisica) + " ml=" + std::to_string(previsto));
    }

    // -------------------------------------------------------------------------
    // 6) Simulator — frota, ciclos e integridade de IDs.
    // -------------------------------------------------------------------------
    {
        Simulator s;
        const int id1 = s.add_tupan();
        const int id2 = s.add_tupan();
        rep.add("simulador: IDs sequenciais", id1 == 1 && id2 == 2);
        s.remove_tupan(id1);
        rep.add("simulador: remoção reflete no count", s.count() == 1);

        auto res = s.run_cycle(1.0, 42);
        rep.add("simulador: ciclo cobre a frota", res.size() == 1);
        rep.add("simulador: status coerente com output",
                res[0].status == ((res[0].output_liters > 0.0) ? "producing" : "idle"));

        // ID inexistente ⇒ previsão 0 (sem exceção: consulta segura).
        rep.add("simulador: ID inexistente ⇒ previsão 0.0",
                s.predict_output(777, 1.0) == 0.0);
    }

    // -------------------------------------------------------------------------
    // 7) Monte Carlo paralelo — ordem estatística e determinismo.
    // -------------------------------------------------------------------------
    {
        Simulator s;
        s.env().relative_humidity = 70.0;
        const auto mc1 = s.monte_carlo(20000, 1.0, 42);
        const auto mc2 = s.monte_carlo(20000, 1.0, 42);
        rep.add("Monte Carlo: determinístico entre chamadas",
                mc1.mean == mc2.mean && mc1.p50 == mc2.p50);
        rep.add("Monte Carlo: p05 ≤ p50 ≤ p95",
                mc1.p05 <= mc1.p50 && mc1.p50 <= mc1.p95);
        const double teorico = theoretical_output(1.0, 70, 28, 25.0, 0.85, 8.0);
        rep.add("Monte Carlo: média ≈ teórico (±5 % ruído)",
                near(mc1.mean, teorico, 0.01 * teorico + 1e-6),
                "média=" + std::to_string(mc1.mean) + " teórico=" + std::to_string(teorico));
        rep.add("Monte Carlo: runs=0 ⇒ struct zerada",
                s.monte_carlo(0, 1.0).mean == 0.0);
    }

    // -------------------------------------------------------------------------
    // 8) Previsão para a frota — unidades conhecidas recebem previsão > 0
    //    em condição úmida (UR 80 %).
    // -------------------------------------------------------------------------
    {
        Simulator s;
        const int id = s.add_tupan();
        s.env().relative_humidity = 80.0;
        rep.add("previsão: unidade ativa > 0 L/h", s.predict_output(id, 1.0) > 0.0);
    }

    return rep.failures == 0 ? 0 : 1;
}
