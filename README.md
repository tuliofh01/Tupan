<!-- ======================================================================
SEO / META (para cópias renderizadas fora do GitHub — o GitHub sanitiza
meta tags, mas indexa todo o texto deste arquivo):
title: Tupan, Máquina de Chuva — Atmospheric Water Generator (AWG)
description: Compressor-free atmospheric water generator (AWG) for the
  Brazilian semi-arid region: nocturnal calcium-chloride sorption, solenoid
  regeneration, glassware distillation, UV sterilization. C++23 core, Lua +
  ImGui + OpenGL studio, Python data pipeline, Flask simulator, Docker/K8s.
keywords: atmospheric water generator, AWG, water from air, Tupan, máquina
  de chuva, água atmosférica, semiárido, Petrolina, PUC-MG, Arduino Mega,
  C++23, Lua, ImGui, OpenGL, Docker, Kubernetes, Jenkins, CI/CD, IoT, MQTT,
  Bluetooth HC-05, calcium chloride, CaCl2, desiccant sorption, distillation,
  UV sterilization, mineralizing filter, Flask, pybind11, scikit-learn
author: Túlio Ferreira Horta
robots: index, follow
====================================================================== -->

<div align="center">

# Tupan, Máquina de Chuva

**Atmospheric Water Generator (AWG) · C++23 core · Lua/ImGui/OpenGL studio · Python · IoT**

*Em português: Tupan, Máquina de Chuva — um gerador de água atmosférica sem
compressor para regiões de escassez hídrica.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PT-BR](https://img.shields.io/badge/docs-PT--BR-blue.svg)](README.pt-BR.md)
[![C++23](https://img.shields.io/badge/C%2B%2B-23-00599C.svg)](src/core/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](tools/)
[![Arduino Mega 2560](https://img.shields.io/badge/Board-Arduino%20Mega%202560-teal.svg)](src/firmware/)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED.svg)](docker/Dockerfile)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-Jenkins%20%7C%20K8s-D24939.svg)](ci/Jenkinsfile)

</div>

A portable, compressor-free **atmospheric water generator (AWG)** for
individual and small-scale hydration in water-scarce environments — built with
an **Arduino Mega** (C++20 firmware), a **C++23 simulation core** with native
CLI/GUI and a **Lua + Dear ImGui + OpenGL interactive studio**, a **Python data
pipeline**, a **Flask web simulator**, and **IoT** connectivity (Bluetooth
HC-05 + MQTT). Ships with **Docker** images and a **Jenkins → Kubernetes/VPS**
delivery pipeline.

## Table of Contents

- [Project Origin](#project-origin)
- [How It Works (no compressor)](#how-it-works-no-compressor)
- [Architecture](#architecture)
- [Tupan Studio (Lua + ImGui + OpenGL)](#tupan-studio-lua--imgui--opengl)
- [Project Structure](#project-structure)
- [Key Technical Highlights](#key-technical-highlights)
- [Getting Started](#getting-started)
- [Docker & CI/CD](#docker--cicd)
- [Media & Documentation](#media--documentation)
- [Sustainability Philosophy](#sustainability-philosophy)
- [License](#license)
- [Contact](#contact)

## Project Origin

The **Tupan, Máquina de Chuva** (formerly "Tupan Water Maker") was conceived as
an academic project for the **IoT & PLCs** course at **PUC-MG** (Pontifícia
Universidade Católica de Minas Gerais), Computer Engineering program, semester
**2026.2**, by **Túlio Ferreira Horta**.

The idea emerged from a shared concern: **water scarcity**. In Brazil's
semi-arid Northeast — home to over 30 million people — drought cycles are
recurrent and devastating. Families depend on water trucks, cisterns, and
increasingly strained groundwater. The project explores whether technology can
provide a **decentralized, low-cost complement** to existing infrastructure.

The name **"Tupan"** comes from the Tupi-Guarani word for "thunder" or "divine
spirit" — a nod to the atmospheric origin of the water.

## How It Works (no compressor)

The Tupan deliberately avoids compressors and cooling stages. It exploits the
semi-arid **nocturnal humidity peak** with a purely chemical-thermal cycle:

1. **Night — Sorption:** fans pull humid night air through a **calcium chloride
   (CaCl₂) bed**, which chemically retains water.
2. **Dawn — Isolation:** a servo damper closes the air intake and opens the
   path to the distillation glassware duct.
3. **Day — Regeneration:** a **solenoid heater** raises the wet salt to
   ~120 °C, releasing the water as vapor.
4. **Distillation:** vapor condenses in recycled laboratory glassware.
5. **Post-treatment:** a **mineralizing filter** and a **UV-C lamp** make the
   distillate potable (Ca 45 / Mg 18 mg/L target).
6. **Storage:** potable water is stored in a small **basin with a tap**.

## Architecture

The full map, data contracts and extension guide live in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). In short: one **header-only C++23
core** is the single source of physical truth; CLI, Qt5 GUI, Lua/ImGui/OpenGL
studio, pybind11 module, Flask service and firmware all consume the same
contracts; Python **tools** produce media, reports and the data pipeline.

```
             src/core (tupan_core.hpp — física única)
                 │        │         │         │
     tupan_sim ──┘  tupan_gui   tupan_studio   tupan_native (pybind11)
                 (Qt5)      (Lua+ImGui+GL)         │
                                                   ├── tools/pipeline (dados/ML)
                                                   ├── tools/server  (Flask)
                                                   └── tools/geradores (relatórios)
```

## Tupan Studio (Lua + ImGui + OpenGL)

`src/studio` is an interactive 3D application where the UI is defined by a
**Lua DSL** (`src/studio/assets/studio.lua`): menus, panels and the 3D scene are
declarative tables — no recompilation needed to change the interface.

- **Custom linear algebra** (`math.hpp`): `Real = float`, `alignas(16)` column-major
  `Mat4` with a `union` exposing columns/floats, `constexpr` ops — minimal per-frame overhead.
- **sol2** reads the declarative Lua DSL; **Dear ImGui** + **GLFW** + **OpenGL 3.3**
  render the widgets and the 3D scene; menu actions are dispatched through **lambdas**.
- **luaaa** (`src/scripting`) exposes the core to headless Lua scripts (`tupan.*`).

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
./build/tupan_studio          # abre a janela interativa
./build/tupan_script          # roda src/scripting/scripts/ciclo.lua
```

## Project Structure

```
Tupan Water Maker/
├── CMakeLists.txt              # build raiz (núcleo + studio)
├── README.md / README.pt-BR.md
├── pyproject.toml / setup.py / requirements.txt
├── docker/Dockerfile           # multi-stage: build | core | web
├── docker-compose.yml
├── ci/Jenkinsfile              # pipeline CI/CD
├── .github/workflows/ci.yml    # espelho GitHub Actions
├── src/                        # CÓDIGO
│   ├── core/                   # núcleo C++23 (física) + CLI + testes + CMake
│   ├── studio/                 # Lua(sol2) + Dear ImGui + OpenGL (math, scene, DSL)
│   ├── scripting/              # runner Lua headless via luaaa
│   ├── bindings/               # módulo Python (pybind11)
│   └── firmware/               # Arduino Mega (C++20, MVC/FSM)
├── tools/                      # SCRIPTS (por propósito)
│   ├── geradores/              # relatório, pitch, diagramas UML
│   ├── midia/                  # imagens, mapas, mockups do app
│   ├── pipeline/               # clima (ERA5/Open-Meteo) + ML + custo de energia
│   ├── cad/                    # esquema elétrico
│   ├── server/                 # microsserviço Flask (+ templates/)
│   └── tests/                  # testes Python (pytest)
├── data/                       # DADOS: raw/ · processed/ · results/
├── docs/                       # ENTREGÁVEIS: relatorios/ · pitch/ · manuais/
│   └── midia/                  # renders/ · graficos/ · mapas/ · mockups/ · diagramas/ · cad/
├── scripts/                    # build-linux.sh · build-windows.bat · docker · k8s
└── deploy/                     # k8s/ (manifests) · vps/ (systemd + nginx)
```

## Key Technical Highlights

| Area | Detail |
|------|--------|
| **Water cycle** | Nocturnal CaCl₂ sorption → solenoid regeneration (~120 °C) → glassware distillation → mineralizing filter + UV-C → basin with tap |
| **Microcontroller** | Arduino Mega 2560 (ATmega2560) |
| **Firmware** | C++20, MVC, FSM (OCIOSO/INTAKE/REGEN/DESTIL/CHEIO/ERRO) |
| **Core** | Header-only C++23, `-Wall -Wextra -Wpedantic`; 35 CTest cases |
| **Studio** | Lua DSL (sol2) + Dear ImGui + OpenGL 3.3; custom aligned linear algebra (`union`); luaaa headless scripting |
| **Simulators** | Native CLI + Qt5 GUI + pybind11 + Flask — physics parity verified (0.68 L potable @ UR 68 %/24 °C) |
| **Data pipeline** | ERA5/Open-Meteo (14,616 h, Petrolina-PE) + ridge/MLP, R² 0.991, RMSE 0.064 L |
| **Energy** | 1.683 kWh/cycle, 0.43 L/kWh; R$ 2.36/L (full tariff), R$ 0.83/L (TSEE) |
| **Communication** | Bluetooth HC-05 (UART) + MQTT bridge |
| **Sensors / Actuators** | DHT22, DS18B20, capacitive level / PWM fans, solenoid heater, servo damper |
| **Delivery** | Docker multi-stage (core/web) + Jenkins → K8s/HPA or VPS (systemd+nginx) |
| **Cost estimate** | ~R$ 447 in purchased parts (~R$ 503 in owned/reused components) |

## Getting Started

### Requirements
- Python 3.10+; GNU toolchain with C++23; CMake ≥ 3.25
- Studio/scripting: GLFW3, GLEW, Lua 5.4 (sol2, Dear ImGui and luaaa are fetched by CMake)
- Arduino IDE or PlatformIO for firmware

### Build the C++ core, CLI, tests and studio
```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
./build/tupan_sim --night 8 --day 6 --ur 68 --temp 24 --json
./build/tupan_studio        # interactive Lua/ImGui/OpenGL UI
./build/tupan_script        # headless Lua script (luaaa) using tupan.*
```
Or use the convenience scripts:
```bash
scripts/build-linux.sh              # Linux (Ubuntu/Debian/Arch)
scripts\build-windows.bat           # Windows 10/11 (MSVC)
```

### Data pipeline (climate + ML + energy cost)
```bash
python3 tools/pipeline/analise_dados.py
python3 tools/pipeline/custo_energia.py
```

### Web simulator
```bash
python3 tools/server/simulador_tupan.py   # http://127.0.0.1:5000
```

### Firmware (Arduino Mega 2560)
```bash
cd src/firmware
pio run        # or open tupan_firmware.hpp + main.cpp in the Arduino IDE
```

### Regenerate media, report and pitch
```bash
python3 tools/midia/gerar_imagens.py   # design renders + engineering charts
python3 tools/midia/gerar_mapas.py     # thematic Brazil maps
python3 tools/midia/gerar_mockups_app.py
python3 tools/geradores/diagramas_uml.py
python3 tools/geradores/gerar_relatorio.py
python3 tools/geradores/gerar_pitch.py
```

## Docker & CI/CD

```bash
scripts/build-docker.sh --target web --tag dev        # build image
docker compose up --build                             # web on :5000
scripts/deploy-k8s.sh --registry ghcr.io/tuliofh --tag 0.1.0   # deploy k8s
```

- **Images:** `docker/Dockerfile` (targets `core`, `web`), gunicorn + `/health`.
- **Kubernetes:** `deploy/k8s/` (namespace, deployment, service, ingress, HPA).
- **VPS:** `deploy/vps/` (systemd unit + nginx reverse proxy).
- **Jenkins:** `ci/Jenkinsfile` builds, tests, generates media, pushes and deploys.
- **GitHub Actions:** `.github/workflows/ci.yml` mirrors build/test/publish.

## Media & Documentation

All generated media lives under `docs/midia/`:

| Folder | Content |
|--------|---------|
| `renders/` | Machine cross-sections (night/day), 4-stage cycle, 3D concept |
| `graficos/` | Energy balance, production × RH, cost, diurnal cycle, growth |
| `mapas/` | Brazil thematic maps (night RH, annual yield, feasibility, biomes) |
| `mockups/` | Companion IoT app screens (HTML + PNG) |
| `diagramas/` | UML use case/sequence/class + firmware flowchart |
| `cad/` | Electrical schematic and technical drawings |

Deliverables: `docs/relatorios/relatorio_descritivo.docx` (ABNT article) and
`docs/pitch/apresentacao_produto.pptx`. The LinkedIn article is at
`docs/relatorios/artigo.txt`. Manuals are in `docs/manuais/`.

## Sustainability Philosophy

The Tupan is designed for **direct human consumption only** (1–2 liters per
cycle), not industrial use. It aligns with UN Sustainable Development Goals
**SDG 6** (Clean Water and Sanitation), **SDG 3** (Good Health and Well-being)
and **SDG 12** (Responsible Production and Consumption).

## License

Released under the [MIT License](LICENSE) — © 2026 Túlio Ferreira Horta.
The academic deliverables (report and pitch) remain for academic purposes.

## Contact

**Túlio Ferreira Horta**
- PUC-MG — Engenharia de Computação
- Disciplina: IoT & PLCs (2026.2)

---

*Keywords: atmospheric water generator, AWG, water from air, Tupan, máquina de
chuva, semiárido brasileiro, Arduino Mega, C++23, Lua, Dear ImGui, OpenGL,
Docker, Kubernetes, Jenkins, calcium chloride sorption, distillation, UV
sterilization, mineralizing filter, IoT, MQTT, Bluetooth HC-05, Flask, pybind11,
scikit-learn, PUC-MG.*
