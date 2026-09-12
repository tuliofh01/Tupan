<!-- ======================================================================
SEO / META (para cópias renderizadas fora do GitHub — o GitHub sanitiza
meta tags, mas indexa todo o texto deste arquivo):
title: Tupan, Máquina de Chuva — Atmospheric Water Generator (AWG)
description: Compressor-free atmospheric water generator (AWG) for the
  Brazilian semi-arid region: nocturnal calcium-chloride sorption, solenoid
  regeneration, glassware distillation, UV sterilization. Arduino Mega
  firmware in C++20, Python data pipeline, Flask web simulator, IoT app.
keywords: atmospheric water generator, AWG, water from air, Tupan, máquina
  de chuva, água atmosférica, semiárido, Petrolina, PUC-MG, Arduino Mega,
  C++20, Python, IoT, MQTT, Bluetooth HC-05, calcium chloride, CaCl2,
  desiccant sorption, distillation, UV sterilization, mineralizing filter,
  Flask, pybind11, scikit-learn, PyTorch, Monte Carlo, FSM, MVC
author: Túlio Ferreira Horta
robots: index, follow
====================================================================== -->

<div align="center">

# Tupan, Máquina de Chuva

**Atmospheric Water Generator (AWG) · Arduino Mega · C++20 · Python · IoT**

*In English: Tupan, Rain Machine — a compressor-free atmospheric water
generator for water-scarce regions.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PT-BR](https://img.shields.io/badge/docs-PT--BR-blue.svg)](software/docs/README_PT-BR.md)
[![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C.svg)](software/scripts/dist/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](software/scripts/)
[![Arduino Mega 2560](https://img.shields.io/badge/Board-Arduino%20Mega%202560-teal.svg)](software/firmware/)

</div>

A portable, compressor-free **atmospheric water generator (AWG)** designed for
individual and small-scale hydration in water-scarce environments — built with
microelectronics (Arduino Mega), C++20 firmware, a Python data pipeline, a
Flask web simulator, and IoT connectivity (Bluetooth HC-05 + MQTT).

## Table of Contents

- [Project Origin](#project-origin)
- [How It Works (no compressor)](#how-it-works-no-compressor)
- [Why the Documentation is in Portuguese](#why-the-documentation-is-in-portuguese)
- [Project Structure](#project-structure)
- [Key Technical Highlights](#key-technical-highlights)
- [Sustainability Philosophy](#sustainability-philosophy)
- [Getting Started](#getting-started)
- [License](#license)
- [Contact](#contact)

## Project Origin

The **Tupan, Máquina de Chuva** (formerly "Tupan Water Maker") was conceived as
an academic project for the **IoT & PLCs** course at **PUC-MG** (Pontifícia
Universidade Católica de Minas Gerais), Computer Engineering program, semester
**2026.2**, by **Túlio Ferreira Horta**.

The idea emerged from a shared concern: **water scarcity**. In Brazil's
semi-arid Northeast region — home to over 30 million people — drought cycles
are recurrent and devastating. Families depend on water trucks, cisterns, and
increasingly strained groundwater. The project explores whether technology can
provide a **decentralized, low-cost complement** to existing infrastructure.

The name **"Tupan"** comes from the Tupi-Guarani word for "thunder" or "divine
spirit" — a nod to the atmospheric origin of the water and the indigenous
knowledge of the land.

## How It Works (no compressor)

The Tupan deliberately avoids compressors and cooling stages. It exploits the
semi-arid **nocturnal humidity peak** with a purely chemical-thermal cycle:

1. **Night — Sorption (INTAKE):** fans pull humid night air through a
   **calcium chloride (CaCl₂) bed**, which chemically retains water.
2. **Dawn — Isolation (servo damper):** a servo motor closes the air intake
   and opens the path to the distillation glassware duct.
3. **Day — Regeneration (REGEN):** a **solenoid heater** raises the wet salt
   to ~120 °C, releasing the water as vapor.
4. **Distillation (DESTIL):** vapor condenses in recycled laboratory
   glassware into liquid water.
5. **Post-treatment:** the distillate passes through a **mineralizing filter**
   and a **UV lamp** for sterilization.
6. **Storage:** potable water is stored in a small **basin with a tap**.

## Why the Documentation is in Portuguese

All official documentation (reports, diagrams, and deliverables) is written in
**Portuguese (PT-BR)** because:

- The project is an **academic requirement** at a Brazilian university (PUC-MG).
- The target users and communities are primarily in **Brazil**, particularly
  the semi-arid Northeast.
- Brazilian **legal standards** (CONAMA, ANVISA, CDC, LGPD) and regulatory
  frameworks are referenced throughout.
- The course syllabus and evaluation criteria are in Portuguese.

This README, however, is in **English** to make the project accessible to an
international audience and potential collaborators.
[Read it in Portuguese →](software/docs/README_PT-BR.md)

## Project Structure

```
Tupan Water Maker/
├── README.md                          # This file (EN)
├── LICENSE                            # MIT
├── documentacao/                      # Official deliverables
│   ├── relatórioDescritivo.docx       # Technical report (PT-BR)
│   ├── apresentaçãoProduto.pptx       # Sales pitch presentation
│   ├── midia/                         # Images, graphs, diagrams (+ fontes/)
│   └── cad/                           # CAD: DXF/SVG/STL (+ fontes/)
└── software/
    ├── docs/README_PT-BR.md           # Portuguese README
    ├── scripts/                       # ALL Python: generators, simulator, tests
    │   ├── testes/                    # Unit tests (pytest)
    │   ├── templates/                 # Flask simulator web UI
    │   └── dist/                      # C++20/pybind11 native simulator
    ├── dados/                         # Climate data, projections, ML metrics
    └── firmware/                      # Arduino Mega C++20 MVC firmware
```

## Key Technical Highlights

| Area | Detail |
|------|--------|
| **Water cycle** | Nocturnal CaCl₂ sorption → solenoid regeneration (~120 °C) → glassware distillation → mineralizing filter + UV → basin with tap |
| **Microcontroller** | Arduino Mega 2560 (ATmega2560) |
| **Firmware** | C++20, MVC architecture, finite state machine (OCIOSO/INTAKE/REGEN/DESTIL/CHEIO/ERRO) |
| **Simulators** | Native C++20 CLI/GUI (Qt5) + pybind11 web simulator (Flask) — physics parity verified |
| **Data pipeline** | pandas + scikit-learn + PyTorch on 14,616 h of ERA5/Open-Meteo data (Petrolina-PE) |
| **Communication** | Bluetooth HC-05 (UART) + MQTT bridge |
| **Sensors** | DHT22 (temp/humidity), DS18B20 (bed/vapor), capacitive water level |
| **Actuators** | PWM fans, solenoid heater, servo damper (no compressor, no pump) |
| **Materials** | Recycled lab glassware, 3D-printed PLA, scrap electronics |
| **Cost estimate** | ~R$ 447 in purchased parts (~R$ 503 in owned/reused components) |

## Sustainability Philosophy

The Tupan is designed for **direct human consumption only** (1–2 liters per
cycle), not industrial use. It aligns with UN Sustainable Development Goals:

- **SDG 6** — Clean Water and Sanitation
- **SDG 3** — Good Health and Well-being
- **SDG 12** — Responsible Production and Consumption

## Getting Started

### Requirements
- Python 3.10+, GNU toolchain with C++20/23, CMake, Qt5 (for the native GUI)
- Arduino IDE or PlatformIO for firmware

### Data pipeline (climate + ML, Petrolina-PE)
```bash
cd "software/scripts"
python3 analise_dados.py
```

### Native Simulator (C++20, software/scripts/dist)
```bash
cd "software/scripts/dist"
./build.sh && ./bin/tupan_sim --help
```

### Run the Web Simulator
```bash
cd "software/scripts"
python3 simulador_tupan.py
# Open http://127.0.0.1:5000
```

### Firmware (Arduino Mega 2560)
```bash
cd "software/firmware"
pio run            # or open tupan_firmware.hpp + main.cpp in the Arduino IDE
```

### Regenerate documentation artifacts
```bash
cd "software/scripts"
python3 gerar_relatorio.py      # ABNT report (PT-BR + EN)
python3 gerar_pitch.py          # pitch presentation
python3 diagramas_uml.py        # PlantUML diagrams
python3 esquema_eletrico.py     # electrical schematic (DXF/SVG/PNG)
python3 gerar_imagens.py        # media assets
```

## License

Released under the [MIT License](LICENSE) — © 2026 Túlio Ferreira Horta.
The academic deliverables (report and pitch) remain for academic purposes.

## Contact

**Túlio Ferreira Horta**
- PUC-MG — Engenharia de Computação
- Disciplina: IoT & PLCs (2026.2)

---

*Keywords: atmospheric water generator, AWG, water from air, gerador de água
atmosférica, Tupan, máquina de chuva, semiárido brasileiro, Arduino Mega,
C++20 firmware, calcium chloride sorption, desiccant, distillation, UV
sterilization, mineralizing filter, IoT, MQTT, Bluetooth HC-05, Flask,
pybind11, scikit-learn, PyTorch, Monte Carlo simulation, PUC-MG.*
