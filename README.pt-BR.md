<!-- ======================================================================
SEO / META (para cópias renderizadas fora do GitHub — o GitHub sanitiza
meta tags, mas indexa todo o texto deste arquivo):
title: Tupan, Máquina de Chuva — Gerador de Água Atmosférica (sem compressor)
description: Gerador de água atmosférica (AWG) sem compressor para o
  semiárido brasileiro: sorção noturna com cloreto de cálcio, regeneração
  por solenoide, destilação em vidraria, UV e filtro mineralizante. Núcleo
  C++23, studio Lua + ImGui + OpenGL, pipeline Python, Docker/K8s e CI/CD.
keywords: gerador de água atmosférica, AWG, água do ar, Tupan, máquina de
  chuva, semiárido, Petrolina, PUC-MG, Arduino Mega, C++23, Lua, sol2, ImGui,
  OpenGL, luaaa, Docker, Kubernetes, Jenkins, IoT, MQTT, cloreto de cálcio
author: Túlio Ferreira Horta
robots: index, follow
====================================================================== -->

<div align="center">

# Tupan, Máquina de Chuva

**Gerador de Água Atmosférica (AWG) · núcleo C++23 · studio Lua/ImGui/OpenGL · Python · IoT**

*In English: Tupan, Rain Machine — a compressor-free atmospheric water
generator for water-scarce regions.*

[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-yellow.svg)](LICENSE)
[![EN](https://img.shields.io/badge/docs-English-blue.svg)](README.md)
[![C++23](https://img.shields.io/badge/C%2B%2B-23-00599C.svg)](src/core/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](tools/)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED.svg)](docker/Dockerfile)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-Jenkins%20%7C%20K8s-D24939.svg)](ci/Jenkinsfile)

</div>

Gerador portátil de água atmosférica **sem compressor**, para hidratação
individual e em pequena escala — construído com **Arduino Mega** (firmware
C++20), **núcleo de simulação C++23** com CLI e um **studio interativo em Lua +
Dear ImGui + OpenGL**, **pipeline de dados em Python**, **simulador web Flask**
e **IoT** (Bluetooth HC-05 + MQTT). Inclui **imagens Docker** e **pipeline
Jenkins → Kubernetes/VPS**.

## Sumário

- [Origem do Projeto](#origem-do-projeto)
- [Como Funciona (sem compressor)](#como-funciona-sem-compressor)
- [Arquitetura](#arquitetura)
- [Tupan Studio (Lua + ImGui + OpenGL)](#tupan-studio-lua--imgui--opengl)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Destaques Técnicos](#destaques-técnicos)
- [Como Começar](#como-começar)
- [Docker e CI/CD](#docker-e-cicd)
- [Mídia e Documentação](#mídia-e-documentação)
- [Filosofia de Sustentabilidade](#filosofia-de-sustentabilidade)
- [Licença](#licença)
- [Contato](#contato)

## Origem do Projeto

O **Tupan, Máquina de Chuva** (antes "Tupan Water Maker") foi concebido como
projeto acadêmico da disciplina **IoT & PLCs** da **PUC-MG** (Pontifícia
Universidade Católica de Minas Gerais), Engenharia de Computação, **2026.2**,
por **Túlio Ferreira Horta**.

A ideia nasceu de uma preocupação comum: a **escassez de água**. No semiárido
brasileiro — mais de 30 milhões de pessoas — as secas são recorrentes. Famílias
dependem de caminhões-pipa, cisternas e aquíferos pressionados. O projeto
explora se a tecnologia pode ser um **complemento descentralizado e barato**.

O nome **"Tupan"** vem do tupi-guarani para "trovão"/"espírito divino" — uma
referência à origem atmosférica da água.

## Como Funciona (sem compressor)

O Tupan evita compressores e refrigeração. Ele usa o **pico de umidade noturna**
do semiárido num ciclo químico-térmico:

1. **Noite — Sorção:** ventoinhas puxam o ar úmido por um leito de **cloreto de
   cálcio (CaCl₂)**, que retém a água quimicamente.
2. **Amanhecer — Isolamento:** um servo-registro fecha o ar e abre o duto da
   vidraria de destilação.
3. **Dia — Regeneração:** a **solenoide a 120 °C** libera a água como vapor.
4. **Destilação:** o vapor condensa na vidraria de laboratório reciclada.
5. **Pós-tratamento:** **filtro mineralizante** + **UV-C** tornam o destilado
   potável (alvo Ca 45 / Mg 18 mg/L).
6. **Armazenamento:** **bacia com torneira** (1–2 L/ciclo).

## Arquitetura

O mapa completo, contratos de dados e guia de extensão estão em
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Em resumo: **um núcleo C++23
header-only** é a fonte única de verdade física; CLI, studio, pybind11, serviço
Flask e firmware consomem os mesmos contratos; os **scripts Python** produzem
mídia, relatórios e o pipeline de dados.

```
             src/core (tupan_core.hpp — física única)
                 │        │              │            │
     tupan_sim ──┘  tupan_studio   tupan_native   tupan_script
                    (Lua+ImGui+GL)   (pybind11)     (luaaa)
                                                       │
                                  tools/pipeline · tools/server · tools/geradores
```

## Tupan Studio (Lua + ImGui + OpenGL)

`src/studio` é uma aplicação 3D interativa em que a interface é definida por um
**DSL Lua** (`src/studio/assets/studio.lua`) com cara de JSON: menus, painéis e
a cena 3D são tabelas declarativas — **sem recompilar** para mudar a UI.

- **Álgebra linear própria** (`math.hpp`): `Real = float`, `Mat4` column-major
  `alignas(16)` com `union` (colunas/floats), operações `constexpr`.
- **sol2** lê o DSL; **Dear ImGui** + **GLFW** + **OpenGL 3.3** desenham widgets
  e cena; ações de menu passam por uma tabela de **lambdas**.
- **Carga de CAD/3D** (`mesh_loader.cpp`): `shape = "model"` + `file = "...stl"`
  renderiza malhas STL/OBJ reais (normalizadas para caixa unitária; `pos`/`size` valem).
- **luaaa** (`src/scripting`) expõe o núcleo ao Lua headless (`tupan.*`).

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
./build/tupan_studio          # janela interativa
./build/tupan_script          # roda src/scripting/scripts/ciclo.lua
```

## Estrutura do Projeto

```
Tupan Water Maker/
├── CMakeLists.txt              # build raiz (núcleo + studio + scripting)
├── README.md / README.pt-BR.md
├── docker/Dockerfile           # multi-stage: build | core | web
├── ci/Jenkinsfile              # pipeline CI/CD
├── src/                        # CÓDIGO
│   ├── core/                   # núcleo C++23 + CLI + testes
│   ├── studio/                 # Lua(sol2) + Dear ImGui + OpenGL
│   ├── scripting/              # runner Lua headless (luaaa)
│   ├── bindings/               # módulo Python (pybind11)
│   └── firmware/               # Arduino Mega (C++20, MVC/FSM)
├── tools/                      # geradores, midia, pipeline, cad, server, tests
├── data/                       # raw/ · processed/ · results/
├── docs/                       # relatorios/ · pitch/ · manuais/ · midia/
├── scripts/                    # build-linux.sh · build-windows.bat · docker · k8s
└── deploy/                     # k8s/ · vps/
```

## Destaques Técnicos

| Área | Detalhe |
|------|---------|
| **Ciclo da água** | Sorção noturna CaCl₂ → solenoide ~120 °C → destilação → filtro + UV-C → bacia com torneira |
| **Microcontrolador** | Arduino Mega 2560 (ATmega2560) |
| **Firmware** | C++20, MVC, FSM (OCIOSO/INTAKE/REGEN/DESTIL/CHEIO/ERRO) |
| **Núcleo** | C++23 header-only, `-Wall -Wextra -Wpedantic`; testes via CTest |
| **Studio** | Lua DSL (sol2) + Dear ImGui + OpenGL 3.3; álgebra com `union`; carrega malhas STL/OBJ; luaaa headless |
| **Simuladores** | CLI + studio + pybind11 + Flask — paridade física (0,68 L potável @ UR 68 %/24 °C) |
| **Pipeline de dados** | ERA5/Open-Meteo (14.616 h) + ridge/MLP, R² 0.991, RMSE 0.064 L |
| **Energia** | 1,683 kWh/ciclo, 0,43 L/kWh; R$ 2,36/L (rede) e R$ 0,83/L (TSEE) |
| **Comunicação** | Bluetooth HC-05 (UART) + MQTT |
| **Entrega** | Docker multi-stage + Jenkins → K8s/HPA ou VPS (systemd+nginx) |
| **Custo estimado** | ~R$ 447 em peças novas (~R$ 503 em reutilizadas) |

## Como Começar

### Requisitos
- Python 3.10+; toolchain GNU com C++23; CMake ≥ 3.25
- Studio/scripting: GLFW3, GLEW, Lua 5.4 (sol2, Dear ImGui e luaaa baixados pelo CMake)
- Arduino IDE ou PlatformIO para o firmware

### Compilar núcleo, CLI, studio e testes
```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
./build/tupan_sim --night 8 --day 6 --ur 68 --temp 24 --json
./build/tupan_studio
./build/tupan_script
```

### Pipeline de dados (clima + ML + custo)
```bash
python3 tools/pipeline/analise_dados.py
python3 tools/pipeline/custo_energia.py
```

### Simulador web
```bash
python3 tools/server/simulador_tupan.py   # http://127.0.0.1:5000
```

### Firmware (Arduino Mega 2560)
```bash
cd src/firmware && pio run
```

### Regenerar mídia, relatório e pitch
```bash
python3 tools/midia/gerar_imagens.py
python3 tools/midia/gerar_mapas.py
python3 tools/geradores/gerar_relatorio.py
python3 tools/geradores/gerar_pitch.py
python3 tools/cad/gerar_cad.py        # DXF/STL/SCAD + prancha técnica
```

## Docker e CI/CD

```bash
scripts/build-docker.sh --target web --tag dev
docker compose up --build
scripts/deploy-k8s.sh --registry ghcr.io/tuliofh --tag 0.1.0
```

- **Imagens:** `docker/Dockerfile` (alvos `core`, `web`), gunicorn + `/health`.
- **Kubernetes:** `deploy/k8s/` (namespace, deployment, service, ingress, HPA).
- **VPS:** `deploy/vps/` (systemd + nginx).
- **Jenkins:** `ci/Jenkinsfile` (build, testes, mídia, push, deploy).
- **GitHub Actions:** `.github/workflows/ci.yml`.
- **Standalone (sem interpretador):** `scripts/build-standalone.sh` → `dist/standalone/tupan-web` (PyInstaller).

## Mídia e Documentação

Toda a mídia gerada fica em `docs/midia/`: `renders/`, `graficos/`, `mapas/`,
`mockups/`, `diagramas/`, `cad/`. Entregáveis:
`docs/relatorios/relatorio_descritivo.docx` (artigo ABNT),
`docs/pitch/apresentacao_produto.pptx` e o artigo do LinkedIn
`docs/relatorios/artigo.txt`. Manuais: [PT-BR](docs/manuais/manual_pt-br.md) e [EN](docs/manuais/manual_en-us.md).

## Filosofia de Sustentabilidade

O Tupan é projetado **exclusivamente para consumo humano direto** (1–2 L/ciclo),
não para uso industrial. Alinha-se aos ODS **6** (Água Potável e Saneamento),
**3** (Saúde e Bem-Estar) e **12** (Produção e Consumo Responsáveis).

## Licença

Distribuído sob a [Licença MIT](LICENSE) — © 2026 Túlio Ferreira Horta.
Os entregáveis acadêmicos (relatório e pitch) permanecem para fins acadêmicos.

## Contato

**Túlio Ferreira Horta**
- PUC-MG — Engenharia de Computação
- Disciplina: IoT & PLCs (2026.2)

---

*Palavras-chave: gerador de água atmosférica, AWG, água do ar, Tupan, máquina de
chuva, semiárido brasileiro, Arduino Mega, C++23, Lua, Dear ImGui, OpenGL, luaaa,
Docker, Kubernetes, Jenkins, sorção por cloreto de cálcio, destilação, UV,
filtro mineralizante, IoT, MQTT, Bluetooth HC-05, Flask, pybind11, PUC-MG.*
