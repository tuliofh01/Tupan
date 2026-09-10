# Tupan Water Maker

[![Traduzir para PT-BR](https://img.shields.io/badge/PT-BR-Português-blue.svg)](README_PT-BR.md)

A portable atmospheric water generator designed for individual/small-scale hydration in water-scarce environments. The project combines microelectronics (Arduino Mega), analog/digital circuit design, systems engineering, and IoT connectivity.

## Project Origin

The **Tupan Water Maker** was conceived as an academic project for the **IoT & PLCs** course at **PUC-MG** (Pontifícia Universidade Católica de Minas Gerais), Computer Engineering program, semester **2026.2**, by **Túlio Ferreira Horta**.

The idea emerged from a shared concern: **water scarcity**. In Brazil's semi-arid Northeast region — home to over 30 million people — drought cycles are recurrent and devastating. Families depend on water trucks, cisterns, and increasingly strained groundwater. The project explores whether technology can provide a **decentralized, low-cost complement** to existing infrastructure.

The name **"Tupan"** comes from the Tupi-Guarani word for "thunder" or "divine spirit" — a nod to the atmospheric origin of the water and the indigenous knowledge of the land.

## Why the Documentation is in Portuguese

All official documentation (reports, diagrams, and deliverables) is written in **Portuguese (PT-BR)** because:

- The project is an **academic requirement** at a Brazilian university (PUC-MG).
- The target users and communities are primarily in **Brazil**, particularly the semi-arid Northeast.
- Brazilian **legal standards** (CONAMA, ANVISA, CDC, LGPD) and **regulatory frameworks** are referenced throughout.
- The course syllabus and evaluation criteria are in Portuguese.

This README, however, is in **English** to make the project accessible to an international audience and potential collaborators.

## Project Structure

```
Tupan Water Maker/
├── Documentação Oficial/          # Official deliverables
│   ├── relatórioDescritivo.docx  # Technical report (PT-BR)
│   ├── Arquivo de Mídia/          # Images, graphs, diagrams
│   └── Arquivos CAD/              # UML, schematics, flowcharts
├── Coleção de Software/           # Source code and scripts
│   ├── scripts/                   # Generation scripts
│   ├── firmware/                  # C++20 MVC firmware
│   ├── docs/                      # Documentation
│   ├── testes/                    # Test plans
│   └── recursos/                  # Resources
└── Tupan_Water_Maker_Pitch.pptx   # Sales pitch presentation
```

## Key Technical Highlights

| Area | Detail |
|------|--------|
| **Microcontroller** | Arduino Mega 2560 (ATmega2560) |
| **Firmware** | C++20 with MVC architecture, Finite State Machine |
| **Communication** | Bluetooth HC-05 (UART) + MQTT bridge |
| **Power** | Dual: 12V car battery (60Ah) + AC 110/220V charger |
| **Sensors** | DHT22 (temp/humidity), DS18B20, BMP280, water level sensor |
| **Actuators** | Fan, pump, heating resistor, valves (via SSR/MOSFET) |
| **Materials** | Recycled lab glassware, 3D-printed PLA, scrap electronics |
| **Cost estimate** | ~R$ 1.223 protótipo (with ~60% recycled materials) |

## Sustainability Philosophy

The Tupan is designed for **direct human consumption only** (1–2 liters per cycle), not industrial use. It aligns with UN Sustainable Development Goals:

- **ODS 6** — Clean Water and Sanitation
- **ODS 3** — Good Health and Well-being
- **ODS 12** — Responsible Production and Consumption

## Getting Started

### Requirements
- Python 3.10+
- `python-docx`, `matplotlib`, `python-pptx`, `Pillow`
- Arduino IDE for firmware development

### Regenerate the Report
```bash
cd "Coleção de Software/scripts"
python3 gerar_relatorio.py
```

### Regenerate the Pitch
```bash
python3 gerar_pitch.py
```

### Regenerate Images
```bash
cd "Coleção de Software/scripts"
python3 gerar_imagens.py
```

## License

This project is for **academic purposes only**. Unauthorized commercial use is prohibited.

## Contact

**Túlio Ferreira Horta**
- PUC-MG — Engenharia de Computação
- Disciplina: IoT & PLCs (2026.2)