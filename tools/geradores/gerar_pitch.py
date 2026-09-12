#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Gerador do PITCH (PPTX)
=============================================================================
DIDÁTICA: este script monta a apresentação comercial/acadêmica em PowerPoint,
sempre a partir das MÍDIAS geradas em `docs/midia/` (renders, gráficos, mapas,
mockups). Assim o pitch nunca "envelhece": rode os geradores de mídia e depois
este arquivo para reconstruir a apresentação inteira.

Uso:  python3 tools/geradores/gerar_pitch.py
Saída: docs/pitch/apresentacao_produto.pptx
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ---------------------------------------------------------------------------
# CAMINHOS — o gerador vive em tools/geradores/ (raiz = parents[2]).
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[2]
DOCS = BASE / "docs"
MEDIA = DOCS / "midia"
RENDERS = MEDIA / "renders"
GRAF = MEDIA / "graficos"
MAPAS = MEDIA / "mapas"
MOCKUPS = MEDIA / "mockups"
OUT = DOCS / "pitch" / "apresentacao_produto.pptx"

# Paleta única do projeto (mesma dos gráficos/renders).
AZUL = RGBColor(30, 58, 95)
AZUL_CLARO = RGBColor(220, 234, 247)
AZUL_MEDIO = RGBColor(64, 112, 160)
VERDE = RGBColor(46, 125, 50)
VERDE_CLARO = RGBColor(226, 239, 218)
LARANJA = RGBColor(230, 81, 0)
LARANJA_CLARO = RGBColor(255, 224, 200)
CINZA = RGBColor(89, 89, 89)
CINZA_CLARO = RGBColor(242, 242, 242)
BRANCO = RGBColor(255, 255, 255)
AMARELO = RGBColor(255, 193, 7)
ROXO = RGBColor(92, 44, 111)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


# ===========================================================================
# FUNÇÕES AUXILIARES — blocos reutilizáveis de layout
# ===========================================================================
def set_bg(slide, color=BRANCO) -> None:
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def add_text(slide, text, x, y, w, h, size=24, color=AZUL, bold=False,
             align=PP_ALIGN.LEFT, font="Arial", italic=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    return box


def add_bullets(slide, items, x, y, w, h, size=15, color=CINZA, spacing=0.42):
    """Lista com marcadores — evita repetir um textbox por linha."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = f"• {item}"
        r.font.name = "Arial"
        r.font.size = Pt(size)
        r.font.color.rgb = color
        p.space_after = Pt(spacing * 4)
    return box


def add_title(slide, title, subtitle=None):
    add_text(slide, title, 0.6, 0.35, 12.0, 0.7, size=30, color=AZUL, bold=True)
    if subtitle:
        add_text(slide, subtitle, 0.62, 1.05, 12.0, 0.4, size=13, color=CINZA, italic=True)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.45), Inches(1.2), Inches(0.08))
    line.fill.solid()
    line.fill.fore_color.rgb = VERDE
    line.line.fill.background()


def add_footer(slide, num) -> None:
    add_text(slide, "Tupan, Máquina de Chuva | PUC-MG Engenharia de Computação", 0.5, 7.15, 10, 0.25, size=8, color=CINZA)
    add_text(slide, str(num), 12.4, 7.15, 0.4, 0.25, size=8, color=CINZA, align=PP_ALIGN.RIGHT)


def add_circle(slide, text, x, y, d, fill_color, text_color=BRANCO, size=18):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = fill_color
    tf = shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = "Arial"
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = text_color
    return shape


def add_rect(slide, text, x, y, w, h, fill_color, text_color=BRANCO, size=14, bold=True):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = fill_color
    tf = shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = "Arial"
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = text_color
    return shape


def add_arrow(slide, x1, y1, x2, y2, color=AZUL_MEDIO, width=2):
    line = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    line.line.color.rgb = color
    line.line.width = Pt(width)
    line.line.end_arrowhead = True
    return line


def add_image(slide, path, x, y, w, h=None):
    slide.shapes.add_picture(str(path), Inches(x), Inches(y),
                             width=Inches(w), height=(Inches(h) if h else None))


def caption(slide, text, x, y, w, color=CINZA, size=10):
    add_text(slide, text, x, y, w, 0.3, size=size, color=color, italic=True, align=PP_ALIGN.CENTER)


def new_slide(bg=BRANCO):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s, bg)
    return s


# ===========================================================================
# SLIDE 1 — CAPA
# ===========================================================================
slide = new_slide(AZUL)
for y, c in [(5.6, RGBColor(46, 78, 120)), (6.0, VERDE), (6.4, AZUL_MEDIO)]:
    wave = slide.shapes.add_shape(MSO_SHAPE.ARC, Inches(-1), Inches(y), Inches(15), Inches(2.0))
    wave.fill.solid()
    wave.fill.fore_color.rgb = c
    wave.fill.transparency = 40
    wave.line.fill.background()
add_text(slide, "TUPAN", 0.7, 1.0, 12.0, 1.2, size=64, color=BRANCO, bold=True, align=PP_ALIGN.CENTER)
add_text(slide, "MÁQUINA DE CHUVA", 0.7, 2.15, 12.0, 0.8, size=32, color=AZUL_CLARO, bold=True, align=PP_ALIGN.CENTER)
add_text(slide, "Água potável do ar — sem compressor, sem gás refrigerante.",
         1.0, 3.25, 11.3, 0.6, size=20, color=BRANCO, align=PP_ALIGN.CENTER)
add_text(slide, "CaCl₂ → solenoide 120 °C → destilação → filtro mineralizante + UV-C",
         1.0, 4.0, 11.3, 0.4, size=13, color=AZUL_CLARO, align=PP_ALIGN.CENTER)
add_text(slide, "PUC-MG · Engenharia de Computação · IoT & PLCs (2026.2)",
         1.0, 5.0, 11.3, 0.35, size=12, color=BRANCO, align=PP_ALIGN.CENTER)
add_text(slide, "Túlio Ferreira Horta", 1.0, 5.5, 11.3, 0.35, size=12, color=BRANCO, align=PP_ALIGN.CENTER)
add_footer(slide, 1)

# ===========================================================================
# SLIDE 2 — O PROBLEMA
# ===========================================================================
slide = new_slide()
add_title(slide, "O PROBLEMA", "Escassez hídrica e o custo da água no semiárido")
for i, (lab, txt, cor) in enumerate([
        ("SECA", "Ciclos de estiagem recorrentes", LARANJA),
        ("SAL", "Aquíferos frequentemente salinizados", LARANJA),
        ("LOGÍSTICA", "Dependência de caminhão-pipa", LARANJA),
        ("PREÇO", "Garrafinha chega a R$ 4,00/L", LARANJA)]):
    y = 1.9 + i * 1.25
    add_rect(slide, lab, 0.7, y, 1.7, 0.8, cor, BRANCO, size=15)
    add_text(slide, txt, 2.6, y + 0.12, 4.6, 0.7, size=14, color=CINZA)
add_rect(slide, "SOLUÇÃO:\nproduzir água potável\nno ponto de uso", 7.7, 2.4, 4.8, 1.8, VERDE_CLARO, VERDE, size=22)
add_text(slide, "+30 milhões de pessoas\nno semiárido brasileiro", 7.7, 4.4, 4.8, 0.8, size=16, color=AZUL, bold=True, align=PP_ALIGN.CENTER)
add_footer(slide, 2)

# ===========================================================================
# SLIDE 3 — A SOLUÇÃO (corte diurno)
# ===========================================================================
slide = new_slide()
add_title(slide, "A SOLUÇÃO", "O Tupan transforma umidade do ar em água potável")
add_image(slide, RENDERS / "render_corte_diurno.png", 0.4, 1.75, 6.4)
add_text(slide, "Ciclo químico-térmico, sem compressor", 7.0, 1.85, 5.8, 0.5, size=20, color=AZUL, bold=True)
add_bullets(slide, [
    "Sem compressor, sem gás refrigerante, silencioso",
    "Aproveita a noite úmida e o calor do dia",
    "Vidraria de laboratório reciclada",
    "Filtro mineralizante + UV-C na bacia (2 L)",
    "Monitoramento Bluetooth/MQTT",
], 7.0, 2.5, 5.9, 3.0, size=14)
add_rect(slide, "0,68 L potável/ciclo", 7.0, 5.6, 2.7, 0.9, AZUL_CLARO, AZUL, size=16)
add_rect(slide, "0,43 L/kWh", 9.9, 5.6, 2.9, 0.9, VERDE_CLARO, VERDE, size=16)
add_footer(slide, 3)

# ===========================================================================
# SLIDE 4 — COMO FUNCIONA (4 etapas)
# ===========================================================================
slide = new_slide()
add_title(slide, "COMO FUNCIONA", "Do ar úmido à água potável em 4 etapas")
steps = [
    ("1", "SORÇÃO", "Ar noturno úmido\n+ leito de CaCl₂", AZUL_MEDIO),
    ("2", "ISOLAMENTO", "Servo fecha o ar\ne abre o vapor", AZUL),
    ("3", "REGENERA", "Solenoide 120 °C\nlibera vapor puro", LARANJA),
    ("4", "POTÁVEL", "Filtro mineral + UV-C\n→ bacia 2 L", VERDE),
]
for i, (num, title, desc, color) in enumerate(steps):
    x = 0.7 + i * 3.1
    add_circle(slide, num, x, 2.2, 0.9, color, size=22)
    add_text(slide, title, x, 3.2, 2.6, 0.4, size=16, color=color, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, desc, x, 3.7, 2.6, 0.8, size=14, color=CINZA, align=PP_ALIGN.CENTER)
    if i < len(steps) - 1:
        add_arrow(slide, x + 1.0, 2.65, x + 2.8, 2.65, CINZA_CLARO, 3)
add_rect(slide, "Ciclo diário: 8 h de sorção + 6 h de regeneração", 3.0, 5.3, 7.3, 0.8, AZUL_CLARO, AZUL, size=18)
add_footer(slide, 4)

# ===========================================================================
# SLIDE 5 — INFográfico do ciclo real
# ===========================================================================
slide = new_slide()
add_title(slide, "O CICLO REAL", "Quatro etapas auditáveis — sem compressor")
add_image(slide, RENDERS / "render_ciclo_4etapas.png", 0.5, 1.9, 12.3)
add_footer(slide, 5)

# ===========================================================================
# SLIDE 6 — VALIDAÇÃO CLIMÁTICA (mapas do Brasil)
# ===========================================================================
slide = new_slide()
add_title(slide, "VALIDAÇÃO CLIMÁTICA", "UR noturna e produção anual estimada por estado")
add_image(slide, MAPAS / "mapa_ur_noturna.png", 0.35, 1.7, 6.2)
add_image(slide, MAPAS / "mapa_producao_anual.png", 6.75, 1.7, 6.2)
caption(slide, "Reanálise Open-Meteo/ERA5 (2024) das 27 capitais + física do Tupan", 3.0, 7.0, 7.3)
add_footer(slide, 6)

# ===========================================================================
# SLIDE 7 — PRODUÇÃO × UMIDADE e ciclo diurno
# ===========================================================================
slide = new_slide()
add_title(slide, "PRODUÇÃO × UMIDADE", "Por que a sorção noturna funciona no sertão")
add_image(slide, GRAF / "grafico_producao_vs_ur.png", 0.4, 1.9, 6.3)
add_image(slide, GRAF / "grafico_ciclo_diurno.png", 6.9, 1.9, 6.0)
add_text(slide, "Regra de bolso: UR noturna ≥ 60 % ⇒ projeto-base; 40–60 % ⇒ ampliar leito; < 40 % ⇒ não instalar.",
         0.6, 6.85, 12.2, 0.35, size=12, color=AZUL, bold=True, align=PP_ALIGN.CENTER)
add_footer(slide, 7)

# ===========================================================================
# SLIDE 8 — ENERGIA
# ===========================================================================
slide = new_slide()
add_title(slide, "ENERGIA", "O solenoide domina o consumo — e há plano para solar")
add_image(slide, GRAF / "grafico_balanco_energia.png", 0.4, 1.8, 6.4)
add_text(slide, "1,683 kWh por ciclo", 7.1, 1.95, 5.6, 0.6, size=24, color=AZUL, bold=True)
add_bullets(slide, [
    "Solenoide 250 W × 6 h = 89 % do consumo",
    "Ventoinhas 7,5 W, eletrônica 5 W, UV-C 6 W",
    "0,43 L de água potável por kWh",
    "Solarização como caminho para autonomia total",
], 7.1, 2.7, 5.7, 2.8, size=14)
add_rect(slide, "→ geração distribuída fotovoltaica", 7.1, 5.7, 5.7, 0.9, VERDE_CLARO, VERDE, size=16)
add_footer(slide, 8)

# ===========================================================================
# SLIDE 9 — CUSTO COMPARATIVO
# ===========================================================================
slide = new_slide()
add_title(slide, "CUSTO DA ÁGUA", "Competitivo onde a rede não chega (R$/litro)")
add_image(slide, GRAF / "grafico_custo_comparativo.png", 0.4, 1.85, 6.4)
add_bullets(slide, [
    "R$ 2,36/L na tarifa plena (rede + tributos)",
    "R$ 0,83/L com Tarifa Social (TSEE 65 %)",
    "Galão 20 L ≈ R$ 0,60/L (referência de mercado)",
    "Garrafinha 500 mL ≈ R$ 4,00/L",
], 7.1, 2.0, 5.7, 2.6, size=15)
add_rect(slide, "O valor do Tupan é AUTONOMIA, não preço", 7.1, 5.2, 5.7, 1.1, AZUL_CLARO, AZUL, size=17)
add_footer(slide, 9)

# ===========================================================================
# SLIDE 10 — PROJEÇÃO ANUAL
# ===========================================================================
slide = new_slide()
add_title(slide, "PRODUÇÃO ANUAL", "593,8 L/ano por unidade em Petrolina-PE")
add_image(slide, GRAF / "grafico_projecao_anual.png", 0.9, 1.9, 11.5)
add_text(slide, "Sazonalidade acompanha a umidade noturna: máximo no período chuvoso, mínimo na estiagem.",
         0.8, 6.8, 11.7, 0.35, size=12, color=CINZA, italic=True, align=PP_ALIGN.CENTER)
add_footer(slide, 10)

# ===========================================================================
# SLIDE 11 — IMPACTO EM ESCALA
# ===========================================================================
slide = new_slide()
add_title(slide, "IMPACTO EM ESCALA", "A escala inverte virtudes — advertência central")
add_image(slide, GRAF / "grafico_impacto_escala.png", 0.5, 1.85, 12.3)
add_bullets(slide, [
    "100 mil unidades ⇒ ~24,7 ML/ano de água e ~61 GWh/ano de energia",
    "70–100 t de sal exaurido por década ⇒ logística reversa obrigatória",
    "Solarização e descarte correto do dessecante são condições de contorno",
], 0.9, 5.9, 11.7, 1.2, size=13, color=LARANJA)
add_footer(slide, 11)

# ===========================================================================
# SLIDE 12 — TECNOLOGIA / ARQUITETURA
# ===========================================================================
slide = new_slide()
add_title(slide, "TECNOLOGIA", "Um núcleo, muitos consumidores — paridade garantida")
add_image(slide, RENDERS / "render_3d_conceito.png", 0.4, 1.7, 6.0)
add_bullets(slide, [
    "Núcleo C++23 header-only = fonte única da física",
    "CLI, studio, Python (pybind11) e web (Flask) com os mesmos números",
    "Arduino Mega 2560: firmware C++20, MVC + FSM",
    "Sensores DHT22/DS18B20/nível; atuadores PWM, solenoide e servo",
    "35 testes C++ + 21 testes Python",
], 6.7, 1.9, 6.2, 3.4, size=14)
add_rect(slide, "IoT: Bluetooth HC-05 + MQTT", 6.7, 5.6, 6.2, 0.9, VERDE_CLARO, VERDE, size=16)
add_footer(slide, 12)

# ===========================================================================
# SLIDE 13 — STUDIO INTERATIVO (Lua + ImGui + OpenGL)
# ===========================================================================
slide = new_slide(AZUL)
add_text(slide, "STUDIO INTERATIVO", 0.7, 0.55, 12.0, 0.8, size=30, color=BRANCO, bold=True, align=PP_ALIGN.CENTER)
add_text(slide, "A UI é um script Lua (estilo JSON) — sem recompilar para mudar.",
         0.8, 1.45, 11.9, 0.4, size=14, color=AZUL_CLARO, align=PP_ALIGN.CENTER)
add_image(slide, RENDERS / "render_3d_conceito.png", 0.6, 2.1, 5.6)
add_bullets(slide, [
    "DSL Lua lido com sol2 (menus, painéis e cena 3D)",
    "Dear ImGui + OpenGL 3.3 para janela e render",
    "Álgebra linear própria (Real=float, Mat4 com union)",
    "Runner headless com luaaa: scripts chamam tupan.*",
    "Física real do núcleo ligada aos sliders",
], 6.5, 2.2, 6.3, 3.4, size=14, color=BRANCO)
add_rect(slide, "./build/tupan_studio   ·   ./build/tupan_script", 6.5, 5.8, 6.3, 0.8, VERDE, BRANCO, size=14)
add_footer(slide, 13)

# ===========================================================================
# SLIDE 14 — APP COMPANHEIRO (IoT)
# ===========================================================================
slide = new_slide()
add_title(slide, "APP COMPANHEIRO", "Dashboard, sensores, controles e histórico")
add_image(slide, MOCKUPS / "app_01_painel.png", 0.7, 1.8, 2.7)
add_image(slide, MOCKUPS / "app_03_sensores.png", 3.7, 1.8, 2.7)
add_image(slide, MOCKUPS / "app_04_controles.png", 6.7, 1.8, 2.7)
add_image(slide, MOCKUPS / "app_05_historico.png", 9.7, 1.8, 2.7)
add_text(slide, "Pareamento HC-05 (Bluetooth) e ponte MQTT · histórico auditável com export CSV",
         0.7, 6.5, 12.0, 0.4, size=13, color=CINZA, align=PP_ALIGN.CENTER)
add_footer(slide, 14)

# ===========================================================================
# SLIDE 15 — ENTREGA (Docker + CI/CD)
# ===========================================================================
slide = new_slide()
add_title(slide, "ENTREGA", "Docker multi-stage + Jenkins → Kubernetes/VPS")
cols = [
    ("IMAGENS", "docker/Dockerfile\nbuild · core · web\n(healthcheck /health)", AZUL_CLARO, AZUL),
    ("KUBERNETES", "deploy/k8s\nDeploy/Service/Ingress/HPA\nrunAsNonRoot + probes", AZUL_CLARO, AZUL),
    ("VPS", "deploy/vps\nsystemd + nginx\nTLS/reverse proxy", VERDE_CLARO, VERDE),
    ("CI/CD", "ci/Jenkinsfile\nbuild+teste+mídia+push+deploy\nGitHub Actions espelhado", LARANJA_CLARO, LARANJA),
]
for i, (titulo, texto, bg, fg) in enumerate(cols):
    x = 0.55 + i * 3.2
    add_rect(slide, titulo, x, 1.9, 3.0, 0.8, fg, BRANCO, size=16)
    add_text(slide, texto, x, 2.9, 3.0, 1.8, size=12, color=CINZA, align=PP_ALIGN.CENTER)
add_rect(slide, "Reprodutível: build → teste → mídia → imagem → deploy", 2.0, 5.4, 9.3, 0.9, AZUL_CLARO, AZUL, size=18)
add_footer(slide, 15)

# ===========================================================================
# SLIDE 16 — CAD & 3D
# ===========================================================================
slide = new_slide()
add_title(slide, "CAD & 3D", "Geometria gerada do mesmo modelo paramétrico")
add_image(slide, MEDIA / "cad" / "tupan_cad.png", 0.4, 1.75, 7.0)
add_image(slide, MEDIA / "cad" / "esquema_eletrico.png", 7.7, 1.75, 5.2)
add_bullets(slide, [
    "tupan_cad.png: vistas frontal/superior/lateral (carcaça 34×24×32 cm)",
    "tupan_pecas.stl: malha 3D exibida no Tupan Studio",
    "tupan.scad: modelo paramétrico OpenSCAD; DXF para desenho técnico",
    "esquema elétrico em PNG/SVG (Arduino Mega + sensores + atuadores)",
], 0.6, 6.05, 12.2, 1.0, size=12)
add_footer(slide, 16)

# ===========================================================================
# SLIDE 16 — MERCADO
# ===========================================================================
slide = new_slide()
add_title(slide, "MERCADO", "Onde o Tupan faz diferença")
segments = [
    ("COMUNIDADES", "Semiárido, vilarejos, assentamentos", VERDE),
    ("EXPEDIÇÕES", "Trilhas, acampamentos, áreas remotas", AZUL_MEDIO),
    ("EMERGÊNCIA", "Desastres naturais e crise hídrica", LARANJA),
    ("RESIDENCIAL", "Casas, chácaras e uso diário", AZUL),
]
for i, (title, desc, color) in enumerate(segments):
    col, row = i % 2, i // 2
    x, y = 0.8 + col * 6.0, 1.9 + row * 2.4
    add_rect(slide, title, x, y, 2.6, 0.8, color, BRANCO, size=17)
    add_text(slide, desc, x + 2.8, y + 0.12, 3.0, 0.6, size=14, color=CINZA)
add_rect(slide, "1 a 2 pessoas por ciclo · foco em consumo humano direto", 3.0, 6.2, 7.3, 0.8, AZUL_CLARO, AZUL, size=17)
add_footer(slide, 17)

# ===========================================================================
# SLIDE 17 — PRÓXIMOS PASSOS / ENCERRAMENTO
# ===========================================================================
slide = new_slide(AZUL)
add_text(slide, "PRÓXIMOS PASSOS", 0.7, 0.6, 12.0, 0.8, size=32, color=BRANCO, bold=True, align=PP_ALIGN.CENTER)
steps = [
    ("1", "Protótipo funcional", "montagem e testes"),
    ("2", "Validação de potabilidade", "parâmetros ANVISA"),
    ("3", "Piloto em comunidade", "campo real"),
    ("4", "Escala sustentável", "produção local + solar"),
]
for i, (num, title, desc) in enumerate(steps):
    x = 0.9 + i * 3.1
    add_circle(slide, num, x, 2.2, 0.9, VERDE, size=22)
    add_text(slide, title, x, 3.3, 2.7, 0.4, size=15, color=BRANCO, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, desc, x, 3.8, 2.7, 0.35, size=13, color=AZUL_CLARO, align=PP_ALIGN.CENTER)
    if i < len(steps) - 1:
        add_arrow(slide, x + 1.0, 2.65, x + 2.8, 2.65, RGBColor(120, 160, 200), 3)
add_text(slide, "Tupan, Máquina de Chuva", 1.0, 5.5, 11.3, 0.5, size=22, color=BRANCO, bold=True, align=PP_ALIGN.CENTER)
add_text(slide, "Água do ar. Onde você precisar.", 1.0, 6.1, 11.3, 0.4, size=16, color=AZUL_CLARO, align=PP_ALIGN.CENTER)
add_text(slide, "github.com/tuliofh01/Tupan · MIT", 1.0, 6.6, 11.3, 0.4, size=12, color=BRANCO, align=PP_ALIGN.CENTER)
add_footer(slide, 18)

# ---------------------------------------------------------------------------
# Salvar
# ---------------------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print("Apresentação salva:", OUT)
print("Slides:", len(prs.slides))
