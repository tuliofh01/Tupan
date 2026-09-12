# Tupan, Máquina de Chuva — Operator & Developer Manual (EN)

> Companion to [`manual_pt-br.md`](manual_pt-br.md). Architecture details live in
> [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Repository: `github.com/tuliofh01/Tupan`.

## 1. What this is

A portable, **compressor-free atmospheric water generator (AWG)** for the
Brazilian semi-arid region. It uses a chemical-thermal cycle instead of
refrigeration:

1. **Night — Sorption:** fans pull humid night air through a **calcium chloride
   (CaCl₂) bed**, which retains water chemically.
2. **Dawn — Isolation:** a servo damper closes the air and opens the glassware
   distillation duct.
3. **Day — Regeneration:** a **solenoid heater (~120 °C)** releases the water as
   vapor; it condenses in recycled lab glassware.
4. **Post-treatment:** a **mineralizing filter** + **UV-C** make the distillate
   potable (target Ca 45 / Mg 18 mg/L).
5. **Storage:** a **2 L basin with a tap**.

Reference output: **≈ 0.68 L potable per cycle** at 68 % RH / 24 °C,
**0.43 L/kWh**, **≈ 594 L/year** per unit in Petrolina-PE.

> ⚠ **Safety:** 120 °C surfaces burn; UV-C 254 nm harms eyes/skin (see §7).

## 2. Requirements

- Python 3.10+, a GNU toolchain with **C++23**, **CMake ≥ 3.25**.
- Studio/scripting: **GLFW3**, **GLEW**, **Lua 5.4** (sol2, Dear ImGui and luaaa
  are fetched automatically by CMake).
- Firmware: Arduino IDE or PlatformIO (Arduino Mega 2560).

## 3. Repository contents

```
Tupan Water Maker/
├── CMakeLists.txt              # root build (core + studio + scripting)
├── README.md / README.pt-BR.md
├── src/                        # CODE
│   ├── core/                   # C++23 physics + CLI + tests
│   ├── studio/                 # UI: Lua(sol2) + Dear ImGui + OpenGL + STL/OBJ
│   ├── scripting/              # headless Lua runner (luaaa)
│   ├── bindings/               # Python module (pybind11)
│   └── firmware/               # Arduino Mega (C++20, MVC/FSM)
├── tools/                      # scripts by purpose
│   ├── geradores/              # report, pitch, UML diagrams
│   ├── midia/                  # renders, maps, mockups
│   ├── pipeline/               # climate/ML + energy cost
│   ├── cad/                    # electrical schematic + DXF/STL/SCAD
│   ├── server/                 # Flask web service (+ templates/)
│   └── tests/                  # pytest suite
├── data/                       # raw/ · processed/ · results/
├── docs/                       # relatorios/ · pitch/ · manuais/ · midia/
├── scripts/                    # build-linux.sh · build-windows.bat · docker · k8s
└── deploy/                     # k8s/ · vps/
```

## 4. Using the software

### 4.1 Native core, CLI, tests and the Tupan Studio

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
./build/tupan_tests               # core tests (CTest)
./build/tupan_sim --night 8 --day 6 --ur 68 --temp 24
./build/tupan_sim --json          # machine-readable output
./build/tupan_studio              # interactive UI (Lua + ImGui + OpenGL)
./build/tupan_script              # headless Lua script using tupan.*
```

The **studio** reads its UI from `src/studio/assets/studio.lua` (a JSON-like Lua
table: menus, panels and the 3D scene). Edit the `.lua` and use
**Arquivo → Recarregar DSL** — no recompilation.

**CAD/3D rendering.** Scene objects support `shape = "model"` with a `file`
field pointing to an STL or OBJ mesh (normalized to a unit box, so `pos`/`size`
still apply):

```lua
{ id = "cad_carcaca", shape = "model",
  file = "docs/midia/cad/tupan_pecas.stl",
  pos = { 0.0, 1.0, -2.0 }, size = { 3.2, 3.2, 3.2 }, color = { 0.82, 0.86, 0.92 } }
```

Regenerate the CAD assets (DXF/STL/SCAD + technical board):
`python3 tools/cad/gerar_cad.py`.

### 4.2 Web simulator (Flask)

```bash
python3 tools/server/simulador_tupan.py     # http://127.0.0.1:5000
```

### 4.3 Data pipeline (real climate + ML + energy cost)

```bash
python3 tools/pipeline/analise_dados.py     # ERA5/Open-Meteo + ML
python3 tools/pipeline/custo_energia.py     # ANEEL tariffs + TSEE
```

Reference numbers: night RH **68.6 %** @ 24.6 °C; **594 L/year**; ML R² 0.991;
**R$ 2.36–2.38/L** on the grid or **R$ 0.83/L** under Tarifa Social.

### 4.4 Firmware (Arduino Mega 2560)

Open `src/firmware/` in the Arduino IDE (or `pio run`). `tupan_firmware.hpp`
holds the MVC/FSM logic; `main.cpp` is the entry point. Serial at **115200 baud**
logs every transition; sensors/actuators are clearly marked `// STUB`.

### 4.5 Tests

```bash
./build/tupan_tests                       # C++ (CTest)
cd tools/tests && python3 -m pytest -q    # Python
```

The Python tests run against the native module when built and against the Python
fallback otherwise — **physical parity guaranteed**.

### 4.6 Media, report and pitch (from source)

```bash
python3 tools/midia/gerar_imagens.py     # design renders + charts
python3 tools/midia/gerar_mapas.py       # Brazil thematic maps
python3 tools/midia/gerar_mockups_app.py # IoT app mockups
python3 tools/cad/gerar_cad.py           # DXF/STL/SCAD + board
python3 tools/geradores/gerar_relatorio.py
python3 tools/geradores/gerar_pitch.py
```

## 5. Standalone packaging (no interpreter on the target)

To distribute without installing Python, build a single executable of the web
service with **PyInstaller**:

```bash
pip install pyinstaller
scripts/build-standalone.sh          # → dist/standalone/tupan-web
./dist/standalone/tupan-web          # serves http://127.0.0.1:5000
```

The Docker image (`docker/Dockerfile`, target `web`) is the equivalent
container-based option.

## 6. Bill of materials (target ≈ R$ 450 in new parts)

| # | Item | Spec | Qty |
|---|------|------|-----|
| 1 | Arduino Mega 2560 (or clone) | ATmega2560 | 1 |
| 2 | 12 V fan | 120 mm, ~2.5 W | 3 |
| 3 | Solenoid / resistor | 250 W, 12/24 V + heatsink | 1 |
| 4 | Servo | MG996R (air damper) | 1 |
| 5 | MOSFET + driver | IRLZ44N ×2 | 2 |
| 6 | DHT22 | RH + temperature | 1 |
| 7 | DS18B20 | waterproof ×2 (bed, vapor) | 2 |
| 8 | Capacitive level sensor | XKC-Y25-V | 1 |
| 9 | Calcium chloride | technical grade, 2 kg | 1 |
| 10 | Glassware | recycled lab flask/condenser | 1 |
| 11 | Mineralizing filter | purifier cartridge | 1 |
| 12 | UV-C lamp | 6 W, 254 nm + ballast | 1 |
| 13 | PSU | 12 V 30 A (360 W) | 1 |
| 14 | Bluetooth | HC-05 | 1 |
| 15 | Frame | printed PLA + MDF/acrylic | — |
| 16 | Potable basin with tap | 2 L, food grade | 1 |

Commonly owned items (Mega, HC-05, servos, fans) bring the typical real cost to
**~R$ 300–350**.

## 7. Electrical safety

| Mega pin | Signal | Wiring |
|----------|--------|--------|
| D2 | DHT22 data | 10 kΩ pull-up |
| D3 / D4 | DS18B20 bed / vapor | 4.7 kΩ (OneWire) |
| A0 | level sensor | 0–5 V analog |
| D5 | fan MOSFET (PWM) | 220 Ω gate resistor |
| D6 | solenoid MOSFET/relay | **always via relay/MOSFET — never direct** |
| D9 | damper servo | dedicated 5 V (current peaks) |
| TX1/RX0 | HC-05 | voltage divider on Mega RX |

- **120 °C:** insulate the bed and label the hot surfaces.
- **UV-C 254 nm:** fully opaque chamber + interlock (firmware cuts UV when open).
- **Water + electronics:** separate compartments; drip tray.
- **First water of a new bed:** discard the first two runs before drinking.

## 8. Where the Tupan works best (biomes)

| Region (biome) | Köppen | Typical night RH | Fit |
|----------------|--------|------------------|-----|
| Brazilian NE semi-arid (base project) | BSh | 60–75 % | ★★★★★ ideal |
| Sahel (Africa, rainy Jun–Sep) | BSh | 70–90 % (wet) | ★★★★☆ seasonal |
| Sahara / Arabia | BWh | < 20 % | ★☆☆☆☆ unviable |
| Mediterranean (Europe) | Csa | 50–70 % | ★★★☆☆ seasonal |
| US Southwest / N Mexico | BWh/BSh | 30–50 % (monsoon) | ★★☆☆☆ marginal |
| Atacama/Namibe coastal fog | BWk | 80–95 % | ★★★★☆ with thermal mods |

Rule of thumb: night RH ≥ 60 % → base design; 40–60 % → extend INTAKE and bed;
< 40 % → do not install. The semi-arid Northeast is one of the **best** places for
this cycle, because the humid night and hot day coincide.

## 9. Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `sorcao: kg=` not rising | saturated air filter; compacted bed | clean/replace filter; loosen the bed (pearls, not powder) |
| `regen: t_leito=` below 120 °C | weak insulation; weak solenoid | add insulation; check 250 W at correct voltage |
| Low `destil: ml=` | leaking duct; hot condenser | seal with silicone; shade/vent the condenser |
| Tasteless water | spent mineralizing cartridge | replace (date the frame) |

## 10. Documentation & media

- Deliverables: `docs/relatorios/relatorio_descritivo.docx` (ABNT article) and
  `docs/pitch/apresentacao_produto.pptx`; LinkedIn article `docs/relatorios/artigo.txt`.
- Generated media in `docs/midia/{renders,graficos,mapas,mockups,diagramas,cad}`.
- Architecture: `docs/ARCHITECTURE.md`. Coding standard: `AGENTS.md`
  (didactic comments in PT-BR).
