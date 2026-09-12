// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Firmware MVC para Arduino Mega (C++20)
//  ---------------------------------------------------------------------------
//  DIDÁTICA (padrão MVC embarcado):
//    • MODEL   = dados do mundo físico: sensores, leito, reservatório, estado;
//    • VIEW    = apresentação: OLED, LEDs semáforo, painel LED+botões, Serial;
//    • CONTROLLER = máquina de estados finita (FSM) + regras + atuadores.
//  A FSM segue o ciclo REAL do projeto (sem compressor):
//    INTAKE  → ventoinhas puxam ar pela noite; leito CaCl₂ sorve água;
//    REGEN   → bobina aquece o leito a 120 °C; água é liberada como vapor;
//    DESTIL  → vapor condensa na vidraria; reservatório enche (mL reais).
//  LOG_* no console da Arduino IDE (Serial, 115200) para depurar quando você
//  começar a mexer: cada transição/leitura tem log com nível, tag e valor.
//
//  MEMÓRIA (otimização p/ ATmega2560, 8 KB SRAM):
//    • NENHUMA String dinâmica — tudo com F() (PROGMEM) e buffers fixos;
//    • tipos de largura fixa (cstdint): uint8_t/uint16_t/uint32_t/float;
//    • enum class : uint8_t (1 byte por estado); structs agregadas contíguas;
//    • stubs de sensores ISOLADOS: plugue os seus e o resto não muda.
// ============================================================================
#pragma once
#include <Arduino.h>

#include <cstdint>

namespace tupan {

// ===========================================================================
// 1) PINAGEM (única fonte de verdade — confere com o esquemático elétrico/CAD)
// ===========================================================================
enum Pin : uint8_t {
    // Sensores
    PIN_DHT22         = 2,    // DHT22: UR + T do ar (noite)
    PIN_DS18B20_LEITO = 3,    // DS18B20 no leito químico (OneWire)
    PIN_DS18B20_VAPOR = 4,    // DS18B20 no duto de vapor (opcional)
    PIN_NIVEL         = A0,   // sensor de nível capacitivo (0–5 V ⇒ 0–2 L)
    // Atuadores
    PIN_FAN_PWM       = 5,    // MOSFET: ventoinhas (PWM — vazão)
    PIN_AQUECEDOR     = 6,    // Relé/MOSFET: bobina do leito (ON/OFF + histerese)
    PIN_SERVO_DAMPER  = 9,    // servo: registro de ar (sorção↔regeneração)
    // HMI (painel LED + botões seta/select + semáforo)
    PIN_BTN_CIMA      = A2,   // painel de navegação (seta)
    PIN_BTN_BAIXO     = A3,
    PIN_BTN_SELECT    = A4,
    PIN_LED_VERDE     = 22,   // semáforo: verde = produzindo (destil)
    PIN_LED_AMARELO   = 23,   // amarelo = ocioso/intake (noite)
    PIN_LED_VERMELHO  = 24,   // vermelho = erro/reservatório cheio
};

// ===========================================================================
// 2) MODEL — dados e estado (sem lógica de controle)
// ===========================================================================
enum class Estado : uint8_t {      // FSM — 1 byte por estado
    OCIOSO = 0,                    // aguardando noite/botão
    INTAKE = 1,                    // sorção noturna (ventoinhas)
    REGEN  = 2,                    // aquecimento do leito (bobina)
    DESTIL = 3,                    // destilação (vapor → vidraria → tanque)
    CHEIO  = 4,                    // reservatório em 2 L
    ERRO   = 5,                    // sensor ausente / superaquecimento
};

struct Ambiente {                  // leituras físicas do ar
    float ur_pct;                  // umidade relativa (%)
    float temp_c;                  // temperatura (°C)
};

struct Leito {                     // leito químico (CaCl₂)
    float temp_c;                  // DS18B20 no leito
    float kg_agua;                 // água sorvida (estimada pela FSM)
    float kg_max;                  // saturação (2,0 kg padrão)
};

struct Reservatorio {
    uint16_t ml;                   // 0..2000 mL
    uint16_t ml_max;               // capacidade
};

// AGREGADO MODEL — um único objeto global (SRAM contígua, sem heap).
struct Model {
    Ambiente     ar{};
    Leito        leito{20.0f, 0.0f, 2.0f};
    Reservatorio tanque{0u, 2000u};
    Estado       estado{Estado::OCIOSO};
    uint32_t     t_estado_ms{0u};           // millis() ao entrar no estado atual
    uint32_t     ciclos{0u};
    float        litros_total{0.0f};        // contabilidade ambiental (auditoria)
    // config ajustável pela HMI (persistir em EEPROM — stub abaixo)
    float        alvo_regen_c{120.0f};
    uint32_t     min_intake_ms{3600ul * 8u}; // 8 h padrão (reduzir p/ testes)
    uint32_t     max_regen_ms{3600ul * 6u};  // 6 h padrão
};

// ===========================================================================
// 3) VIEW — console (LOG_*), semáforo, OLED (stub)
// ===========================================================================
namespace view {

// ---- Console: níveis leves, tag + valor — zero alocação -------------------
enum class LogNivel : uint8_t { INFO = 0, WARN = 1, ERRO = 2, CICLO = 3 };

inline void prefixo(LogNivel n) {
    Serial.print(F("["));
    switch (n) {
        case LogNivel::INFO:  Serial.print(F("INFO ")); break;
        case LogNivel::WARN:  Serial.print(F("WARN ")); break;
        case LogNivel::ERRO:  Serial.print(F("ERRO ")); break;
        case LogNivel::CICLO: Serial.print(F("CICLO")); break;
    }
    Serial.print(F("] "));
}

// Msg como FSH (F("...")) — caminho principal, tudo em PROGMEM.
inline void log(LogNivel n, const __FlashStringHelper* tag,
                const __FlashStringHelper* msg) {
    prefixo(n);
    Serial.print(tag);
    Serial.print(F(": "));
    Serial.println(msg);
}

// Msg como literal C simples (const char*) — sobrecarga p/ textos em RAM.
inline void log(LogNivel n, const __FlashStringHelper* tag, const char* msg) {
    prefixo(n);
    Serial.print(tag);
    Serial.print(F(": "));
    Serial.println(msg);
}

// Valor float — DIDÁTICA: Serial.print(float) já formata; sem snprintf/heap.
inline void logf(LogNivel n, const __FlashStringHelper* tag,
                 const __FlashStringHelper* rot, float v) {
    prefixo(n);
    Serial.print(tag);
    Serial.print(F(": "));
    Serial.print(rot);
    Serial.print(F("="));
    Serial.println(v, 3);
}

// Valor inteiro sem sinal (ms, ciclos, mL).
inline void logu(LogNivel n, const __FlashStringHelper* tag,
                 const __FlashStringHelper* rot, uint32_t v) {
    prefixo(n);
    Serial.print(tag);
    Serial.print(F(": "));
    Serial.print(rot);
    Serial.print(F("="));
    Serial.println(v);
}

// ---- Semáforo: verde=produzindo · amarelo=noite/ocioso · vermelho=alerta ---
inline void semaforo(Estado e) {
    digitalWrite(PIN_LED_VERDE,    e == Estado::DESTIL ? HIGH : LOW);
    digitalWrite(PIN_LED_AMARELO,
                 (e == Estado::INTAKE || e == Estado::OCIOSO) ? HIGH : LOW);
    digitalWrite(PIN_LED_VERMELHO,
                 (e == Estado::ERRO || e == Estado::CHEIO) ? HIGH : LOW);
}

// ---- OLED SSD1306 I²C: stub claro p/ U8g2 (plugue o seu driver) ------------
inline void oled_init() { /* TODO: u8g2.begin() */ }
inline void oled_estado(Estado e) { (void)e; /* TODO: estado + mL */ }
inline void oled_medidas(const Model& m) { (void)m; /* TODO: UR/T/leito/nível */ }

} // namespace view

// ===========================================================================
// 4) DRIVERS/STUBS — SENSORES E ATUADORES (plugue os seus aqui)
// ===========================================================================
namespace driver {

// ---- DHT22 (UR + T): STUB determinístico; troque por DHT.h -----------------
//   Plugar: DHT dht(PIN_DHT22, DHT22);
//           ar.ur_pct = dht.readHumidity(); ar.temp_c = dht.readTemperature();
//   return false = sensor desconectado ⇒ FSM vai p/ ERRO (seguro).
inline bool dht22_ler(Ambiente& ar) {
    ar.ur_pct = 68.0f;   // STUB: valores noturnos plausíveis (Petrolina, 20h–6h)
    ar.temp_c = 24.0f;
    return true;
}

// ---- DS18B20 (OneWire): STUB; troque por OneWire + DallasTemperature -------
inline bool ds18b20_ler(uint8_t /*pino*/, float& temp_c) {
    temp_c = 22.0f;      // STUB
    return true;
}

// ---- Nível capacitivo (0–5 V ⇒ 0..ml_max mL) — STUB proporcional ----------
inline uint16_t nivel_ler_ml(uint16_t ml_max) {
    const uint16_t adc = analogRead(PIN_NIVEL);   // 0..1023
    return static_cast<uint16_t>((static_cast<uint32_t>(adc) * ml_max) / 1023u);
}

// ---- Ventoinhas (PWM 0–255 via MOSFET) --------------------------------------
inline void fans_pwm(uint8_t duty) { analogWrite(PIN_FAN_PWM, duty); }

// ---- Aquecedor (relé/MOSFET ON/OFF — a histerese fica na FSM) --------------
inline void aquecedor(bool on) { digitalWrite(PIN_AQUECEDOR, on ? HIGH : LOW); }

// ---- Servo do registro de ar (damper) — STUB; plugue Servo.h ---------------
//   0° = ar novo do ambiente (sorção) · 90° = recirculação (regeneração)
inline void damper_angulo(uint8_t graus) { (void)graus; }

} // namespace driver

// ===========================================================================
// 5) CONTROLLER — FSM + regras (o coração do firmware)
// ===========================================================================
namespace controller {

// Parâmetros de controle (constexpr: sem custo em RAM).
constexpr float HISTERESE_C = 2.0f;    // janela do termostato do leito
constexpr uint32_t LOG_MS   = 5000u;   // cadência do log de rotina
constexpr float ML_POR_H    = 120.0f;  // taxa nominal de destilação (mL/h)

// Contexto global único (Meyer's singleton: inicialização thread-safe, sem heap).
inline Model& modelo() {
    static Model m{};
    return m;
}

// Transição FSM com log — toda mudança de estado é auditável no console.
inline void transicao(Estado novo) {
    static const __FlashStringHelper* const nome[] = {
        F("OCIOSO"), F("INTAKE"), F("REGEN"), F("DESTIL"), F("CHEIO"), F("ERRO") };
    Model& m = modelo();
    view::log(view::LogNivel::CICLO, F("fsm"), nome[static_cast<uint8_t>(novo)]);
    m.estado = novo;
    m.t_estado_ms = millis();
    view::semaforo(novo);
    view::oled_estado(novo);
}

// Entradas digitais da HMI (pull-up interno: botão pressionado = LOW).
inline bool botao(uint8_t pino) { return digitalRead(pino) == LOW; }

// ---- PASSOS por estado ------------------------------------------------------

// OCIOSO: espera botão SELECT (no futuro: relógio noturno automático).
inline void passo_ocioso() {
    driver::fans_pwm(0);
    driver::aquecedor(false);
}

// INTAKE (sorção noturna): ventoinhas em vazão máxima, leito captura água.
// DIDÁTICA: cinética de 1ª ordem dm/dt = k·(M·q − m) — k = 0,55/h (calibrado
// pela esteira de dados: UR noturna média 68,6 % @ 24,6 °C em Petrolina-PE).
inline void passo_intake() {
    Model& m = modelo();
    static uint32_t t_log = 0;

    driver::damper_angulo(0);       // ar novo do ambiente
    driver::aquecedor(false);       // frio: sorção é exotérmica
    driver::fans_pwm(255);          // vazão máxima

    if (millis() - t_log >= LOG_MS) {
        t_log = millis();
        Ambiente a{};
        if (!driver::dht22_ler(a)) { transicao(Estado::ERRO); return; }
        m.ar = a;
        const float k_ms = 0.55f / 3600000.0f;      // h⁻¹ → ms⁻¹
        m.leito.kg_agua += (m.leito.kg_max - m.leito.kg_agua) * k_ms * LOG_MS;
        view::logf(view::LogNivel::INFO, F("sorcao"), F("kg"), m.leito.kg_agua);
        view::logf(view::LogNivel::INFO, F("ar"), F("ur"), m.ar.ur_pct);
    }
}

// REGEN (aquecimento): termostato com histerese ±2 °C protege o relé/MOSFET.
inline void passo_regen() {
    Model& m = modelo();
    static uint32_t t_log = 0;

    driver::damper_angulo(90);      // recirculação interna
    driver::fans_pwm(180);          // circula vapor devagar

    float t_leito = 0.0f;
    if (!driver::ds18b20_ler(PIN_DS18B20_LEITO, t_leito)) {
        transicao(Estado::ERRO);
        return;
    }
    m.leito.temp_c = t_leito;

    if (m.leito.temp_c < (m.alvo_regen_c - HISTERESE_C)) {
        driver::aquecedor(true);
    } else if (m.leito.temp_c > (m.alvo_regen_c + HISTERESE_C)) {
        driver::aquecedor(false);
    }

    if (millis() - t_log >= LOG_MS) {
        t_log = millis();
        view::logf(view::LogNivel::INFO, F("regen"), F("t_leito"), m.leito.temp_c);
        view::logf(view::LogNivel::INFO, F("regen"), F("kg_agua"), m.leito.kg_agua);
    }
}

// DESTIL: vapor → vidraria → condensação → tanque (mL reais, auditável).
inline void passo_destil() {
    Model& m = modelo();
    static uint32_t t_log = 0;
    static uint32_t t_ultimo = 0;

    const uint32_t agora = millis();
    if (agora > t_ultimo) {
        const float dt_h = static_cast<float>(agora - t_ultimo) / 3600000.0f;
        const float ml = ML_POR_H * dt_h;
        m.tanque.ml += static_cast<uint16_t>(ml);
        m.litros_total += ml / 1000.0f;
        t_ultimo = agora;
    }
    if (agora - t_log >= LOG_MS) {
        t_log = agora;
        view::logf(view::LogNivel::CICLO, F("destil"), F("ml"),
                   static_cast<float>(m.tanque.ml));
        view::logu(view::LogNivel::CICLO, F("destil"), F("ciclos"), m.ciclos);
        view::oled_medidas(m);
    }
}

// ---- FSM: tabela de transições explícita (a máquina inteira num switch) -----
inline void atualizar() {
    Model& m = modelo();
    const uint32_t decorrido = millis() - m.t_estado_ms;

    switch (m.estado) {
        case Estado::OCIOSO:
            passo_ocioso();
            if (botao(PIN_BTN_SELECT)) { transicao(Estado::INTAKE); }
            break;

        case Estado::INTAKE:
            passo_intake();
            if (m.leito.kg_agua >= m.leito.kg_max) {
                transicao(Estado::REGEN);              // leito saturado
            } else if (decorrido >= m.min_intake_ms) {
                transicao(Estado::REGEN);              // janela noturna terminou
            }
            break;

        case Estado::REGEN:
            passo_regen();
            if (m.leito.kg_agua <= 0.05f || decorrido >= m.max_regen_ms) {
                transicao(Estado::DESTIL);             // água liberada como vapor
            }
            break;

        case Estado::DESTIL:
            passo_destil();
            if (m.tanque.ml >= m.tanque.ml_max) {
                transicao(Estado::CHEIO);
            } else if (m.leito.kg_agua <= 0.01f && decorrido > 60000u) {
                ++m.ciclos;                            // ciclo completo auditado
                transicao(Estado::OCIOSO);
            }
            break;

        case Estado::CHEIO:
            if (botao(PIN_BTN_SELECT)) {               // usuário esvaziou
                m.tanque.ml = 0u;
                transicao(Estado::OCIOSO);
            }
            break;

        case Estado::ERRO:
            driver::fans_pwm(0);
            driver::aquecedor(false);                  // segurança primeiro
            if (botao(PIN_BTN_SELECT)) {
                Ambiente a{}; float t = 0.0f;
                if (driver::dht22_ler(a) &&
                    driver::ds18b20_ler(PIN_DS18B20_LEITO, t)) {
                    transicao(Estado::OCIOSO);         // sensores OK: recupera
                }
            }
            break;
    }
}

} // namespace controller

} // namespace tupan
