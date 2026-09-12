# Firmware — Tupan, Máquina de Chuva (MVC, Arduino Mega 2560)

FSM do ciclo real (sem compressor): `OCIOSO → INTAKE (sorção noturna) →
REGEN (aquecimento do leito) → DESTIL → CHEIO/ERRO`.

## Estrutura (arquivo único, seções numeradas)
1. **Pinagem** — única fonte de verdade (confere com o esquemático CAD).
2. **Model** — structs de ambiente/leito/reservatório + estado (1 byte).
3. **View** — `log()`/`logf()`/`logu()` no console da Arduino IDE, semáforo, OLED stub.
4. **Drivers** — stubs claros p/ DHT22, DS18B20, nível, PWM, relé, servo-damper.
5. **Controller** — FSM com transições logadas + histerese do termostato.

## Logs no Arduino IDE (115200 baud)
[CICLO] fsm: INTAKE          ← toda transição de estado
[INFO ] sorcao: kg=0.741     ← captação do leito a cada 5 s
[INFO ] regen: t_leito=119.8 ← termostato com histerese ±2 °C
[CICLO] destil: ml=1240      ← reservatório em tempo real

## Onde plugar seu hardware
- `driver::dht22_ler()` → DHT.h real
- `driver::ds18b20_ler()` → OneWire + DallasTemperature
- `driver::damper_angulo()` → Servo.h
- `view::oled_init/estado/medidas` → U8g2

## Memória (ATmega2560: 8 KB SRAM)
Sem `String` dinâmica (tudo `F()`/PROGMEM + buffers fixos), `enum class : uint8_t`,
structs empacotadas — cabe com folga mesmo com U8g2.
