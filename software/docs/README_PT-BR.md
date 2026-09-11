# Tupan, Máquina de Chuva

[![Read in English](https://img.shields.io/badge/EN-English-blue.svg)](../../README.md)

Gerador portátil de água atmosférica projetado para hidratação individual/em pequena escala em ambientes com escassez hídrica. O projeto combina microeletrônica (Arduino Mega), projeto de circuitos analógico-digitais, engenharia de sistemas e conectividade IoT.

## Origem do Projeto

O **Tupan, Máquina de Chuva** (anteriormente "Tupan Water Maker") foi concebido como projeto acadêmico para a disciplina **IoT & PLCs** da **PUC-MG** (Pontifícia Universidade Católica de Minas Gerais), Curso de Engenharia de Computação, semestre **2026.2**, por **Túlio Ferreira Horta**.

A ideia surgiu de uma preocupação compartilhada: a **escassez de água**. No semiárido brasileiro — onde vivem mais de 30 milhões de pessoas — os ciclos de seca são recorrentes e devastadores. Famílias dependem de caminhões-pipa, cisternas e aquíferos cada vez mais pressionados. O projeto explora se a tecnologia pode oferecer um **complemento descentralizado e de baixo custo** à infraestrutura existente.

O nome **"Tupan"** vem da palavra tupi-guarani para "trovão" ou "espírito divino" — uma referência à origem atmosférica da água e ao conhecimento indígena da terra.

## Por que a Documentação Está em Português

Toda a documentação oficial (relatórios, diagramas e entregáveis) está escrita em **Português (PT-BR)** porque:

- O projeto é um **requisito acadêmico** em uma universidade brasileira (PUC-MG).
- Os usuários e comunidades-alvo estão principalmente no **Brasil**, particularmente no semiárido nordestino.
- Normas legais brasileiras (CONAMA, ANVISA, CDC, LGPD) e marcos regulatórios são referenciados ao longo do material.
- O plano de ensino e os critérios de avaliação estão em português.

Este README, no entanto, está em **inglês** para tornar o projeto acessível a um público internacional e a potenciais colaboradores.

## Estrutura do Projeto

```
Tupan Water Maker/
├── README.md
├── Documentação Oficial/            # Entregáveis oficiais
│   ├── relatórioDescritivo.docx    # Relatório técnico (PT-BR)
│   ├── apresentaçãoProduto.pptx    # Apresentação de pitch
│   ├── Arquivo de Mídia/           # Imagens, gráficos, diagramas (+ fontes/)
│   └── Arquivos CAD/               # UML, esquemáticos, CAD (DXF/SVG/STL, + fontes/)
└── Coleção de Software/             # Código-fonte
    ├── docs/                       # README_PT-BR.md
    └── scripts/                    # TODO Python: geradores, simulador, CAD, testes
        ├── testes/                 # Testes unitários (pytest)
        ├── templates/              # Interface web do simulador (Flask)
        ├── dist/                   # Simulador nativo C++20/pybind11 + builds
        ├── requirements.txt
        ├── setup.py
        └── pyproject.toml
```

## Principais Destaques Técnicos

| Área | Detalhe |
|------|---------|
| **Microcontrolador** | Arduino Mega 2560 (ATmega2560) |
| **Firmware** | C++20 com arquitetura MVC, Máquina de Estados Finitos |
| **Comunicação** | Bluetooth HC-05 (UART) + ponte MQTT |
| **Alimentação** | Dual: bateria de carro 12V (60Ah) + carregador 110/220V CA |
| **Sensores** | DHT22 (temp/umidade), DS18B20, BMP280, sensor de nível |
| **Atuadores** | Ventilador, bomba, relés, válvula solenóide (via SSR/MOSFET) |
| **Materiais** | Vidraria de laboratório reciclada, impressão 3D, sucata eletrônica |
| **Custo estimado** | ~R$ 527,00 em peças (+ ~R$ 503,00 em componentes já próprios/reutilizados) |

## Filosofia de Sustentabilidade

O Tupan é projetado **exclusivamente para consumo humano direto** (1–2 litros por ciclo), não para uso industrial. Está alinhado aos Objetivos de Desenvolvimento Sustentável da ONU:

- **ODS 6** — Água Potável e Saneamento
- **ODS 3** — Saúde e Bem-Estar
- **ODS 12** — Produção e Consumo Responsáveis

## Como Começar

### Requisitos
- Python 3.10+
- `python-docx`, `matplotlib`, `python-pptx`, `Pillow`, `flask`, `scikit-learn`
- Arduino IDE para desenvolvimento do firmware

### Regenerar o Relatório
```bash
cd "Coleção de Software/scripts"
python3 gerar_relatorio.py
```

### Regenerar o Pitch
```bash
cd "Coleção de Software/scripts"
python3 gerar_pitch.py
```

### Regenerar Diagramas (PlantUML)
```bash
cd "Coleção de Software/scripts"
python3 gerar_diagramas.py
```

### Regenerar CAD (esquemático DXF/SVG/PNG + carcaça STL)
```bash
cd "Coleção de Software/scripts"
python3 esquema_eletrico.py
python3 gerar_mecanica.py
```

### Mockups do Simulador (Chromium headless)
```bash
cd "Coleção de Software/scripts"
python3 gerar_mockups.py
```

### Simulador Nativo (C++20, scripts/dist)
```bash
cd "Coleção de Software/scripts/dist"
./build.sh && ./bin/tupan_sim --help
```

### Executar o Simulador Web
```bash
cd "Coleção de Software/scripts"
python3 simulador_tupan.py
# Acesse http://127.0.0.1:5000 no navegador
```

## Licença

Este projeto destina-se **exclusivamente a fins acadêmicos**. O uso comercial não autorizado é proibido.

## Contato

**Túlio Ferreira Horta**
- PUC-MG — Engenharia de Computação
- Disciplina: IoT & PLCs (2026.2)