// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — main.cpp (Arduino Mega 2560)
//  ---------------------------------------------------------------------------
//  Ponto de entrada mínimo: setup() inicia console (p/ Arduino IDE), HMI e
//  drivers; loop() roda a FSM a cada tick. Toda a lógica vive em tupan_core.
//  Compile pela Arduino IDE (Board: Arduino Mega or Mega 2560) ou PlatformIO.
// ============================================================================
#include "tupan_firmware.hpp"

void setup() {
    Serial.begin(115200);

    // Pinos: botões com pull-up interno; saídas de potência/HMI.
    pinMode(tupan::PIN_BTN_CIMA,     INPUT_PULLUP);
    pinMode(tupan::PIN_BTN_BAIXO,   INPUT_PULLUP);
    pinMode(tupan::PIN_BTN_SELECT, INPUT_PULLUP);
    pinMode(tupan::PIN_LED_VERDE,    OUTPUT);
    pinMode(tupan::PIN_LED_AMARELO,  OUTPUT);
    pinMode(tupan::PIN_LED_VERMELHO, OUTPUT);
    pinMode(tupan::PIN_FAN_PWM,   OUTPUT);
    pinMode(tupan::PIN_AQUECEDOR, OUTPUT);
    pinMode(tupan::PIN_SERVO_DAMPER, OUTPUT);

    tupan::view::oled_init();

    tupan::view::log(tupan::view::LogNivel::INFO, F("boot"),
                     "Tupan, Maquina de Chuva — firmware MVC");
    tupan::view::logu(tupan::view::LogNivel::INFO, F("boot"), "f_cpu_hz", F_CPU);
    tupan::view::log(tupan::view::LogNivel::INFO, F("boot"),
                     "FSM: OCIOSO aguardando botao SELECT");
    tupan::controller::transicao(tupan::Estado::OCIOSO);
}

void loop() {
    tupan::controller::atualizar();
    // Histerese de tempo: FSM a ~20 Hz é suficiente (sensores lentos).
    delay(50);
}
