# Tupan, Máquina de Chuva — Manual de Uso e Montagem (PT-BR)

> **Feito para o sertão.** Este manual descreve a montagem da máquina e o uso
> de todo o software do projeto. O Tupan foi desenhado para a realidade do
> **semiárido nordestino brasileiro** — e, como mostrado na seção 7, esse
> mesmo desenho funciona (com adaptações) em biomas irmãos na África, Europa
> e América do Norte.

**Versão:** 1.0 · **Licença:** MIT · **Autores:** Túlio Ferreira Horta (PUC-MG, IoT & PLCs 2026.2)

---

## 1. Para quem é este manual

- **Famílias e comunidades rurais do Nordeste** que convivem com caminhão-pipa,
  poços salobros e secas recorrentes;
- **Escolas técnicas, IFs e makers** que queiram replicar o projeto como
  plataforma de ensino (física + eletrônica + software);
- **Docentes e extensionistas** que atuem em tecnologias sociais hídricas.

O Tupan produz **~0,68 L de água potável por ciclo noturno** (média climática
de Petrolina-PE), consumindo **~1,7 kWh por ciclo**. Não é para encher caixa
d'água: é para **hidratação digna e autônoma**, complemento à pipa, cisterna e
dessalinizador.

---

## 2. O ciclo em 1 minuto (entender antes de montar)

```
NOITE (20h–6h)              AMANHECER                DIA (6h–12h)          PÓS
┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────┐
│ Ventoinhas puxam │  │ Servo fecha a    │  │ Solenoide aquece  │  │ Filtro mini- │
│ ar úmido pelo    │→ │ entrada de ar e  │→ │ o sal úmido a     │→ │ mineralizante│
│ leito de CaCl₂   │  │ abre o duto da   │  │ 120 °C; água sai  │  │ + UV-C →     │
│ (sorção química) │  │ vidraria         │  │ como vapor puro   │  │ bacia 2 L    │
└─────────────────┘  └──────────────────┘  └───────────────────┘  └──────────────┘
```

- O **cloreto de cálcio (CaCl₂)** é a esponja química: retém a água do ar à
  noite e a devolve como vapor quando aquecido. **Não é consumido** — seca-se
  e volta a funcionar (troca total só a cada 2–3 anos por impurezas).
- **Sem compressor, sem refrigeração, sem bomba.** As peças móveis são
  ventoinhas (comuns, baratas) e 1 servo motor.

---

## 3. O que há no repositório

```
Tupan/
├── README.md / README.pt-BR.md   # visão geral (EN / PT-BR)
├── CMakeLists.txt                # build raiz (núcleo + studio + scripting)
├── src/                          # CÓDIGO
│   ├── core/         # núcleo C++23 (física) + CLI + testes
│   ├── studio/       # UI: DSL Lua (sol2) + Dear ImGui + OpenGL + math.hpp
│   ├── scripting/    # runner Lua headless (luaaa)
│   ├── bindings/     # módulo Python (pybind11)
│   └── firmware/     # Arduino Mega (C++20, MVC + FSM)
├── tools/                        # SCRIPTS por propósito
│   ├── geradores/    # relatório, pitch, diagramas UML
│   ├── midia/        # geradores de imagens, mapas e mockups
│   ├── pipeline/     # clima/ML + custo de energia
│   ├── cad/          # esquemático elétrico
│   ├── server/       # simulador web Flask (+ templates/)
│   └── tests/        # testes unitários (pytest)
├── data/                         # raw/ · processed/ · results/
├── docs/                         # ENTREGÁVEIS
│   ├── relatorios/   # relatório .docx, artigo LinkedIn (artigo.txt)
│   ├── pitch/        # apresentação .pptx
│   ├── manuais/      # este manual
│   └── midia/        # renders/ graficos/ mapas/ mockups/ diagramas/ cad/
├── scripts/                      # build-linux.sh, build-windows.bat, docker, k8s
├── deploy/                       # k8s/ (manifests) e vps/ (systemd + nginx)
└── ci/                           # Jenkinsfile (+ GitHub Actions)
```

---

## 4. Como usar o SOFTWARE

### 4.1 Simulador nativo (C++23) — física de referência

Requisitos: g++ ≥ 13 (C++23), CMake ≥ 3.25. Para o studio: GLFW3, GLEW e Lua 5.4
(sol2, Dear ImGui e luaaa são baixados pelo CMake). A GUI Qt5 foi removida.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
./build/tupan_tests               # testes do núcleo — todos devem passar
./build/tupan_sim --night 8 --day 6 --ur 68 --temp 24
./build/tupan_sim --json          # saída máquina (integração)
./build/tupan_studio              # UI interativa: Lua + ImGui + OpenGL
./build/tupan_script              # script Lua headless (módulo tupan.*)
```

Saída típica (condições médias de Petrolina):

```
  noite: UR 68% | 24 °C | 25 m³/h | η 0.85 → 0.75 kg sorvidos no leito
  dia  : solenoide 120 °C → 0.69 L destilados na vidraria
  pós  : filtro mineralizante (Ca 45/Mg 18 mg/L) + UV-C → 0.68 L na bacia
  conta: 0.43 L/kWh
```

O **Tupan Studio** lê a interface de `src/studio/assets/studio.lua` (DSL com
cara de JSON: menus, painéis e objetos 3D). Edite o `.lua` e use o menu
**Arquivo → Recarregar DSL** — sem recompilar. Ele também **carrega CAD/3D
reais** (STL/OBJ): use `shape = "model"` e `file = "docs/midia/cad/tupan_pecas.stl"`.
Para regenerar o CAD: `python3 tools/cad/gerar_cad.py` (DXF/STL/SCAD + prancha).

### 4.2 Simulador web (Flask) — para experimentar sem hardware

Requisitos: Python ≥ 3.10, `flask` (`pip install -r requirements.txt`).

```bash
cd tools/server
python3 simulador_tupan.py        # http://127.0.0.1:5000
```

Na tela: arraste UR, temperatura, vazão e temperatura da solenoide; clique
**"Executar ciclo completo"**; a sala animada mostra ar noturno → leito →
vapor → vidraria → filtro/UV → bacia. A tabela "frota" permite simular
vários Tupans.

### 4.3 Esteira de dados (clima real + ML + custo)

```bash
cd tools/pipeline
python3 analise_dados.py     # baixa ERA5/Open-Meteo de Petrolina-PE, treina ML,
                             # gera data/results/projetoes_tupan.csv e metricas_ml.json
python3 custo_energia.py     # custo elétrico com tarifas médias ANEEL +
                             # bandeiras + Tarifa Social → data/results + data/processed
```

Números de referência: UR noturna média **68,6 %** @ 24,6 °C; projeção
**594 L/ano** por unidade; ML R² = 0,991; custo **R$ 2,36–2,38/L** na rede
ou **R$ 0,83/L** com Tarifa Social (65 % de desconto, consumo ≈ 51 kWh/mês,
dentro da faixa ≤ 80 kWh).

### 4.4 Firmware (Arduino Mega 2560)

Abra `src/firmware/` na Arduino IDE (ou `pio run` com PlatformIO).
Arquivos: `tupan_firmware.hpp` (toda a lógica MVC/FSM) e `main.cpp` (entrada).

- Console serial **115200 baud** imprime `LOG_*` de toda transição:
  `[CICLO] fsm: INTAKE` → `[INFO ] sorcao: kg=0.741` → `[CICLO] destil: ml=1240`.
- Sensores/atuadores são **stubs bem marcados** (`// STUB`) — troque pelos
  seus drivers reais (DHT22, DS18B20, servo, MOSFET) sem tocar na FSM.
- Estados: `OCIOSO → INTAKE → REGEN → DESTIL → CHEIO/ERRO`.

### 4.5 Testes

```bash
./build/tupan_tests                       # testes C++ (CTest)
cd tools/tests && python3 -m pytest -q    # testes Python
```

Os testes Python rodam contra o módulo nativo quando compilado e contra o
fallback Python quando não — **paridade física garantida**.

### 4.6 Empacotamento standalone (sem Python no destino)

Para distribuir sem instalar Python, gere UM executável do serviço web:

```bash
pip install pyinstaller
scripts/build-standalone.sh          # → dist/standalone/tupan-web
./dist/standalone/tupan-web          # serve http://127.0.0.1:5000
```

A imagem Docker (`docker/Dockerfile`, alvo `web`) é a alternativa em contêiner.
Manual em inglês: `docs/manuais/manual_en-us.md`.

---

## 5. COMO MONTAR A MÁQUINA

### 5.1 Lista de materiais (BOM) — alvo ≈ R$ 450 em peças novas

| # | Item | Especificação | Qtd | Preço estimado |
|---|------|---------------|-----|----------------|
| 1 | Arduino Mega 2560 (ou clone) | ATmega2560 | 1 | R$ 120 (comum já possuir) |
| 2 | Ventoinha 12 V | 120 mm, ~2,5 W cada | 3 | R$ 30 |
| 3 | Solenoide/ Resistência | 250 W, 12/24 V com dissipador | 1 | R$ 60 |
| 4 | Servo motor | MG996R (registo de ar) | 1 | R$ 35 |
| 5 | MOSFET + driver | IRLZ44N ×2 (fans, solenoide) | 2 | R$ 12 |
| 6 | DHT22 | UR + temperatura | 1 | R$ 40 |
| 7 | DS18B20 | prova d'água ×2 (leito, vapor) | 2 | R$ 30 |
| 8 | Sensor de nível capacitivo | XKC-Y25-V | 1 | R$ 25 |
| 9 | Cloreto de cálcio | grau técnico, 2 kg | 1 | R$ 30 |
| 10 | Vidraria | balão/condensador de lab (reciclado) | 1 | R$ 0–80 |
| 11 | Filtro mineralizante | cartucho de reposição p/ purificador | 1 | R$ 45 |
| 12 | Lâmpada UV-C | 6 W, 254 nm + reator | 1 | R$ 40 |
| 13 | Fonte 12 V 30 A | 360 W | 1 | R$ 90 |
| 14 | Módulo Bluetooth | HC-05 (telemetria) | 1 | R$ 25 (comum já possuir) |
| 15 | Estrutura | PLA impresso + MDF/acrílico | — | R$ 30 |
| 16 | Bacia potável c/ torneira | 2 L, grau alimentício | 1 | R$ 15 |

**Já possuído com frequência:** Mega, HC-05, servos, ventoinhas, fios → custo
real típico cai para **~R$ 300–350**.

### 5.2 Fluxo de ar e montagem mecânica (ordem)

1. **Câmara do leito:** caixa de MDF/acrílico ~20×20×25 cm com bandeja
   perfurada no meio; preencha 2 kg de **pérolas de CaCl₂** (não use pó —
   compacta e estrangula o fluxo).
2. **Pleno de ventoinhas:** 3× 120 mm na entrada, com **filtro de ar** tipo
   janela de A/C (o poeira do sertão é inimiga nº 1 do sal).
3. **Servo-registro (damper):** na saída da câmara, um túnel único que o servo
   comuta entre (a) aberto p/ o ambiente (noite) e (b) fechado sobre o duto da
   vidraria (dia). Posição 0° = sorção; 90° = destilação.
4. **Duto de vapor → vidraria:** silicone/borossilato; balão de fundo redondo
   recebe o vapor, condensador Liebig horizontal esfria com ar (ou água se
   tiver). Incline **2–3°** para o condensado correr sozinho.
5. **Pós-tratamento:** saída do condensador → cartucho mineralizante →
   câmara UV-C (tubo de PVC transparente com a lâmpada 254 nm **fora** do
   fluxo, atravessando — nunca dentro d'água sem tubo quartzoluz) → bacia 2 L
   com torneira.
6. **Isolamento térmico:** lã de rocha ou manta cerâmica enrolada na câmara
   do leito (a regeneração a 120 °C não pode cozinhar a eletrônica).

### 5.3 Ligações elétricas (confere com `tupan_firmware.hpp`)

| Pino Mega | Sinal | Ligação |
|-----------|-------|---------|
| D2 | DHT22 (dados) | pull-up 10 kΩ |
| D3 / D4 | DS18B20 leito / vapor | pull-up 4,7 kΩ (OneWire) |
| A0 | sensor de nível | saída analógica 0–5 V |
| D5 | MOSFET ventoinhas (PWM) | gate c/ resistor 220 Ω |
| D6 | MOSFET/releu solenoide | **sempre via releu ou MOSFET — nunca direto** |
| D9 | servo-registro | fonte 5 V dedicada (pico de corrente) |
| A2/A3/A4 | botões cima/baixo/select | pull-up interno |
| D22/23/24 | LEDs verde/amarelo/vermelho | resistor 330 Ω |
| TX1/RX0 | HC-05 | divisor resistivo no RX do Mega |

**Segurança elétrica:** fonte 12 V chaveada em caixa ventilada; tudo de potência
(ventoinhas, solenoide) fora da proto do Mega; aterrar o chassi metálico da
solenoide; fusível 15 A na entrada da fonte.

### 5.4 Segurança — leia de novo

-  **120 °C:** superfícies do leito queimam. Isolamento + adesivo de alerta.
-  **UV-C 254 nm:** cega e queima pele. Câmara UV **totalmente opaca**;
  intertravamento (o firmware corta a UV quando a bacia é aberta).
-  **Água + eletrônica:** bacia e vidraria em compartimento separado do
  Mega; bandeja de gotejamento.
-  **Primeira água de cada leito novo:** descarte as 2 primeiras rodadas
  (sais residuais de manufatura) antes de consumir.

### 5.5 Comissionamento (primeiro dia)

1. Firmware gravado; console conectado; verifique `[CICLO] fsm: OCIOSO`.
2. Teste de vazão: `INTAKE` manual 30 min → log `sorcao: kg=` deve subir.
3. Teste térmico: `REGEN` com bacia fora → log `regen: t_leito=` deve chegar
   a 120 ± 2 °C e a histerese deve cortar a solenoide.
4. Destilação de validação: rode um ciclo completo; meça o volume na bacia;
   compare com `tupan_sim --night 8 --day 6` (esperado 0,6–0,7 L).
5. Assine a UV: verifique dose com cartão dosimétrico UV-C (opcional, mas
   recomendado antes do primeiro consumo).

---

## 6. Operação diária (rotina do usuário)

| Quando | O quê | Quem/Como |
|--------|-------|-----------|
| 20h | Abrir o registro de ar / plugar ou conferir agendamento | 1 clique no painel ou automático |
| 6h | Fechar registro; a máquina entra em REGEN sozinha | automático (FSM) |
| 12h | Bacia cheia: LED verde + torneira livre | beber |
| Semanal | Inspecionar filtro de poeira e gotejamentos | 2 min |
| Anual | Completar leito com CaCl₂ novo (reposição ~10 %) | 10 min |
| 2–3 anos | Troca total do leito; regenerar o sal velho > 150 °C e **entregar em ponto de coleta** | logística reversa |

---

## 7. Onde o Tupan funciona melhor — comparação de biomas

O desenho é calibrado no **semiárido brasileiro**, mas o ciclo de sorção/
regeneração depende de duas variáveis: **umidade noturna** (combustível) e
**calor diurno** (energia de regeneração). O mapa abaixo compara o sertão com
biomas irmãos nos três continentes citados:

| Região (bioma) | Clima Köppen | UR noturna típica | T noturna | Adequação do Tupan | Observações de adaptação |
|---|---|---|---|---|---|
| **Sertão nordestino (Brasil)** — Petrolina-PE, Juazeiro, Picos | BSh (árido quente c/ estação chuvosa curta) | **60–75 %** | 22–26 °C | ★★★★★ **ideal (projeto-base)** | Dados ERA5 embutidos no pipeline; 594 L/ano por unidade |
| **Sahel (África)** — Niamey, Ouagadougou, Kano | BSh, monção Jun–Set | 70–90 % na estação chuvosa; 25–40 % na seca (harmatão) | 24–30 °C | ★★★★☆ sazonal | Excelente Jun–Set; na seca, o harmatão carrega **poeira fina** → dobrar a manutenção do filtro e prever pré-filtro lavável; leito trocável |
| **Sahara / Arábia (deserto hiperárido)** | BWh | < 20 % | 15–30 °C | ★☆☆☆☆ inviável | Sem vapor no ar, não há o que sorver — aqui só dessalinização ou transporte |
| **Mediterrâneo (Europa)** — Andaluzia, Sicília, Grécia, Algarve | Csa (verão quente e seco) | 50–70 % (noites de verão) | 18–24 °C | ★★★☆☆ estacional | Rende bem Mai–Set; no inverno úmido a sorção funciona, mas a regeneração solar é fraca → janela de REGEN mais longa ou auxílio elétrico |
| **Sudoeste dos EUA / Norte do México** — Phoenix, Tucson, Sonora | BWh/BSh c/ monção Jul–Set | 30–50 % no monção; 10–25 % no resto | 20–30 °C | ★★☆☆☆ marginal | Só vale no monção; alternativa local: colheita de névoa no litoral da Califórnia (clima BSh/Csb com névoas noturnas 85 %+ seria ★★★★☆) |
| **Litoral árido da Costa Oeste (Atacama/Namibe)** | BWk c/ névoa costeira | 80–95 % | 12–20 °C | ★★★★☆ (com adaptação térmica) | UR altíssima, mas noites frias: a regeneração precisa de sol concentrado ou solenoide extra |

**Regras de bolso da adaptação:**
- UR noturna média ≥ 60 % → projeto-base funciona sem mudanças;
- 40–60 % → aumenta horas de INTAKE (10–12 h) e capacidade do leito;
- < 40 % → não instale; procure fonte alternativa;
- Ambientes com poeira (Sahel, sertão do Pajeú) → filtro lavável + troca
  anual do leito, **logística reversa do sal é obrigatória em escala**;
- Noites frias (Atacama, Mediterrâneo inverno) → REGEN mais longa; a
  solenoide assume o papel do sol.

[PT-BR] Resumo: o sertão nordestino não é o pior lugar do mundo para tirar
água do ar — é um dos melhores, porque a noite úmida e o dia quente ocorrem
no mesmo lugar, todo dia. O Sahel é quase um gêmeo; o Mediterrâneo é um
primo que rende menos no inverno; o deserto do Arizona é um primo seco que
só bebe no monção.

---

## 8. Solução de problemas

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| `sorcao: kg=` não sobe | filtro de ar saturado; leito compactado | limpar trocar filtro; soltar leito (pérolas, não pó) |
| `regen: t_leito=` não chega a 120 °C | isolamento insuficiente; solenoide fraca | reforçar manta; conferir 250 W @ tensão correta |
| `destil: ml=` baixo | duto com perdas; condensador quente | vedar com silicone; sombrear/arejar o condensador |
| Água sem gosto | filtro mineralizante esgotado | trocar cartucho (marcar data na estrutura) |
| `[CICLO] fsm: ERRO` | sensor fora | console indica qual; recupera com SELECT após conserto |
| Bacia nunca cheia | UR noturna < 50 % na sua região | rode `analise_dados.py` com sua cidade — o clima decide |

---

## 9. Garantia acadêmica e limites

- Protótipo **educacional**: antes de consumo rotineiro, valide a qualidade
  (parâmetros ANVISA; caminho de certificação INMETRO Portaria 344/2017 para
  produtos). O firmware já audita cada ciclo em log para essa finalidade.
- Números deste manual vêm do núcleo físico + ERA5; **seu clima manda** —
  rode a esteira de dados com a sua cidade antes de montar.
- Licença MIT para o software; o sal usado deve retornar a ponto de coleta
  (o relatório traz a seção de responsabilidade ambiental).
