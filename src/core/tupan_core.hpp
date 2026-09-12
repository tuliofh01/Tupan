#pragma once
// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Núcleo de simulação (header-only, C++23)
//  ---------------------------------------------------------------------------
//  ARQUITETURA DE MICROSSERVIÇOS (visão macro):
//    [nuvem/dados]  datasets HF → analise_dados.py (pandas/PyTorch) → CSV
//         ↓ dados curados (envelope operacional, coeficientes)
//    [núcleo nativo] tupan_core.hpp (este arquivo) — física+ML, zero deps
//         ↓ API C (header)            ↓ pybind (tupan_native)
//    [serviços]  tupan_sim CLI · tupan_gui Qt5 · Flask web · firmware FSM
//  Cada serviço consome o MESMO núcleo; dados fluem via CSV/JSON (contratos).
//
//  CICLO FÍSICO FINAL (sem compressor — decisão de projeto 2026-09):
//    NOITE  (SORÇÃO) : ventoinhas forçam ar noturno → leito CaCl₂ retém H₂O
//    AMANHECER       : servo-registro fecha a entrada de ar e abre o duto
//    DIA    (REGEN)  : solenoide aquece o sal úmido a 120 °C → vapor
//    DESTILAÇÃO      : vapor condensa na vidraria → destilado limpo
//    PÓS-TRATAMENTO  : filtro mineralizante (reposição Ca/Mg, perda ~2 %)
//                      + lâmpada UV-C 254 nm (esterilização, sem perda de água)
//    ARMAZENAMENTO   : bacia potável com torneira (2 L)
//  A produção depende de: água sorvida (kg), energia do aquecedor, eficiência
//  de destilação e perdas térmicas. Modelo: Balança-de-massa + bolha de Calder.
// ============================================================================
#ifndef TUPAN_CORE_HPP
#define TUPAN_CORE_HPP

#include <algorithm>
#include <array>
#include <charconv>   // std::from_chars — parse numérico sem locale/alocação
#include <cmath>
#include <concepts>
#include <cstdint>
#include <cstdio>
#include <cstdlib>    // std::getenv
#include <cstring>    // std::memcpy p/ binlog
#include <fstream>
#include <memory>
#include <numeric>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <vector>

namespace tupan {

// ---------------------------------------------------------------------------
// ALIASES DE TIPO — largura fixa garantida (cstdint) + intenção legível.
// ---------------------------------------------------------------------------
using Real   = double;         // grandeza física (7-8 dígitos, 8 B)
using Liters = Real;           // produção de água
using Watts  = Real;           // potência
using Joules = Real;           // energia
using Id     = std::int32_t;   // id de unidade (4 B fixos)
using Seed   = std::uint64_t;  // semente PRNG (8 B fixos)
using Weight = Real;           // peso do modelo de ML
using Hours  = Real;           // duração

// ---------------------------------------------------------------------------
// CONCEITO: restringe templates a tipos numéricos (erro claro em compile-time).
// ---------------------------------------------------------------------------
template <typename T>
concept Numeric = std::is_arithmetic_v<T>;

[[nodiscard]] inline constexpr Real clamp01(Numeric auto v) noexcept {
    return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : static_cast<Real>(v));
}

// ---------------------------------------------------------------------------
// CONSTANTES EXTERNAS (JSON flat, streaming — sem árvore em RAM).
// DIDÁTICA: em vez de montar uma árvore JSON inteira na memória (map/variant),
// varremos o arquivo uma única vez e "caspamos" os pares (grupo,chave) que
// nos interessam. O(n) em tempo, O(1) em memória extra.
// ---------------------------------------------------------------------------
struct Constants {
    // --- Psicrometria (Magnus) — usada na fase de SORÇÃO ---
    Real magnus_a  = 6.1094;
    Real magnus_b  = 17.625;
    Real magnus_c  = 243.04;
    Real rho_const = 216.7;
    Real kelvin    = 273.15;
    // --- Leito químico (CaCl₂) ---
    Real desiccant_mass_kg      = 2.0;    // massa de CaCl₂ anidro no leito
    Real sorption_capacity      = 1.0;    // kg H₂O / kg CaCl₂ (CaCl₂·4H₂O ≈ 1,0)
    Real sorption_kinetics_1h   = 0.55;   // fração de captação por hora (k)
    Real regen_temp_c           = 120.0;  // temperatura alvo da regeneração
    // --- Ruído estocástico (± fração em torno do determinístico) ---
    Real noise_default          = 0.05;
    // --- Aquecedor (bobina) ---
    Watts heater_watts          = 250.0;  // potência da bobina de aquecimento
    Real  heater_efficiency     = 0.90;   // fração que vira calor no leito
    // --- Destilação em vidraria ---
    Real  distillation_efficiency = 0.92; // fração de vapor que condensa limpo
    // --- Pós-tratamento (filtro mineralizante + UV-C) ---
    Real  mineral_filter_recovery = 0.98; // perda de purga do filtro (~2 %)
    Real  mineral_ca_mg_l         = 45.0; // Ca²⁺ reposto (mg/L — perfil "água mineral")
    Real  mineral_mg_mg_l         = 18.0; // Mg²⁺ reposto (mg/L)
    Watts uv_watts                = 6.0;  // lâmpada UV-C 254 nm (6 W, 30 min)
    Real  uv_dose_mj_cm2          = 40.0; // dose UV (mJ/cm²) — > 40 inativa 99,99 %
    // --- Bacia potável ---
    Real  basin_liters            = 2.0;  // capacidade da bacia com torneira
    // --- Energia ---
    Watts fans_watts            = 7.5;    // 3× 2,5 W (ventoinhas, sem compressor)
    Watts electronics_w         = 5.0;    // Mega + sensores + OLED
    Real  specific_heat_liquid  = 4.186;  // kJ/(kg·K) — água líquida
    Real  latent_heat_vap       = 2257.0; // kJ/kg — vaporização a 100 °C
    // --- ML (regressão grau 2) ---
    int  ml_train_samples = 500;
    Real ml_ridge         = 1e-9;
    Seed ml_seed_train    = 42;
    Seed ml_seed_test     = 123;
    int  ml_test_samples  = 100;
    // Treino/avaliação do ML.
    // Envelope operacional SEM pressão (x = {UR, T, vazão, η, T_aquecedor}):
    // a pressão não entra na física do ciclo, e features que não influenciam
    // o alvo só adicionam variância ao ajuste (leis de regulação estatística).
    std::array<Real, 5> env_lo{30.0, 15.0, 10.0, 0.5, 100.0};
    std::array<Real, 5> env_hi{95.0, 40.0, 40.0, 1.0, 160.0};
    // --- Monte Carlo ---
    Seed mc_seed_default = 42;
    int  mc_runs_default = 50000;
};

namespace detail {

// ---------------------------------------------------------------------------
// Mini-JSON FLAT (didático, O(n)/O(1)): procuramos padrões "grupo": { ... }
// e lemos pares chave: valor DENTRO do grupo, sem construir árvore.
// ---------------------------------------------------------------------------
[[nodiscard]] inline std::size_t find_key(std::string_view s, std::string_view key,
                                          std::size_t from) noexcept {
    std::size_t pos = from;
    while ((pos = s.find(key, pos)) != std::string_view::npos) {
        // Deve estar entre aspas e ser um campo (não substring de outro).
        const bool quoted_left = pos > 0 && s[pos - 1] == '"';
        const std::size_t close = pos + key.size();
        const bool quoted_right = close < s.size() && s[close] == '"';
        if (quoted_left && quoted_right) return pos;
        pos = close;
    }
    return std::string_view::npos;
}

// Extrai o número imediatamente após "chave": (com tolerância a espaços).
[[nodiscard]] inline bool extract_number(std::string_view s, std::string_view key,
                                         std::size_t from, Real& out) noexcept {
    const std::size_t k = find_key(s, key, from);
    if (k == std::string_view::npos) return false;
    std::size_t i = k + key.size() + 2; // pula fechamento " e :
    while (i < s.size() && (s[i] == ' ' || s[i] == '\t')) ++i;
    const auto [ptr, ec] = std::from_chars(s.data() + i, s.data() + s.size(), out);
    return ec == std::errc{} && ptr != s.data() + i;
}

// Extrai a PRIMEIRA string entre aspas após a chave (usada p/ schema).
[[nodiscard]] inline bool extract_string(std::string_view s, std::string_view key,
                                         std::size_t from, std::string& out) {
    const std::size_t k = find_key(s, key, from);
    if (k == std::string_view::npos) return false;
    std::size_t i = k + key.size() + 2;
    while (i < s.size() && s[i] == ' ') ++i;
    if (i >= s.size() || s[i] != '"') return false;
    ++i;
    out.clear();
    while (i < s.size() && s[i] != '"') out.push_back(s[i++]);
    return true;
}

// Bloco de um grupo: retorna {início,fim} do conteúdo entre chaves.
[[nodiscard]] inline bool group_block(std::string_view s, std::string_view group,
                                      std::size_t& begin, std::size_t& end) noexcept {
    const std::size_t g = find_key(s, group, 0);
    if (g == std::string_view::npos) return false;
    std::size_t i = g + group.size() + 2;
    while (i < s.size() && s[i] != '{') { if (s[i] == '}') return false; ++i; }
    if (i >= s.size()) return false;
    begin = ++i;                       // primeiro char após '{'
    int depth = 1;
    while (i < s.size() && depth > 0) {
        if (s[i] == '{') ++depth;
        else if (s[i] == '}') --depth;
        ++i;
    }
    end = (depth == 0) ? i - 1 : s.size();
    return true;
}

inline Constants& constants_mut() noexcept {
    static Constants g{};
    return g;
}

} // namespace detail

[[nodiscard]] inline const Constants& constants() noexcept { return detail::constants_mut(); }

// Carrega tupan_constants.json (flat). Falha ⇒ mantém defaults compilados.
inline bool load_constants(const std::string& path) {
    std::ifstream f(path);
    if (!f) return false;
    std::string src{(std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>()};
    // Schema mínimo: precisa ter ao menos um grupo conhecido.
    if (detail::find_key(src, "fisica", 0) == std::string_view::npos &&
        detail::find_key(src, "ml", 0) == std::string_view::npos) return false;

    auto& c = detail::constants_mut();
    auto num = [&](std::string_view g, std::string_view k, Real& target) {
        std::size_t b = 0, e = 0;
        if (detail::group_block(src, g, b, e))
            (void)detail::extract_number(src, k, b, target);  // ausente ⇒ mantém default
    };
    num("fisica", "magnus_a", c.magnus_a);
    num("fisica", "magnus_b", c.magnus_b);
    num("fisica", "magnus_c", c.magnus_c);
    num("fisica", "rho_const", c.rho_const);
    num("fisica", "kelvin", c.kelvin);
    num("quimico", "desiccant_mass_kg", c.desiccant_mass_kg);
    num("quimico", "sorption_capacity", c.sorption_capacity);
    num("quimico", "sorption_kinetics_1h", c.sorption_kinetics_1h);
    num("quimico", "regen_temp_c", c.regen_temp_c);
    num("aquecedor", "heater_watts", c.heater_watts);
    num("aquecedor", "heater_efficiency", c.heater_efficiency);
    num("destilacao", "distillation_efficiency", c.distillation_efficiency);
    num("pos_tratamento", "mineral_filter_recovery", c.mineral_filter_recovery);
    num("pos_tratamento", "mineral_ca_mg_l", c.mineral_ca_mg_l);
    num("pos_tratamento", "mineral_mg_mg_l", c.mineral_mg_mg_l);
    num("pos_tratamento", "uv_watts", c.uv_watts);
    num("pos_tratamento", "uv_dose_mj_cm2", c.uv_dose_mj_cm2);
    num("pos_tratamento", "basin_liters", c.basin_liters);
    num("energia", "fans_watts", c.fans_watts);
    num("energia", "potencia_eletronica_w", c.electronics_w);
    num("ml", "ridge_lambda", c.ml_ridge);
    {
        std::size_t b = 0, e = 0;
        if (detail::group_block(src, "ml", b, e)) {
            Real v = 0;
            if (detail::extract_number(src, "amostras_treino", b, v))
                c.ml_train_samples = static_cast<int>(v);
            if (detail::extract_number(src, "amostras_teste", b, v))
                c.ml_test_samples = static_cast<int>(v);
        }
    }
    return true;
}

// ---------------------------------------------------------------------------
// AMBIENTE — condições climáticas + parâmetros operacionais do NOVO ciclo.
// ---------------------------------------------------------------------------
struct Environment {
    Real relative_humidity  = 60.0;   // UR (%) — noite
    Real temperature        = 28.0;   // temperatura noturna (°C)
    Real pressure           = 1013.0; // hPa
    Real fan_flow           = 25.0;   // vazão total das ventoinhas (m³/h)
    Real efficiency         = 0.85;   // eficiência global do leito (0..1)
    Real heater_temp_c      = 120.0;  // temperatura do aquecedor (regeneração)
};

// ---------------------------------------------------------------------------
// FÍSICA DO CICLO — Fase 1: SORÇÃO noturna (kg de água retida no leito).
// Cinética de 1ª ordem: m(t) = M·q·(1 − e^(−k·t)), saturação M·q.
// Ar: ρ_v(T,UR) g/m³ → massa captada ≈ Δρ × vazão × t × η (limitada pela
// saturação do leito). Retorna kg de água retida após `hours`.
// ---------------------------------------------------------------------------
[[nodiscard]] inline Real saturation_vapor_density(Real temp_c) noexcept {
    const Constants& k = constants();
    const Real es = k.magnus_a * std::exp((k.magnus_b * temp_c) / (k.magnus_c + temp_c));
    return k.rho_const * es / (temp_c + k.kelvin);
}

[[nodiscard]] inline Real sorption_intake(Real hours, Real humidity, Real temperature,
                                          Real fan_flow, Real efficiency) noexcept {
    const Constants& k = constants();
    const Real rho_air  = (humidity / 100.0) * saturation_vapor_density(temperature); // g/m³
    const Real rho_dry  = saturation_vapor_density(20.0);  // saída do leito ≈ 20 °C/60 % (didático)
    const Real captured = std::max(Real{0}, rho_air - 0.60 * rho_dry)   // g/m³ removidos
                        * std::max(Real{0}, fan_flow * hours)           // m³
                        * clamp01(efficiency) / 1000.0;                 // → kg
    // Cinética de 1ª ordem + teto de saturação do leito (M·q).
    const Real saturated = k.desiccant_mass_kg * k.sorption_capacity;
    const Real kinetic   = saturated * (1.0 - std::exp(-k.sorption_kinetics_1h * hours));
    return std::min(captured, kinetic); // o que limita: ar ou leito
}

// ---------------------------------------------------------------------------
// FÍSICA DO CICLO — Fase 2: REGEN+DESTILAÇÃO diurna (litros potáveis).
// 1. Energia da bobina: E = P·t·η_aquecedor
// 2. Água liberável: m_regen = m_sorvida × fração liberada a T_aquecedor
//    (linear: fração = clamp01((T−80)/40) ⇒ 100 % a 120 °C)
// 3. Destilação: só parte do vapor condensa limpo (η_d)
// 4. Custo térmico: sensível (ΔT 25→100 °C) + latente (2257 kJ/kg)
// ---------------------------------------------------------------------------
[[nodiscard]] inline Liters distillation_output(Real hours, Real water_kg,
                                                Real heater_temp_c) noexcept {
    const Constants& k = constants();
    if (hours <= 0.0 || water_kg <= 0.0) return 0.0;

    const Real release_frac = clamp01((heater_temp_c - 80.0) / 40.0);
    const Real released_kg  = water_kg * release_frac;

    // Energia disponível (kJ) vs. energia necessária (kJ) p/ vaporizar tudo.
    const Real energy_kj = k.heater_watts * hours * 3.6 * k.heater_efficiency; // W·h → kJ
    const Real needed_kj = released_kg * (k.specific_heat_liquid * 75.0 + k.latent_heat_vap);
    // A energia limita: fator ≤ 1 (o leito inteiro não vaporiza sem energia).
    const Real energy_factor = (needed_kj > 0.0)
        ? std::min(Real{1}, energy_kj / needed_kj) : Real{0};
    return released_kg * energy_factor * k.distillation_efficiency; // kg ≈ L
}

// ---------------------------------------------------------------------------
// FÍSICA DO CICLO — Fase 3: PÓS-TRATAMENTO (filtro mineralizante + UV-C).
// DIDÁTICA (modelo):
//   • Filtro mineralizante: acrescenta sais (Ca²⁺/Mg²⁺) ao destilado "agéutico"
//     e tem PERDA de purga (~2 %) — modelada como recuperação 0,98;
//   • UV-C: esterilização DOSMOLÓGICA — dose D = P_uv·t/(área·fluxo). Como o
//     destilado já é destilado (esterilidade parcial), a UV é barreira de
//     segurança e NÃO remove água: custo só de energia (W·min).
//   • Bacia: o que não cabe (2 L) fica no ciclo seguinte (não é perda física —
//     é limite de armazenamento reportado).
// ---------------------------------------------------------------------------
struct PostTreatment {
    Liters  water_l      = 0.0;   // L potáveis que chegam à bacia
    Real    ca_mg_l      = 0.0;   // Ca²⁺ no produto final (mg/L)
    Real    mg_mg_l      = 0.0;   // Mg²⁺ no produto final (mg/L)
    Joules  uv_energy_j  = 0.0;   // energia da UV-C no ciclo
    bool    basin_full   = false; // bacia atingiu a capacidade
};

[[nodiscard]] inline PostTreatment post_treatment(Liters distilled_l) noexcept {
    const Constants& k = constants();
    PostTreatment p;
    if (distilled_l <= 0.0) return p;

    // 1) Filtro mineralizante (recuperação 0,98: perda de purga).
    const Real filtrada = distilled_l * k.mineral_filter_recovery;

    // 2) UV-C: sem perda de água; energia da lâmpada por 30 min (dose segura).
    p.uv_energy_j = k.uv_watts * 1800.0; // 30 min em joules

    // 3) Bacia com torneira (capacidade limita o armazenamento reportado).
    p.water_l    = std::min(filtrada, k.basin_liters);
    p.basin_full = filtrada > k.basin_liters;
    p.ca_mg_l    = k.mineral_ca_mg_l;   // perfil de mineralização fixo (ANVISA)
    p.mg_mg_l    = k.mineral_mg_mg_l;
    return p;
}

// ---------------------------------------------------------------------------
// RESULTADO DE UM CICLO COMPLETO (noite+dia+pós) — didático e auditável.
// ---------------------------------------------------------------------------
struct CycleBreakdown {
    Real  water_kg_sorbed  = 0.0; // kg retidos na noite
    Liters distilled_l     = 0.0; // L destilados na vidraria (dia)
    Liters potable_l       = 0.0; // L POTÁVEIS na bacia (após filtro+UV)
    Real  ca_mg_l          = 0.0; // mineralização final (Ca²⁺ mg/L)
    Real  mg_mg_l          = 0.0; // mineralização final (Mg²⁺ mg/L)
    Joules energy_kj_total = 0.0; // energia total (fans + solenoide + UV)
    Real  liters_per_kwh   = 0.0; // eficiência energética (L/kWh — potável!)
    bool  basin_full       = false;
};

// Executa um ciclo completo: `night_hours` de sorção + `day_hours` de regen.
[[nodiscard]] inline CycleBreakdown full_cycle(Real night_hours, Real day_hours,
                                               Real humidity, Real temperature,
                                               Real fan_flow, Real efficiency,
                                               Real heater_temp_c) noexcept {
    const Constants& k = constants();
    CycleBreakdown cb;
    cb.water_kg_sorbed = sorption_intake(night_hours, humidity, temperature,
                                         fan_flow, efficiency);
    cb.distilled_l     = distillation_output(day_hours, cb.water_kg_sorbed, heater_temp_c);
    const auto p       = post_treatment(cb.distilled_l);
    cb.potable_l       = p.water_l;
    cb.ca_mg_l         = p.ca_mg_l;
    cb.mg_mg_l         = p.mg_mg_l;
    cb.basin_full      = p.basin_full;
    cb.energy_kj_total = (k.fans_watts * night_hours + k.heater_watts * day_hours) * 3600.0
                       + p.uv_energy_j;
    const Real kwh     = cb.energy_kj_total / 3.6e6;
    cb.liters_per_kwh  = (kwh > 0.0) ? cb.potable_l / kwh : 0.0;
    return cb;
}

// ---------------------------------------------------------------------------
// PRNG determinístico (xorshift64*) — mesmo seed ⇒ mesma saída.
// ---------------------------------------------------------------------------
[[nodiscard]] inline Seed next_rand(Seed& state) noexcept {
    state ^= state >> 12; state ^= state << 25; state ^= state >> 27;
    return state * 0x2545F4914F6CDD1DULL;
}
[[nodiscard]] inline Real uniform01(Seed& state) noexcept {
    return static_cast<Real>(next_rand(state) >> 11) / 9007199254740992.0;
}

// ---------------------------------------------------------------------------
// TUPAN MODEL — dispositivo estocástico do novo ciclo.
// ---------------------------------------------------------------------------
struct TupanModel {
    Environment params;
    Real noise = 0.05;

    // Produção estocástica: distilação com ruído multiplicative ±noise.
    [[nodiscard]] Liters calculate_output(Real night_hours, Real day_hours, Seed seed) const {
        const Real u = uniform01(seed);
        const Real noise_factor = 1.0 + (2.0 * u - 1.0) * noise;
        const auto cb = full_cycle(night_hours, day_hours, params.relative_humidity,
                                   params.temperature, params.fan_flow, params.efficiency,
                                   params.heater_temp_c);
        return std::max(Real{0}, cb.distilled_l * noise_factor);
    }
};

// ---------------------------------------------------------------------------
// ML PREDICTOR — regressão grau 2 sobre x = {UR, T, vazão, η, T_aquecedor}.
// 5 variáveis → 5 lineares + 10 cruzados + 5 quadráticos = 20 features.
// Treino EM STREAMING (XᵀX/Xᵀy acumulados — sem dataset em RAM).
// ---------------------------------------------------------------------------
class MLPredictor {
public:
    // 20 polinomiais + 3 de engenharia (kinks) = 23 features.
    static constexpr std::size_t kFeatures = 23;
    static constexpr std::size_t kDim      = 24; // + bias

    explicit MLPredictor(const Constants& k = constants()) { train(k); }

    [[nodiscard]] Weight predict(const std::array<Real, 5>& x) const noexcept {
        const auto phi = features(x);
        const Weight* const w = w_.data();
        Real acc = w[kFeatures];
        for (std::size_t j = 0; j < kFeatures; ++j) acc += w[j] * phi[j];
        return acc;
    }

    void accuracy(Seed seed, int n, Real& rmse, Real& r2) const {
        const Constants& k = constants();
        std::vector<Real> ys(static_cast<std::size_t>(n)), ps(ys.size());
        Real mean = 0.0;
        Seed st = seed;
        for (int i = 0; i < n; ++i) {
            std::array<Real, 5> x{};
            for (std::size_t j = 0; j < 5; ++j)
                x[j] = k.env_lo[j] + uniform01(st) * (k.env_hi[j] - k.env_lo[j]);
            const std::size_t iu = static_cast<std::size_t>(i);
            // Alvo físico do novo ciclo: 8 h noite + 6 h dia (padrão de projeto).
            ys[iu] = full_cycle(8.0, 6.0, x[0], x[1], x[2], x[3], x[4]).distilled_l;
            ps[iu] = predict(x);
            mean += ys[iu];
        }
        mean /= static_cast<Real>(n);
        Real sse = 0.0, sst = 0.0;
        for (std::size_t i = 0; i < ys.size(); ++i) {
            sse += (ys[i] - ps[i]) * (ys[i] - ps[i]);
            sst += (ys[i] - mean) * (ys[i] - mean);
        }
        rmse = std::sqrt(sse / static_cast<Real>(n));
        r2   = (sst > 0.0) ? 1.0 - sse / sst : 1.0;
    }

private:
    // ---------------------------------------------------------------------------
    // FEATURES ENRIQUECIDAS (didático) — além do mapa polinomial grau 2,
    // adicionamos 3 features de ENGENHARIA que dão ao regressor a estrutura
    // dos cortes (kinks) da física:
    //   • f_ur  = UR/100 · ρ_v(T)              → conteúdo de vapor do ar (g/m³)
    //   • f_sat = carga no leito / saturação   → proximidade do teto M·q
    //   • f_lib = clamp01((T_aquec−80)/40)     → fração liberável na regeneração
    // Com elas, o grau 2 passa a reproduzir zeros (secos/saturados) e a
    // saturação sem precisar de grau alto — menos pesos, mais generalização.
    // ---------------------------------------------------------------------------
    [[nodiscard]] static std::array<Weight, kFeatures> features(const std::array<Real, 5>& x) noexcept {
        static_assert(kFeatures == 23, "features: 20 polinomiais + 3 de engenharia");
        std::array<Weight, kFeatures> f{};
        std::size_t t = 0;
        for (std::size_t i = 0; i < 5; ++i) f[t++] = x[i];
        for (std::size_t i = 0; i < 5; ++i)
            for (std::size_t j = i + 1; j < 5; ++j) f[t++] = x[i] * x[j];
        for (std::size_t i = 0; i < 5; ++i) f[t++] = x[i] * x[i];
        // features de engenharia (normalizadas p/ mesma ordem de grandeza)
        const Real f_ur  = (x[0] / 100.0) * saturation_vapor_density(x[1]) / 30.0;
        const Real carga = sorption_intake(8.0, x[0], x[1], x[2], x[3]); // kg no leito
        const Real sat   = constants().desiccant_mass_kg * constants().sorption_capacity;
        const Real f_sat = carga / std::max(sat, Real{1e-9});
        const Real f_lib = clamp01((x[4] - 80.0) / 40.0);
        f[t++] = f_ur;
        f[t++] = f_sat;
        f[t++] = f_lib;
        return f;
    }

    void train(const Constants& k) {
        std::array<std::array<Real, kDim>, kDim> M{}; // XᵀX (3,5 KB na stack)
        std::array<Real, kDim> b{};                   // Xᵀy
        const int N = k.ml_train_samples;
        Seed st = k.ml_seed_train;
        std::array<Real, 5> x{};
        std::array<Real, kDim> a{};
        for (int n = 0; n < N; ++n) {
            for (std::size_t j = 0; j < 5; ++j)
                x[j] = k.env_lo[j] + uniform01(st) * (k.env_hi[j] - k.env_lo[j]);
            const auto phi = features(x);
            for (std::size_t j = 0; j < kFeatures; ++j) a[j] = phi[j];
            a[kFeatures] = 1.0;
            const Real y = full_cycle(8.0, 6.0, x[0], x[1], x[2], x[3], x[4]).distilled_l;
            for (std::size_t i = 0; i < kDim; ++i) {
                const Real ai = a[i];
                b[i] += ai * y;
                for (std::size_t j = 0; j < kDim; ++j) M[i][j] += ai * a[j];
            }
        }
        for (std::size_t i = 0; i < kDim; ++i) M[i][i] += k.ml_ridge;
        for (std::size_t col = 0; col < kDim; ++col) {
            std::size_t piv = col;
            for (std::size_t r = col + 1; r < kDim; ++r)
                if (std::abs(M[r][col]) > std::abs(M[piv][col])) piv = r;
            std::swap(M[col], M[piv]);
            std::swap(b[col], b[piv]);
            const Real d = M[col][col];
            for (std::size_t r = col + 1; r < kDim; ++r) {
                const Real f = M[r][col] / d;
                if (f == 0.0) continue;
                for (std::size_t c = col; c < kDim; ++c) M[r][c] -= f * M[col][c];
                b[r] -= f * b[col];
            }
        }
        for (std::size_t r = kDim; r-- > 0;) {
            Real s = b[r];
            for (std::size_t c = r + 1; c < kDim; ++c) s -= M[r][c] * w_[c];
            w_[r] = s / M[r][r];
        }
    }

    std::array<Weight, kDim> w_{};
};

// ---------------------------------------------------------------------------
// BINLOG — log binário append-only p/ rotinas e erros não-críticos.
// Formato por registro: [u32 magic][u8 level][u8 tag_len][tag][u32 ms][u16 len][payload]
// DIDÁTICA: binário = menor e mais rápido que texto; ferramenta tupan_log.py
// converte p/ texto. "Não-crítico" = nada disso trava o fluxo de produção.
// ---------------------------------------------------------------------------
enum class LogLevel : std::uint8_t { INFO = 0, WARN = 1, ERROR = 2, ROUTINE = 3 };

class BinLogger {
public:
    explicit BinLogger(std::string path) : path_(std::move(path)) {}
    // Abre append; cria se não existir. RAII: fecha no destrutor.
    bool open() {
        f_.open(path_, std::ios::binary | std::ios::app);
        return f_.good();
    }
    void log(LogLevel lv, std::string_view tag, std::string_view msg, std::uint32_t ms = 0) {
        if (!f_.is_open()) return;
        const std::uint32_t magic = 0x54504E31; // "TN01" — Tupan Native v1
        const std::uint8_t tag_len = static_cast<std::uint8_t>(std::min<std::size_t>(tag.size(), 255));
        const std::uint16_t len = static_cast<std::uint16_t>(std::min<std::size_t>(msg.size(), 65535));
        f_.write(reinterpret_cast<const char*>(&magic), 4);
        f_.write(reinterpret_cast<const char*>(&lv), 1);
        f_.write(reinterpret_cast<const char*>(&tag_len), 1);
        f_.write(tag.data(), tag_len);
        f_.write(reinterpret_cast<const char*>(&ms), 4);
        f_.write(reinterpret_cast<const char*>(&len), 2);
        f_.write(msg.data(), len);
        f_.flush(); // rotinas curtas: flush por registro (durabilidade simples)
    }
    ~BinLogger() = default;

private:
    std::string path_;
    std::ofstream f_;
};

// ---------------------------------------------------------------------------
// FROTA — unidade Tupan registrada no simulador.
// ---------------------------------------------------------------------------
struct TupanUnit {
    Id          id     = 0;
    TupanModel  model{};
    Liters      output = 0.0;
    std::string status = "online";
};

// Estatísticas de Monte Carlo (litros).
struct MonteCarloStats {
    Liters mean = 0.0;
    Liters p05  = 0.0;
    Liters p50  = 0.0;
    Liters p95  = 0.0;
};

// ---------------------------------------------------------------------------
// SIMULATOR — frota + ciclos + Monte Carlo paralelo + binlog opcional.
// ---------------------------------------------------------------------------
class Simulator {
public:
    struct CycleResult {
        Id          tupan_id = 0;
        Liters      output_liters = 0.0;
        std::string status;
    };

    Simulator() : ml_(std::make_unique<MLPredictor>()) {
        // Tenta carregar constantes JSON (silencioso se ausente).
        if (const char* p = std::getenv("TUPAN_CONSTANTS")) load_constants(p);
    }

    // Contas ambientais: L/kWh do ciclo padrão (8 h noite + 6 h dia).
    [[nodiscard]] static Real liters_per_kwh_default() noexcept {
        return full_cycle(8.0, 6.0, 65.0, 24.0, 25.0, 0.85, 120.0).liters_per_kwh;
    }

    Environment&                    env()       noexcept { return environment_; }
    [[nodiscard]] const Environment& env() const noexcept { return environment_; }

    Id add_tupan() {
        TupanUnit u;
        u.id = next_id_++;
        units_.push_back(u);
        return u.id;
    }

    void remove_tupan(Id id) {
        std::erase_if(units_, [id](const TupanUnit& u) { return u.id == id; });
    }

    [[nodiscard]] int count() const noexcept { return static_cast<int>(units_.size()); }
    [[nodiscard]] const std::vector<TupanUnit>& units() const noexcept { return units_; }

    [[nodiscard]] std::vector<CycleResult> run_cycle(Real night_hours, Real day_hours, Seed seed = 0) {
        std::vector<CycleResult> out;
        out.reserve(units_.size());
        for (auto& u : units_) {
            u.output = u.model.calculate_output(night_hours, day_hours,
                                                seed ? seed : next_rand(rng_state_));
            u.status = (u.output > 0.0) ? "producing" : "idle";
            out.push_back({u.id, u.output, u.status});
        }
        return out;
    }

    // Monte Carlo paralelo: buffer único, faixas disjuntas, jthread (RAII).
    [[nodiscard]] MonteCarloStats monte_carlo(int runs, Real night_hours, Real day_hours, Seed seed = 0) const {
        if (runs <= 0) return {};
        const Constants& k = constants();
        if (seed == 0) seed = k.mc_seed_default;

        std::vector<Liters> all(static_cast<std::size_t>(runs));
        const unsigned hw = std::max(1u, std::thread::hardware_concurrency());
        const int n_threads = static_cast<int>(std::min<long>(hw, runs));

        const Real rh = environment_.relative_humidity;   // locals const → registradores
        const Real tp = environment_.temperature;
        const Real fl = environment_.fan_flow;
        const Real ef = environment_.efficiency;
        const Real ht = environment_.heater_temp_c;
        const Real noise = k.noise_default;

        {
            std::vector<std::jthread> workers;
            workers.reserve(static_cast<std::size_t>(n_threads));
            for (int t = 0; t < n_threads; ++t) {
                const std::size_t begin = static_cast<std::size_t>(t) * all.size() / static_cast<std::size_t>(n_threads);
                const std::size_t end   = static_cast<std::size_t>(t + 1) * all.size() / static_cast<std::size_t>(n_threads);
                workers.emplace_back([begin, end, night_hours, day_hours, seed, t,
                                      rh, tp, fl, ef, ht, noise, &all] {
                    Seed st = seed ^ (0x9E3779B97F4A7C15ULL * static_cast<Seed>(t + 1));
                    for (std::size_t i = begin; i < end; ++i) {
                        const Real nf = 1.0 + (2.0 * uniform01(st) - 1.0) * noise;
                        all[i] = distillation_output(day_hours,
                                 sorption_intake(night_hours, rh, tp, fl, ef), ht) * nf;
                    }
                });
            }
        }
        std::sort(all.begin(), all.end());
        auto quantile = [&all](Real q) -> Real {
            const Real idx = q * static_cast<Real>(all.size() - 1);
            const std::size_t i = static_cast<std::size_t>(idx);
            const Real frac = idx - static_cast<Real>(i);
            return (i + 1 < all.size()) ? all[i] * (1.0 - frac) + all[i + 1] * frac : all[i];
        };

        MonteCarloStats s;
        s.mean = std::accumulate(all.begin(), all.end(), Real{0}) / static_cast<Real>(all.size());
        s.p05 = quantile(0.05);
        s.p50 = quantile(0.50);
        s.p95 = quantile(0.95);
        return s;
    }

    [[nodiscard]] Liters predict_output(Id id, Real night_hours, Real day_hours) const {
        const auto it = std::find_if(units_.begin(), units_.end(),
                                     [id](const TupanUnit& u) { return u.id == id; });
        if (it == units_.end()) return 0.0;
        const auto& e = env();
        // Features: {UR, T, vazão, η, T_aquecedor} — a pressão não participa.
        const Liters por_ciclo = ml_->predict({e.relative_humidity, e.temperature,
                                               e.fan_flow, e.efficiency,
                                               e.heater_temp_c});
        // O ML aprende o ciclo padrão (8 h + 6 h); escala p/ janela pedida.
        return por_ciclo * (night_hours + day_hours) / 14.0;
    }

    void ml_accuracy(Real& rmse, Real& r2) const {
        const auto& k = constants();
        ml_->accuracy(k.ml_seed_test, k.ml_test_samples, rmse, r2);
    }

    // Binlog opcional (não-crítico): rotinas e erros sem travar o fluxo.
    void attach_logger(std::string path) {
        logger_ = std::make_unique<BinLogger>(std::move(path));
        logger_->open();
    }
    void blog(LogLevel lv, std::string_view tag, std::string_view msg) {
        if (logger_) logger_->log(lv, tag, msg);
    }

private:
    Environment                  environment_{};
    std::unique_ptr<MLPredictor> ml_;
    std::vector<TupanUnit>       units_{};
    Id                           next_id_ = 1;
    mutable Seed                 rng_state_ = 20260911ULL;
    std::unique_ptr<BinLogger>   logger_;     // opcional, não-crítico
};

} // namespace tupan

#endif // TUPAN_CORE_HPP
