<!-- ======================================================================
SEO / META (para cópias renderizadas fora do GitHub — o GitHub sanitiza
meta tags, mas indexa todo o texto deste arquivo):
title: Tupan, Máquina de Chuva — Gerador de Água Atmosférica (sem compressor)
description: Gerador de água atmosférica (AWG) sem compressor para o
  semiárido brasileiro: sorção noturna com cloreto de cálcio, regeneração
  por solenoide, destilação em vidraria, esterilização UV e filtro
  mineralizante. Firmware Arduino Mega em C++20, pipeline de dados em
  Python, simulador web Flask e app IoT via Bluetooth/MQTT.
keywords: gerador de água atmosférica, AWG, água do ar, Tupan, máquina de
  chuva, semiárido, Petrolina, PUC-MG, Arduino Mega, C++20, Python, IoT,
  MQTT, Bluetooth HC-05, cloreto de cálcio, CaCl2, sorção, dessicante,
  destilação, esterilização UV, filtro mineralizante, Flask, pybind11,
  scikit-learn, PyTorch, Monte Carlo, FSM, MVC
author: Túlio Ferreira Horta
robots: index, follow
====================================================================== -->

<div align="center">

# Tupan, Máquina de Chuva

**Gerador de Água Atmosférica (AWG) · Arduino Mega · C++20 · Python · IoT**

*In English: Tupan, Rain Machine — compressor-free atmospheric water
generator for water-scarce regions.*

[![Licença: MIT](https://img.shields.io/badge/Licença-MIT-yellow.svg)](../../LICENSE)
[![EN](https://img.shields.io/badge/docs-English-blue.svg)](../../README.md)
[![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C.svg)](../scripts/dist/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](../scripts/)
[![Arduino Mega 2560](https://img.shields.io/badge/Placa-Arduino%20Mega%202560-teal.svg)](../firmware/)

</div>

Gerador portátil de água atmosférica **sem compressor**, projetado para
hidratação individual e em pequena escala em ambientes com escassez hídrica —
construído com microeletrônica (Arduino Mega), firmware C++20, pipeline de
dados em Python, simulador web Flask e conectividade IoT (Bluetooth HC-05 +
MQTT).

## Sumário

- [Origem do Projeto](#origem-do-projeto)
- [Como Funciona (sem compressor)](#como-funciona-sem-compressor)
- [Por que a Documentação está em Português](#por-que-a-documentação-está-em-português)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Destaques Técnicos](#destaques-técnicos)
- [Filosofia de Sustentabilidade](#filosofia-de-sustentabilidade)
- [Como Começar](#como-começar)
- [Licença](#licença)
- [Contato](#contato)

## Origem do Projeto

O **Tupan, Máquina de Chuva** (anteriormente "Tupan Water Maker") foi concebido
como projeto acadêmico para a disciplina **IoT & PLCs** da **PUC-MG**
(Pontifícia Universidade Católica de Minas Gerais), curso de Engenharia de
Computação, semestre **2026.2**, por **Túlio Ferreira Horta**.

A ideia surgiu de uma preocupação compartilhada: a **escassez de água**. No
semiárido brasileiro — onde vivem mais de 30 milhões de pessoas — os ciclos de
seca são recorrentes e devastadores. Famílias dependem de caminhões-pipa,
cisternas e aquíferos cada vez mais pressionados. O projeto explora se a
tecnologia pode oferecer um **complemento descentralizado e de baixo custo** à
infraestrutura existente.

O nome **"Tupan"** vem da palavra tupi-guarani para "trovão" ou "espírito
divino" — uma referência à origem atmosférica da água e ao conhecimento
indígena da terra.

## Como Funciona (sem compressor)

O Tupan evita deliberadamente compressores e estágios de resfriamento. Ele
explora o **pico de umidade noturna** do semiárido com um ciclo químico-térmico:

1. **Noite — Sorção (INTAKE):** ventoinhas puxam o ar noturno úmido por um
   leito de **cloreto de cálcio (CaCl₂)**, que retém a água quimicamente.
2. **Amanhecer — Isolamento (servo-registro):** o servo motor fecha a entrada
   de ar e abre o caminho para o duto de destilação na vidraria.
3. **Dia — Regeneração (REGEN):** a **solenoide aquecedora** eleva o sal úmido
   a ~120 °C, liberando a água como vapor.
4. **Destilação (DESTIL):** o vapor condensa em vidraria de laboratório
   reciclada, virando água líquida.
5. **Pós-tratamento:** o destilado passa por **filtro mineralizante** e
   **luz UV** para esterilização.
6. **Armazenamento:** a água potável é armazenada em uma pequena **bacia com
   torneira**.

## Por que a Documentação está em Português

Toda a documentação oficial (relatórios, diagramas e entregáveis) está escrita
em **Português (PT-BR)** porque:

- O projeto é um **requisito acadêmico** em uma universidade brasileira (PUC-MG).
- Os usuários e comunidades-alvo estão principalmente no **Brasil**,
  particularmente no semiárido nordestino.
- Normas legais brasileiras (CONAMA, ANVISA, CDC, LGPD) e marcos regulatórios
  são referenciados ao longo do material.
- O plano de ensino e os critérios de avaliação estão em português.

Este README em português é a tradução do
[README principal (em inglês)](../../README.md), para acessibilidade
internacional do projeto.

## Estrutura do Projeto

```
Tupan Water Maker/
├── README.md                          # README principal (EN)
├── LICENSE                            # MIT
├── documentacao/                      # Entregáveis oficiais
│   ├── relatórioDescritivo.docx       # Relatório técnico (PT-BR)
│   ├── apresentaçãoProduto.pptx       # Apresentação de pitch
│   ├── midia/                         # Imagens, gráficos, diagramas (+ fontes/)
│   └── cad/                           # CAD: DXF/SVG/STL (+ fontes/)
└── software/
    ├── docs/README_PT-BR.md           # Este arquivo
    ├── scripts/                       # TODO Python: geradores, simulador, testes
    │   ├── testes/                    # Testes unitários (pytest)
    │   ├── templates/                 # Interface web do simulador (Flask)
    │   └── dist/                      # Simulador nativo C++20/pybind11
    ├── dados/                         # Dados de clima, projeções, métricas ML
    └── firmware/                      # Firmware MVC C++20 (Arduino Mega)
```

## Destaques Técnicos

| Área | Detalhe |
|------|---------|
| **Ciclo da água** | Sorção noturna com CaCl₂ → regeneração por solenoide (~120 °C) → destilação em vidraria → filtro mineralizante + UV → bacia com torneira |
| **Microcontrolador** | Arduino Mega 2560 (ATmega2560) |
| **Firmware** | C++20, arquitetura MVC, máquina de estados finita (OCIOSO/INTAKE/REGEN/DESTIL/CHEIO/ERRO) |
| **Simuladores** | CLI/GUI nativo C++20 (Qt5) + simulador web pybind11 (Flask) — paridade física verificada |
| **Pipeline de dados** | pandas + scikit-learn + PyTorch sobre 14.616 h de dados ERA5/Open-Meteo (Petrolina-PE) |
| **Comunicação** | Bluetooth HC-05 (UART) + ponte MQTT |
| **Sensores** | DHT22 (temp/umidade), DS18B20 (leito/vapor), nível capacitivo |
| **Atuadores** | Ventoinhas PWM, solenoide aquecedora, servo-registro (sem compressor, sem bomba) |
| **Materiais** | Vidraria de laboratório reciclada, impressão 3D em PLA, sucata eletrônica |
| **Custo estimado** | ~R$ 447 em peças novas (~R$ 503 em componentes próprios/reutilizados) |

## Filosofia de Sustentabilidade

O Tupan é projetado **exclusivamente para consumo humano direto** (1–2 litros
por ciclo), não para uso industrial. Está alinhado aos Objetivos de
Desenvolvimento Sustentável da ONU:

- **ODS 6** — Água Potável e Saneamento
- **ODS 3** — Saúde e Bem-Estar
- **ODS 12** — Produção e Consumo Responsáveis

## Como Começar

### Requisitos
- Python 3.10+, toolchain GNU com C++20/23, CMake, Qt5 (para a GUI nativa)
- Arduino IDE ou PlatformIO para o firmware

### Pipeline de dados (clima + ML, Petrolina-PE)
```bash
cd "software/scripts"
python3 analise_dados.py
```

### Simulador Nativo (C++20, software/scripts/dist)
```bash
cd "software/scripts/dist"
./build.sh && ./bin/tupan_sim --help
```

### Executar o Simulador Web
```bash
cd "software/scripts"
python3 simulador_tupan.py
# Acesse http://127.0.0.1:5000 no navegador
```

### Firmware (Arduino Mega 2560)
```bash
cd "software/firmware"
pio run            # ou abra tupan_firmware.hpp + main.cpp na Arduino IDE
```

### Regenerar artefatos de documentação
```bash
cd "software/scripts"
python3 gerar_relatorio.py      # relatório ABNT (PT-BR + EN)
python3 gerar_pitch.py          # apresentação de pitch
python3 diagramas_uml.py        # diagramas PlantUML
python3 esquema_eletrico.py     # esquemático elétrico (DXF/SVG/PNG)
python3 gerar_imagens.py        # mídia (imagens/gráficos)
```

## Licença

Distribuído sob a [Licença MIT](../../LICENSE) — © 2026 Túlio Ferreira Horta.
Os entregáveis acadêmicos (relatório e pitch) permanecem para fins acadêmicos.

## Contato

**Túlio Ferreira Horta**
- PUC-MG — Engenharia de Computação
- Disciplina: IoT & PLCs (2026.2)

---

*Palavras-chave: gerador de água atmosférica, AWG, água do ar, atmospheric
water generator, Tupan, máquina de chuva, semiárido brasileiro, Arduino Mega,
firmware C++20, sorção por cloreto de cálcio, dessicante, destilação,
esterilização UV, filtro mineralizante, IoT, MQTT, Bluetooth HC-05, Flask,
pybind11, scikit-learn, PyTorch, simulação de Monte Carlo, PUC-MG.*
