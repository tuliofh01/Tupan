#pragma once
// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Núcleo de simulação (header-only, C++23)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: este arquivo é a ÚNICA fonte da física/ML do simulador. Ele é
//  consumido de três formas diferentes para demonstrar integração:
//    1) tupan_sim.cpp   → CLI  (binário tupan_sim)
//    2) tupan_gui.cpp   → GUI  (Qt5 Widgets, binário tupan_gui)
//    3) tupan_pybind.cpp→ módulo Python (tupan_native)
//    4) tupan_core.cppm → wrapper em MÓDULO C++20/23 (import tupan.core;)
//  Recursos modernos usados: RAII, unique_ptr, std::jthread, concepts,
//  templates, auto, constexpr/inline, ranges-style lambdas.
// ============================================================================
#ifndef TUPAN_CORE_HPP
#define TUPAN_CORE_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <concepts>
#include <cstdint>
#include <memory>
#include <numeric>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

namespace tupan {

// ---------------------------------------------------------------------------
// CONCEITO (C++20 concepts): restringe templates a tipos numéricos.
// Assim, clamp01(3.14) compila; clamp01("texto") dá erro claro.
// ---------------------------------------------------------------------------
template <typename T>
concept Numeric = std::is_arithmetic_v<T>;

// [[nodiscard]] = o compilador avisa se você ignorar o retorno.
// constexpr = calculável em tempo de compilação quando possível.
[[nodiscard]] inline constexpr double clamp01(Numeric auto v) noexcept {
    return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : static_cast<double>(v));
}

inline constexpr double kDefaultNoise = 0.05; // ruído estocástico padrão (±5%)

// ---------------------------------------------------------------------------
// AMBIENTE — parâmetros físicos que o usuário ajusta no simulador.
// ---------------------------------------------------------------------------
struct Environment {
    double relative_humidity = 60.0;   // umidade relativa (%)
    double temperature       = 28.0;   // temperatura do ar (°C)
    double pressure          = 1013.0; // pressão atmosférica (hPa)
    double fan_flow          = 25.0;   // vazão do ventilador (m³/h)
    double efficiency        = 0.85;   // eficiência global do sistema (0..1)
    double coil_temperature  = 8.0;    // temperatura da serpentina (°C)
};

// ---------------------------------------------------------------------------
// PSICROMETRIA
// Magnus/Alduchov-Eskridge: e_s(T) = 6.1094·e^(17.625·T/(243.04+T)) [hPa]
// Densidade de vapor saturado: ρ_v = 216.7·e_s/(T+273.15) [g/m³]
// ---------------------------------------------------------------------------
[[nodiscard]] inline double saturation_vapor_density(double temp_c) noexcept {
    const double es = 6.1094 * std::exp((17.625 * temp_c) / (243.04 + temp_c));
    return 216.7 * es / (temp_c + 273.15);
}

// Produção teórica (litros): água condensável (g/m³) × ar movido (m³) × η.
[[nodiscard]] inline double theoretical_output(double hours, double humidity,
                                               double temperature, double fan_flow,
                                               double efficiency,
                                               double coil_temperature) noexcept {
    const double vapor_in    = (humidity / 100.0) * saturation_vapor_density(temperature);
    const double vapor_out   = saturation_vapor_density(coil_temperature);
    const double condensable = std::max(0.0, vapor_in - vapor_out); // g/m³
    const double volume_m3   = std::max(0.0, fan_flow * std::max(0.0, hours));
    return (condensable * volume_m3 * clamp01(efficiency)) / 1000.0; // g → L
}

// ---------------------------------------------------------------------------
// PRNG determinístico (xorshift64*) — mesmo seed ⇒ mesma saída.
// DIDÁTICA: `inline` no header evita múltiplas definições ao incluir em vários TUs.
// ---------------------------------------------------------------------------
[[nodiscard]] inline std::uint64_t next_rand(std::uint64_t& state) noexcept {
    state ^= state >> 12; state ^= state << 25; state ^= state >> 27;
    return state * 0x2545F4914F6CDD1DULL;
}
// Converte 64 bits em double ∈ [0,1) com 53 bits de precisão.
[[nodiscard]] inline double uniform01(std::uint64_t& state) noexcept {
    return static_cast<double>(next_rand(state) >> 11) / 9007199254740992.0;
}

// ---------------------------------------------------------------------------
// TUPAN MODEL — um dispositivo físico-estocástico.
// ---------------------------------------------------------------------------
struct TupanModel {
    Environment params;
    double noise = kDefaultNoise;

    // Espelha TupanModel.calculate_output() do Python (compatibilidade de seeds).
    [[nodiscard]] double calculate_output(double hours = 1.0, std::uint64_t seed = 1) const {
        const double u = uniform01(seed);
        const double noise_factor = 1.0 + (2.0 * u - 1.0) * noise;
        return std::max(0.0,
            theoretical_output(hours, params.relative_humidity, params.temperature,
                               params.fan_flow, params.efficiency,
                               params.coil_temperature) * noise_factor);
    }
};

// ---------------------------------------------------------------------------
// ML PREDICTOR — regressão polinomial de grau 2 (27 pesos) treinada aqui mesmo:
//   • 6 termos lineares + 15 cruzados + 6 quadráticos = 27 features (+bias)
//   • 500 amostras sintéticas (seed 42) no envelope operacional
//   • equações normais (XᵀX+λI)w = Xᵀy, Gauss com pivoteamento parcial
// DIDÁTICA: sklearn PolynomialFeatures(degree=2, include_bias=False) faz o
// mesmo mapeamento; aqui implementamos "na mão" para ficar 100% embarcado.
// ---------------------------------------------------------------------------
class MLPredictor {
public:
    MLPredictor() { train(); }

    [[nodiscard]] double predict(const std::array<double, 6>& x) const noexcept {
        const auto phi = features(x);
        double acc = w_.back(); // bias
        for (std::size_t j = 0; j < phi.size(); ++j) acc += w_[j] * phi[j];
        return acc;
    }

    // Métricas em amostra de teste sintética (RMSE e R²).
    void accuracy(std::uint64_t seed, int n, double& rmse, double& r2) const {
        const std::array<double, 6> lo{30, 15, 980, 10, 0.5, 5};
        const std::array<double, 6> hi{95, 40, 1035, 40, 1.0, 15};
        std::vector<double> ys(static_cast<std::size_t>(n)), ps(ys.size());
        double mean = 0.0;
        std::uint64_t st = seed;
        for (int i = 0; i < n; ++i) {
            std::array<double, 6> x{};
            for (int j = 0; j < 6; ++j) x[static_cast<std::size_t>(j)] =
                lo[static_cast<std::size_t>(j)] + uniform01(st) * (hi[static_cast<std::size_t>(j)] - lo[static_cast<std::size_t>(j)]);
            const std::size_t iu = static_cast<std::size_t>(i);
            ys[iu] = theoretical_output(1.0, x[0], x[1], x[2], x[3], x[5]);
            ps[iu] = predict(x);
            mean += ys[iu];
        }
        mean /= static_cast<double>(n);
        double sse = 0.0, sst = 0.0;
        for (std::size_t i = 0; i < ys.size(); ++i) {
            sse += (ys[i] - ps[i]) * (ys[i] - ps[i]);
            sst += (ys[i] - mean) * (ys[i] - mean);
        }
        rmse = std::sqrt(sse / static_cast<double>(n));
        r2   = (sst > 0.0) ? 1.0 - sse / sst : 1.0;
    }

private:
    static constexpr std::size_t kP = 27; // nº de features (sem bias)
    static constexpr std::size_t kD = 28; // features + bias

    // Mapeamento polinomial: [x1..x6, x1x2, x1x3..., x1²..x6²]
    [[nodiscard]] static std::array<double, kP> features(const std::array<double, 6>& x) noexcept {
        std::array<double, kP> f{};
        std::size_t k = 0;
        for (int i = 0; i < 6; ++i) f[k++] = x[static_cast<std::size_t>(i)];
        for (int i = 0; i < 6; ++i)
            for (int j = i + 1; j < 6; ++j)
                f[k++] = x[static_cast<std::size_t>(i)] * x[static_cast<std::size_t>(j)];
        for (int i = 0; i < 6; ++i) f[k++] = x[static_cast<std::size_t>(i)] * x[static_cast<std::size_t>(i)];
        return f;
    }

    // Treino via equações normais (matriz 28×28) — feito UMA vez no construtor.
    void train() {
        constexpr int N = 500;
        const std::array<double, 6> lo{30, 15, 980, 10, 0.5, 5};
        const std::array<double, 6> hi{95, 40, 1035, 40, 1.0, 15};

        std::vector<std::array<double, kD>> A(static_cast<std::size_t>(N));
        std::vector<double> y(static_cast<std::size_t>(N));
        std::uint64_t st = 42;
        for (int n = 0; n < N; ++n) {
            std::array<double, 6> x{};
            for (int j = 0; j < 6; ++j)
                x[static_cast<std::size_t>(j)] = lo[static_cast<std::size_t>(j)]
                    + uniform01(st) * (hi[static_cast<std::size_t>(j)] - lo[static_cast<std::size_t>(j)]);
            const auto phi = features(x);
            const std::size_t nu = static_cast<std::size_t>(n);
            for (std::size_t j = 0; j < kP; ++j) A[nu][j] = phi[j];
            A[nu][kP] = 1.0; // coluna de bias
            y[nu] = theoretical_output(1.0, x[0], x[1], x[2], x[3], x[5]);
        }

        // XᵀX (28×28) e Xᵀy (28) — acumulados em loop triplo trivial p/ P=28.
        std::array<std::array<double, kD>, kD> M{};
        std::array<double, kD> b{};
        for (int n = 0; n < N; ++n) {
            const auto& a = A[static_cast<std::size_t>(n)];
            const double yn = y[static_cast<std::size_t>(n)];
            for (std::size_t i = 0; i < kD; ++i) {
                b[i] += a[i] * yn;
                for (std::size_t j = 0; j < kD; ++j) M[i][j] += a[i] * a[j];
            }
        }
        for (std::size_t i = 0; i < kD; ++i) M[i][i] += 1e-9; // ridge λ (estabilidade)

        // Eliminação de Gauss com pivoteamento parcial.
        for (std::size_t col = 0; col < kD; ++col) {
            std::size_t piv = col;
            for (std::size_t r = col + 1; r < kD; ++r)
                if (std::abs(M[r][col]) > std::abs(M[piv][col])) piv = r;
            std::swap(M[col], M[piv]);
            std::swap(b[col], b[piv]);
            const double d = M[col][col];
            for (std::size_t r = col + 1; r < kD; ++r) {
                const double f = M[r][col] / d;
                if (f == 0.0) continue;
                for (std::size_t c = col; c < kD; ++c) M[r][c] -= f * M[col][c];
                b[r] -= f * b[col];
            }
        }
        // Retrossubstituição.
        w_.assign(kD, 0.0);
        for (std::size_t r = kD; r-- > 0;) {
            double s = b[r];
            for (std::size_t c = r + 1; c < kD; ++c) s -= M[r][c] * w_[c];
            w_[r] = s / M[r][r];
        }
    }

    std::vector<double> w_; // 28 pesos (27 features + bias)
};

// ---------------------------------------------------------------------------
// FROTA — uma unidade Tupan registrada no simulador.
// ---------------------------------------------------------------------------
struct TupanUnit {
    int id = 0;
    TupanModel model;
    double output = 0.0;
    std::string status = "online";
};

// Estatísticas de Monte Carlo (litros).
struct MonteCarloStats {
    double mean = 0.0;
    double p05  = 0.0;
    double p50  = 0.0;
    double p95  = 0.0;
};

// ---------------------------------------------------------------------------
// SIMULATOR — agrega a frota, executa ciclos e Monte Carlo PARALELO.
// RAII: unique_ptr gerencia o modelo de ML (liberação automática).
// ---------------------------------------------------------------------------
class Simulator {
public:
    struct CycleResult {
        int tupan_id = 0;
        double output_liters = 0.0;
        std::string status;
    };

    Simulator() : ml_(std::make_unique<MLPredictor>()) {}

    Environment&       env()       noexcept { return environment_; }
    [[nodiscard]] const Environment& env() const noexcept { return environment_; }

    int add_tupan() {
        TupanUnit u;
        u.id = next_id_++;
        units_.push_back(u);
        return u.id;
    }

    void remove_tupan(int id) {
        // std::erase_if (C++20): remove-erase idiomático sem loops manuais.
        std::erase_if(units_, [id](const TupanUnit& u) { return u.id == id; });
    }

    [[nodiscard]] int count() const noexcept { return static_cast<int>(units_.size()); }
    [[nodiscard]] const std::vector<TupanUnit>& units() const noexcept { return units_; }

    [[nodiscard]] std::vector<CycleResult> run_cycle(double hours, std::uint64_t seed = 0) {
        std::vector<CycleResult> out;
        out.reserve(units_.size());
        for (auto& u : units_) {
            u.output = u.model.calculate_output(hours, seed ? seed : next_rand(rng_state_));
            u.status = (u.output > 0.0) ? "producing" : "idle";
            out.push_back({u.id, u.output, u.status});
        }
        return out;
    }

    // Monte Carlo paralelo com std::jthread (RAII: join automático no destrutor).
    // Determinístico: cada thread usa RNG derivado do seed, p/ resultado estável.
    [[nodiscard]] MonteCarloStats monte_carlo(int runs, double hours, std::uint64_t seed = 42) const {
        if (runs <= 0) return {};
        const unsigned hw = std::max(1u, std::thread::hardware_concurrency());
        const int n_threads = static_cast<int>(std::min<long>(hw, runs));
        std::vector<std::vector<double>> chunks(static_cast<std::size_t>(n_threads));
        {
            std::vector<std::jthread> workers;
            workers.reserve(static_cast<std::size_t>(n_threads));
            for (int t = 0; t < n_threads; ++t) {
                workers.emplace_back([this, t, runs, hours, seed, n_threads, &chunks] {
                    const int per = runs / n_threads + (t < runs % n_threads ? 1 : 0);
                    auto& chunk = chunks[static_cast<std::size_t>(t)];
                    chunk.reserve(static_cast<std::size_t>(per));
                    std::uint64_t st = seed ^ (0x9E3779B97F4A7C15ULL * static_cast<std::uint64_t>(t + 1));
                    const auto& e = env();
                    for (int i = 0; i < per; ++i) {
                        const double noise_factor = 1.0 + (2.0 * uniform01(st) - 1.0) * kDefaultNoise;
                        chunk.push_back(theoretical_output(hours, e.relative_humidity, e.temperature,
                                                           e.fan_flow, e.efficiency,
                                                           e.coil_temperature) * noise_factor);
                    }
                });
            }
        } // jthreads fazem join aqui (RAII)
        std::vector<double> all;
        all.reserve(static_cast<std::size_t>(runs));
        for (const auto& c : chunks) all.insert(all.end(), c.begin(), c.end());
        std::sort(all.begin(), all.end());

        // Interpolação linear entre ordinais p/ percentis.
        auto quantile = [&](double q) -> double {
            if (all.empty()) return 0.0;
            const double idx = q * static_cast<double>(all.size() - 1);
            const std::size_t i = static_cast<std::size_t>(idx);
            const double frac = idx - static_cast<double>(i);
            return (i + 1 < all.size()) ? all[i] * (1.0 - frac) + all[i + 1] * frac : all[i];
        };

        MonteCarloStats s;
        s.mean = std::accumulate(all.begin(), all.end(), 0.0) /
                 static_cast<double>(std::max<std::size_t>(1, all.size()));
        s.p05 = quantile(0.05);
        s.p50 = quantile(0.50);
        s.p95 = quantile(0.95);
        return s;
    }

    [[nodiscard]] double predict_output(int id, double hours) const {
        const auto it = std::find_if(units_.begin(), units_.end(),
                                     [id](const TupanUnit& u) { return u.id == id; });
        if (it == units_.end()) return 0.0;
        const auto& e = env();
        return ml_->predict({e.relative_humidity, e.temperature, e.pressure,
                             e.fan_flow, e.efficiency, e.coil_temperature}) * hours;
    }

    void ml_accuracy(double& rmse, double& r2) const { ml_->accuracy(123ULL, 100, rmse, r2); }

private:
    Environment                  environment_;
    std::unique_ptr<MLPredictor> ml_;      // RAII / ponteiro dinâmico
    std::vector<TupanUnit>       units_;
    int                          next_id_ = 1;
    mutable std::uint64_t        rng_state_ = 20260911ULL;
};

} // namespace tupan

#endif // TUPAN_CORE_HPP
