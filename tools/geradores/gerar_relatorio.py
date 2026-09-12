#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GERADOR DO RELATÓRIO CIENTÍFICO — TUPAN, MÁQUINA DE CHUVA
=============================================================================
DIDÁTICA: este gerador monta um ARTIGO CIENTÍFICO (ABNT NBR 14724) em .docx
com python-docx. A linha de raciocínio do documento é:

    Problema (escassez hídrica no semiárido)
      → Fundamentação (psicrometria + sorção + termodinâmica + química)
      → Métodos (modelo físico, núcleo C++23, esteira de dados ERA5, ML)
      → Resultados (clima, produção, energia, custo, ML, escala)
      → Discussão (biomas, conformidade INMETRO/ANVISA/ANEEL/LGPD, riscos)
      → Instruções computacionais (reprodutibilidade)
      → Conclusão + Referências + Apêndices

Equações matemáticas (avançadas) e químicas são renderizadas em Unicode,
com cor distinta por tipo (azul = matemática, verde = química) para que o
leitor distinga modelo físico de reação química.

Executar:  python3 tools/geradores/gerar_relatorio.py
Saída:     docs/relatorios/relatorio_descritivo.docx
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ---------------------------------------------------------------------------
# CAMINHOS — o gerador vive em tools/geradores/ (raiz = parents[2])
# ---------------------------------------------------------------------------
RAIZ: Final[Path] = Path(__file__).resolve().parents[2]
DOC_DIR: Final[Path] = RAIZ / "docs"
MIDIA: Final[Path] = DOC_DIR / "midia"
GRAF: Final[Path] = MIDIA / "graficos"
RENDERS: Final[Path] = MIDIA / "renders"
MAPAS: Final[Path] = MIDIA / "mapas"
DADOS: Final[Path] = RAIZ / "data"
OUT: Final[Path] = DOC_DIR / "relatorios" / "relatorio_descritivo.docx"
DOC_DIR.mkdir(parents=True, exist_ok=True)

AZUL = "1E3A5F"; AZUL_CLARO = "DCEAF7"; VERDE = "1B5E20"; VERDE_CLARO = "E3F2E3"
LARANJA = "E65100"; CINZA = "595959"; ROXO = "5B2C6F"

# ===========================================================================
# HELPERS DE FORMATAÇÃO (didáticos: cada função = um elemento ABNT)
# ===========================================================================
def set_cell_shading(cell, fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:fill'), fill)
    tcPr.append(shd)


def set_cell_border(cell, **kwargs) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders'); tcPr.append(tcBorders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        if edge in kwargs:
            data = kwargs[edge]; tag = 'w:' + edge
            el = tcBorders.find(qn(tag))
            if el is None:
                el = OxmlElement(tag); tcBorders.append(el)
            for k in ['sz', 'val', 'color', 'space']:
                if k in data:
                    el.set(qn('w:' + k), str(data[k]))


def set_cell_text(cell, text, bold=False, color=None, size=9, align=None) -> None:
    cell.text = ""; p = cell.paragraphs[0]
    if align:
        p.alignment = align
    r = p.add_run(str(text)); r.bold = bold; r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor.from_string(color)


def add_table(doc, headers, rows, widths=None, font_size=8):
    table = doc.add_table(rows=1, cols=len(headers)); table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        set_cell_text(hdr[i], h, bold=True, color="FFFFFF", size=font_size,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_shading(hdr[i], AZUL)
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            set_cell_text(cells[i], val, size=font_size)
            if len(table.rows) % 2 == 0:
                set_cell_shading(cells[i], "F7F9FB")
    if widths:
        for row in table.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(6)
    return p


def add_para(doc, text, bold_prefix=None, italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4); p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r1 = p.add_run(bold_prefix); r1.bold = True
        r1.font.color.rgb = RGBColor.from_string(AZUL)
        p.add_run(text)
    else:
        p.add_run(text).italic = italic
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet' if level == 0 else 'List Bullet 2')
    p.paragraph_format.space_after = Pt(2); p.add_run(text); return p


def add_numbered(doc, text):
    p = doc.add_paragraph(style='List Number')
    p.paragraph_format.space_after = Pt(2); p.add_run(text); return p


def add_subheading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(12)
    r.font.color.rgb = RGBColor.from_string(VERDE)
    return p


def add_image(doc, path: str | Path, caption: str, width=Inches(6.2)):
    """Insere figura apenas se o arquivo existir (robustez de reprodutibilidade)."""
    path = Path(path)
    if not path.exists():
        return None
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=width)
    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption); r.italic = True; r.font.size = Pt(9)
    r.font.color.rgb = RGBColor.from_string(CINZA)
    return cap


def add_page_break(doc): doc.add_page_break()


def add_formula(doc, text, note=None, kind="math"):
    """Renderiza equação. kind='math' (azul) | 'chem' (verde, com rótulo Química)."""
    cor = AZUL if kind == "math" else VERDE
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(11)
    r.font.name = 'Cambria Math' if kind == "math" else 'Cambria'
    r.font.color.rgb = RGBColor.from_string(cor)
    if note:
        p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(4)
        prefixo = "Reação: " if kind == "chem" else ""
        r2 = p2.add_run(prefixo + note); r2.italic = True; r2.font.size = Pt(9)
        r2.font.color.rgb = RGBColor.from_string(CINZA)


def add_chem(doc, equation, note=None):
    """Atalho didático para equações químicas (balanceadas, Unicode)."""
    add_formula(doc, equation, note, kind="chem")


def add_callout(doc, title, text, color=AZUL_CLARO):
    table = doc.add_table(rows=1, cols=1); table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0); set_cell_shading(cell, color)
    set_cell_border(cell, top={'val': 'single', 'sz': 8, 'color': AZUL},
                    bottom={'val': 'single', 'sz': 8, 'color': AZUL},
                    left={'val': 'single', 'sz': 8, 'color': AZUL},
                    right={'val': 'single', 'sz': 8, 'color': AZUL})
    cell.text = ""; p = cell.paragraphs[0]
    r1 = p.add_run(title + "\n"); r1.bold = True
    r1.font.color.rgb = RGBColor.from_string(AZUL)
    r2 = p.add_run(text); r2.font.size = Pt(10)
    doc.add_paragraph()


def setup_doc():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(2.0); s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(2.5); s.right_margin = Cm(2.5)
        s.page_width = Cm(21.0); s.page_height = Cm(29.7)
    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'; normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string("222222")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for name, size, color in [('Heading 1', 15, AZUL), ('Heading 2', 13, AZUL),
                              ('Heading 3', 11, AZUL)]:
        st = doc.styles[name]; st.font.name = 'Times New Roman'
        st.font.size = Pt(size); st.font.bold = True
        st.font.color.rgb = RGBColor.from_string(color)
    for s in doc.sections:
        footer = s.footer; p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Página ")
        f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
        it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve')
        it.text = 'PAGE'
        f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end')
        run._r.append(f1); run._r.append(it); run._r.append(f2)
        r2 = p.add_run(" de ")
        f1b = OxmlElement('w:fldChar'); f1b.set(qn('w:fldCharType'), 'begin')
        itb = OxmlElement('w:instrText'); itb.set(qn('xml:space'), 'preserve')
        itb.text = 'NUMPAGES'
        f2b = OxmlElement('w:fldChar'); f2b.set(qn('w:fldCharType'), 'end')
        r2._r.append(f1b); r2._r.append(itb); r2._r.append(f2b)
    return doc


def add_code(doc, code, caption=None):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0); set_cell_shading(cell, 'F5F5F5')
    set_cell_border(cell, top={'val': 'single', 'sz': 6, 'color': 'B0B0B0'},
                    bottom={'val': 'single', 'sz': 6, 'color': 'B0B0B0'},
                    left={'val': 'single', 'sz': 6, 'color': 'B0B0B0'},
                    right={'val': 'single', 'sz': 6, 'color': 'B0B0B0'})
    cell.text = ''; p = cell.paragraphs[0]
    for line in code.split('\n'):
        r = p.add_run(line + '\n')
        r.font.name = 'Courier New'; r.font.size = Pt(8.5)
    if caption:
        cp = doc.add_paragraph(); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = cp.add_run(caption); rr.italic = True; rr.font.size = Pt(9)
        rr.font.color.rgb = RGBColor.from_string(CINZA)


# ===========================================================================
# DOCUMENTO
# ===========================================================================
doc = setup_doc()

# --- CAPA / CABEÇALHO DE ARTIGO -------------------------------------------
doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('PONTIFÍCIA UNIVERSIDADE CATÓLICA DE MINAS GERAIS — PUC-MG')
r.bold = True; r.font.size = Pt(13); r.font.color.rgb = RGBColor.from_string(AZUL)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Curso de Engenharia de Computação · Disciplina: IoT & PLCs · 2026.2')
r.font.size = Pt(11); r.font.color.rgb = RGBColor.from_string(CINZA)
doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('TUPAN, MÁQUINA DE CHUVA')
r.bold = True; r.font.size = Pt(26); r.font.color.rgb = RGBColor.from_string(AZUL)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Gerador de Água Atmosférica por Sorção de Cloreto de Cálcio e '
              'Regeneração por Solenoide: modelagem físico-química, simulação '
              'computacional e avaliação de impacto em escala')
r.font.size = Pt(13); r.italic = True
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Túlio Ferreira Horta')
r.font.size = Pt(12); r.bold = True
doc.add_paragraph()

# --- RESUMO / ABSTRACT -----------------------------------------------------
add_heading(doc, 'Resumo', 1)
add_para(doc, 'Este trabalho apresenta o projeto, a modelagem e a validação de um '
         'gerador de água atmosférica (Atmospheric Water Generator, AWG) sem '
         'compressor, destinado à hidratação humana descentralizada no semiárido '
         'brasileiro. O dispositivo opera em ciclo diário: à noite, ventiladores '
         'forçam ar úmido através de um leito de cloreto de cálcio (CaCl₂), que '
         'retém água por sorção química; ao amanhecer, um servo-registro isola a '
         'entrada de ar e abre o duto de destilação; durante o dia, uma solenoide '
         'aquece o sal úmido a 120 °C, liberando vapor que condensa em vidraria de '
         'laboratório; o destilado atravessa um filtro mineralizante e uma câmara '
         'UV-C antes de ser armazenado em bacia de 2 L com torneira. O núcleo '
         'físico implementado em C++23 foi acoplado a uma esteira de dados de '
         '14.616 horas de reanálise ERA5/Open-Meteo para Petrolina-PE e a um '
         'modelo de aprendizado de máquina por regressão ridge de grau 2 treinado '
         'em streaming. Resultados: umidade relativa noturna média de 68,65 % a '
         '24,64 °C; produção de 0,68 L potáveis por ciclo (0,43 L/kWh); projeção '
         'de 593,8 L/ano por unidade; R² = 0,991 e RMSE = 0,064 L para o modelo '
         'preditivo. A análise de escala para 100 mil unidades estima 24,7 ML/ano '
         'de água, 61 GWh/ano de energia e 70–100 t de sal exaurido por década, '
         'impondo solarização e logística reversa como condições de contorno do '
         'projeto. Conclui-se pela viabilidade técnica e pela necessidade de '
         'acoplamento socioambiental explícito.'),
add_para(doc, '')
p = doc.add_paragraph()
r = p.add_run('Palavras-chave: '); r.bold = True
p.add_run('gerador de água atmosférica; sorção; cloreto de cálcio; destilação '
          'solar; semiárido; IoT; conformidade regulatória.')

add_heading(doc, 'Abstract', 1)
add_para(doc, 'This work presents the design, modeling and validation of a '
         'compressor-free Atmospheric Water Generator (AWG) for decentralized '
         'human hydration in the Brazilian semi-arid region. The device runs a '
         'diurnal cycle: at night, fans force humid air through a calcium '
         'chloride (CaCl₂) bed that chemically retains water; at dawn a servo '
         'damper isolates the air intake and opens the distillation duct; during '
         'the day a solenoid heats the wet salt to 120 °C, releasing vapor that '
         'condenses in laboratory glassware; the distillate passes through a '
         'mineralizing filter and a UV-C chamber before storage in a 2 L tap '
         'basin. The C++23 physical core was coupled to 14,616 hours of ERA5/'
         'Open-Meteo reanalysis for Petrolina-PE and to a degree-2 ridge '
         'regression model trained in streaming fashion. Results: mean nocturnal '
         'relative humidity of 68.65 % at 24.64 °C; 0.68 L of potable water per '
         'cycle (0.43 L/kWh); 593.8 L/year per unit; R² = 0.991 and RMSE = '
         '0.064 L for the predictive model. A 100,000-unit scale analysis '
         'estimates 24.7 ML/year of water, 61 GWh/year of energy and 70–100 t of '
         'spent salt per decade, making solarization and reverse logistics '
         'mandatory boundary conditions. Technical feasibility is confirmed; '
         'explicit socio-environmental coupling is required.'),
p = doc.add_paragraph()
r = p.add_run('Keywords: '); r.bold = True
p.add_run('atmospheric water generator; sorption; calcium chloride; solar '
          'distillation; semi-arid; IoT; regulatory compliance.')

add_page_break(doc)

# ===========================================================================
# 1 INTRODUÇÃO
# ===========================================================================
add_heading(doc, '1 Introdução', 1)
add_para(doc, 'A escassez hídrica no semiárido brasileiro é um fenômeno '
         'estrutural, e não apenas conjuntural: a região abriga mais de 30 '
         'milhões de habitantes distribuídos por 1.262 municípios oficialmente '
         'delimitados como semiáridos [32], com precipitação média entre 250 e '
         '800 mm/ano concentrada em poucos meses e forte variabilidade '
         'interanual associada aos ciclos de El Niño e ao aquecimento do '
         'Atlântico tropical [20]. Nesse cenário, o abastecimento domiciliar '
         'depende de cisternas, caminhões-pipa e aquíferos frequentemente '
         'salobros [19], [33].')
add_para(doc, 'A umidade atmosférica constitui um recurso hídrico difuso e '
         'renovável, cuja exploração por geradores de água atmosférica (AWG) '
         'tem sido investigada por diferentes rotas tecnológicas [6], [7]. A '
         'rota convencional emprega refrigeração por compressão de vapor, '
         'resfriando o ar abaixo do ponto de orvalho; trata-se de tecnologia '
         'madura, porém dependente de compressor, gás refrigerante e de '
         'potência elétrica concentrada — o que compromete custo, ruído, '
         'manutenção e acessibilidade em comunidades rurais [6]. Rotas '
         'alternativas exploram dessecantes sólidos e líquidos, cuja afinidade '
         'química pela água permite capturá-la sem atingir o ponto de orvalho, '
         'com regeneração térmica posterior [6], [8].')
add_para(doc, 'Este trabalho adota a rota de dessecante sólido (cloreto de '
         'cálcio) e responde à seguinte questão de pesquisa: é possível operar '
         'um AWG doméstico sem compressor e sem refrigeração, aproveitando o '
         'ciclo diário de umidade do semiárido, com produção suficiente para '
         'hidratação humana e custo elétrico socialmente aceitável? A hipótese '
         'central é que o assincronismo entre a captura noturna (ar úmido e '
         'frio) e a regeneração diurna (calor disponível) confere ao semiárido '
         'uma vantagem termodinâmica para sorção térmica, dispensando '
         'refrigeração ativa.')
add_para(doc, 'Os objetivos específicos são: (i) modelar físico-quimicamente '
         'as etapas de sorção, regeneração, destilação e pós-tratamento; '
         '(ii) implementar um núcleo de simulação determinístico em C++23 e '
         'validá-lo por testes automatizados; (iii) estimar a produção anual '
         'com dados climáticos reais de Petrolina-PE; (iv) construir um modelo '
         'preditivo por aprendizado de máquina com interpretabilidade física; '
         '(v) quantificar custo energético sob tarifas brasileiras; (vi) '
         'avaliar riscos de adoção em massa; e (vii) verificar aderência ao '
         'arcabouço regulatório brasileiro.')
add_para(doc, 'O nome Tupan deriva do tupi-guarani para "trovão" ou "espírito '
         'divino", referência à origem atmosférica da água e ao conhecimento '
         'indígena sobre os ciclos de chuva no território [31].')

# ===========================================================================
# 2 FUNDAMENTAÇÃO TEÓRICA
# ===========================================================================
add_heading(doc, '2 Fundamentação Teórica', 1)

add_heading(doc, '2.1 Psicrometria e disponibilidade de vapor', 2)
add_para(doc, 'A pressão de saturação do vapor d\'água é descrita pela equação '
         'de Magnus, forma empírica da integração da relação de '
         'Clausius–Clapeyron [1], [2]:')
add_formula(doc, 'e_s(T) = 6,1094 · exp( 17,625 · T / (243,04 + T) )   [hPa]',
            'Equação de Magnus (T em °C)')
add_formula(doc, 'd e_s / dT = L_v · e_s / (R_v · T²)',
            'Forma diferencial de Clausius–Clapeyron (L_v = calor latente, '
            'R_v = constante do vapor)')
add_para(doc, 'A densidade de vapor é obtida pela lei dos gases ideais, e a '
         'umidade absoluta (razão de mistura) pela relação psicrométrica [2], [3]:')
add_formula(doc, 'ρ_v(T, UR) = UR/100 · e_s(T) · M_w / (R · (T + 273,15))   [g/m³]',
            'Densidade de vapor saturado/parcial (M_w = 18,015 g/mol)')
add_formula(doc, 'w = 0,622 · e / (p − e)   [kg H₂O / kg ar seco]',
            'Razão de mistura (e = pressão parcial de vapor, p = pressão total)')
add_para(doc, 'A entalpia específica do ar úmido, usada no balanço térmico do '
         'leito, é [3]:')
add_formula(doc, 'h = 1,006 · T + w · (2501 + 1,86 · T)   [kJ/kg ar seco]',
            'Entalpia do ar úmido (referência 0 °C)')
add_para(doc, 'A vantagem do semiárido reside na histerese diária: a UR sobe '
         'à noite (ar frio) e cai ao dia (ar quente), enquanto a razão de '
         'mistura absoluta varia menos. O modelo explora exatamente essa '
         'janela: captura quando ρ_v é alta no ciclo noturno e regenera com '
         'calor diurno.')

add_heading(doc, '2.2 Sorção química no leito de CaCl₂', 2)
add_para(doc, 'O cloreto de cálcio é um dessecante deliquescente: forma '
         'hidratos estáveis e, acima da umidade relativa de deliquescência '
         '(≈ 29 % a 25 °C), dissocia-se em solução saturada. As reações '
         'reversíveis relevantes são [5], [6]:')
add_chem(doc, 'CaCl₂(s) + 2 H₂O(g) ⇌ CaCl₂·2H₂O(s) + ΔH₁   (ΔH₁ < 0)',
         'formação do di-hidrato (sorção exotérmica)')
add_chem(doc, 'CaCl₂·2H₂O(s) + 4 H₂O(g) ⇌ CaCl₂·6H₂O(s) + ΔH₂',
         'formação do hexa-hidrato / deliquescência')
add_chem(doc, 'CaCl₂(s) ⇌ Ca²⁺(aq) + 2 Cl⁻(aq)   (solubilidade ≈ 74 g/100 mL a 20 °C)',
         'dissociação iônica em fase líquida')
add_para(doc, 'A sorção em sólidos porosos é frequentemente descrita por '
         'isotermas de Langmuir (cobertura monocamada) e, para valores '
         'elevados de atividade de água, por modelos GAB [5]:')
add_formula(doc, 'θ = K·P / (1 + K·P)',
            'Isoterma de Langmuir (θ = fração de sítios ocupados)')
add_formula(doc, 'm_eq/(M·q) = C·K·a_w / ((1 − K·a_w)(1 + (C−1)·K·a_w))',
            'Isoterma GAB (a_w = atividade de água)')
add_para(doc, 'A transferência de massa intrapartícula é governada pela '
         'segunda lei de Fick, cuja solução para esferas fundamenta o '
         'coeficiente efetivo de difusão D_eff [5]:')
add_formula(doc, '∂C/∂t = ∇·(D_eff · ∇C) = D_eff ∇²C',
            'Segunda lei de Fick (difusão em meio poroso)')
add_para(doc, 'Neste trabalho, a cinética global de captação é aproximada por '
         'uma equação diferencial ordinária de primeira ordem com teto de '
         'saturação M·q:')
add_formula(doc, 'dm/dt = k · (M·q − m)   ⇒   m(t) = M·q · (1 − e^(−k·t))',
            'Cinética de sorção de 1ª ordem (k = 0,55 h⁻¹; M = 2 kg; q = 1,0)')
add_para(doc, 'O fluxo mássico advectado pelo ar é limitado pela diferença de '
         'concentração entre entrada e saída do leito:')
add_formula(doc, 'ṁ_ar = (ρ_v,ent − ρ_v,sai) · Q_ar · η_leito',
            'Taxa de captação mássica (Q_ar = vazão; η_leito = eficiência do leito)')
add_callout(doc, 'Por que CaCl₂?',
            'Custo muito baixo, alta capacidade (até ~1 kg H₂O/kg de sal), '
            'regeneração a ~120 °C (compatível com solenoide ou calor solar) e '
            'reversibilidade. Contrapartida: exige filtragem de poeira e '
            'logística reversa do sal exaurido — tratada na Seção 5.6.')

add_heading(doc, '2.3 Regeneração térmica e transporte de calor', 2)
add_para(doc, 'A regeneração inverte as reações de sorção pela adição de '
         'calor sensível e latente:')
add_chem(doc, 'CaCl₂·6H₂O(s) → CaCl₂·2H₂O(s) + 4 H₂O(g) → CaCl₂(s) + 6 H₂O(g)',
         'desidratação térmica escalonada (120 °C)')
add_para(doc, 'O transporte de calor no leito e na vizinhança é descrito pela '
         'equação de condução de Fourier e, em regime transiente, pela difusão '
         'térmica [4]:')
add_formula(doc, '∂T/∂t = α ∇²T + Q̇/(ρ·c_p)   (α = k/(ρ·c_p))',
            'Equação de calor com geração interna (α = difusividade térmica)')
add_formula(doc, 'q = −k ∇T   (lei de Fourier)',
            'Fluxo de calor condutivo')
add_para(doc, 'Para a fase concentrada (leito), o balanço de energia de '
         'primeira ordem é modelado pelo resfriamento de Newton com '
         'aquecimento da solenoide:')
add_formula(doc, 'ρ V c_p · dT/dt = P_sol · η_aq − h A (T − T_amb)',
            'Balanço térmico do leito (P = 250 W; η_aq = 0,90)')
add_para(doc, 'A potência térmica necessária à vaporização combina calor '
         'sensível (aquecimento da água de 25 °C a 100 °C) e latente:')
add_formula(doc, 'Q_nec = m_lib · [ c_p,água · ΔT + L_v ] = m_lib · [4,186 · 75 + 2257]',
            'Calor sensível + latente (kJ/kg)')
add_para(doc, 'A fração liberável é função da temperatura do aquecedor, '
         'modelada por saturação linear com corte físico:')
add_formula(doc, 'φ(T_aq) = clamp01( (T_aq − 80) / 40 )   ⇒ φ = 1,0 a 120 °C',
            'Fração de água liberável na regeneração')
add_para(doc, 'A destilação em vidraria é modelada pela equação de Rayleigh, '
         'que descreve a variação de composição do líquido residual na '
         'destilação diferencial [5]:')
add_formula(doc, 'ln( W / W₀ ) = ∫ ( dx / (y* − x) )',
            'Equação de Rayleigh (W = massa no balanço; y* = composição do vapor)')
add_para(doc, 'Neste sistema, o "resíduo" é água salina no leito e o '
         '"destilado" é o vapor condensado; a eficiência de condensação mede o '
         'aproveitamento limpo:')
add_formula(doc, 'η_dest = m_condensado / m_vapor   (η_dest ≈ 0,92)',
            'Eficiência de destilação')
add_para(doc, 'O trocador de calor passivo da vidraria é dimensionado pela '
         'diferença média logarítmica de temperatura (LMTD) [4]:')
add_formula(doc, 'ΔT_lm = (ΔT₁ − ΔT₂) / ln(ΔT₁/ΔT₂)   e   Q̇ = U · A · ΔT_lm',
            'LMTD e taxa de troca térmica')
add_para(doc, 'Números adimensionais orientam o projeto do escoamento e da '
         'convecção no leito e no condensador [4]:')
add_formula(doc, 'Re = ρ v L / μ,    Nu = h L / k,    Pr = μ c_p / k',
            'Reynolds, Nusselt e Prandtl')

add_heading(doc, '2.4 Pós-tratamento: mineralização e esterilização UV-C', 2)
add_para(doc, 'A água destilada é agressiva (baixa alcalinidade e força '
         'iônica) e possui sabor insosso; o filtro mineralizante repõe Ca²⁺ e '
         'Mg²⁺ por dissolução controlada de calcita e dolomita, '
         'frequentemente assistida por CO₂ [5]:')
add_chem(doc, 'CaCO₃(s) + CO₂(aq) + H₂O(l) ⇌ Ca²⁺(aq) + 2 HCO₃⁻(aq)',
         'mineralização com calcita (perfil cálcico)')
add_chem(doc, 'CaMg(CO₃)₂(s) + 2 CO₂(aq) + 2 H₂O(l) → Ca²⁺(aq) + Mg²⁺(aq) + 4 HCO₃⁻(aq)',
         'mineralização com dolomita (perfil Ca/Mg)')
add_chem(doc, 'CaCO₃(s) ⇌ Ca²⁺(aq) + CO₃²⁻(aq)   (K_ps ≈ 3,3·10⁻⁹ a 25 °C)',
         'equilíbrio de solubilidade (risco de incrustação)')
add_para(doc, 'O potencial de incrustação/corrosão é quantificado pelo índice '
         'de saturação de Langelier (LSI), que referencia a água ao equilíbrio '
         'carbonato [5]:')
add_formula(doc, 'LSI = pH − pH_s,   pH_s = (9,3 + A + B) − (C + D)',
            'Índice de Langelier (LSI ≈ 0 = equilíbrio; > 0 incrustante)')
add_para(doc, 'A desinfecção UV-C segue a lei de Chick–Watson, de primeira '
         'ordem na dose e na concentração de microrganismos viáveis [14]:')
add_formula(doc, 'N/N₀ = exp( −k_d · D ),   D = I · t   [mJ/cm²]',
            'Lei de Chick–Watson (N = viáveis; D = dose UV)')
add_para(doc, 'A energia do fóton a 254 nm é suficiente para fotólise de '
         'dímeros de timina no DNA microbiano:')
add_formula(doc, 'E = h c / λ = (6,626·10⁻³⁴ · 3·10⁸) / 254·10⁻⁹ ≈ 4,88 eV',
            'Energia do fóton UV-C (h = Planck; c = velocidade da luz)')
add_chem(doc, 'Timina–Timina → Timina(=)Timina   (dímero de ciclobutano)',
         'fotoproduto que bloqueia a replicação do DNA')
add_para(doc, 'A água ainda sofre autoionização, cujo equilíbrio define o pH '
         'de referência (neutralidade a 25 °C):')
add_chem(doc, '2 H₂O(l) ⇌ H₃O⁺(aq) + OH⁻(aq),   K_w = 1,0·10⁻¹⁴ a 25 °C',
         'produto iônico da água (pH neutro = 7,0)')
add_callout(doc, 'Sequência de segurança do pós-tratamento',
            'Destilado → filtro mineralizante (perda de purga ~2 %) → câmara '
            'UV-C opaca com intertravamento (dose ≥ 40 mJ/cm²) → bacia de 2 L '
            'com torneira. A UV é barreira antimicrobiana e NÃO remove água; '
            'seu custo é apenas energético (6 W × 30 min = 10,8 kJ/ciclo).',
            VERDE_CLARO)

add_page_break(doc)

# ===========================================================================
# 3 MATERIAIS E MÉTODOS
# ===========================================================================
add_heading(doc, '3 Materiais e Métodos', 1)

add_heading(doc, '3.1 Arquitetura do sistema e máquina de estados', 2)
add_para(doc, 'O sistema físico é organizado em cinco subsistemas: captação '
         'de ar (ventiladores + pré-filtro de poeira), leito de sorção '
         '(CaCl₂), comutação por servo-registro, regeneração/destilação '
         '(solenoide + vidraria) e pós-tratamento/armazenamento (filtro + UV '
         '+ bacia com torneira). O controle embarcado segue o padrão MVC sobre '
         'a Máquina de Estados Finitos (FSM) abaixo, evitando qualquer '
         'alocação dinâmica de memória [17]:')
add_table(doc, ['Estado', 'Descrição', 'Transição de saída', 'Evento'],
          [['OCIOSO', 'Aguarda noite / botão SELECT', 'INTAKE', 'SELECT ou agendamento'],
           ['INTAKE', 'Ventoinhas 100 %; leito sorve água', 'REGEN', 'm ≥ M·q ou fim da janela'],
           ['REGEN', 'Solenoide 120 °C; servo fecha ar', 'DESTIL', 'm ≤ 0,05 kg ou tempo máx.'],
           ['DESTIL', 'Vapor → vidraria → filtro + UV → bacia', 'CHEIO/OCIOSO', 'bacia 2 L / fim do leito'],
           ['CHEIO', 'Bacia cheia; aguarda esvaziamento', 'OCIOSO', 'SELECT'],
           ['ERRO', 'Falha de sensor/superaquecimento', 'OCIOSO', 'sensores OK + SELECT']],
          widths=[2.2, 6.0, 2.6, 4.6])
add_para(doc, 'A pinagem é única fonte de verdade e coincide com o esquemático '
         'elétrico (Apêndice C). O firmware é C++20, sem `String` dinâmica '
         '(tudo `F()`/PROGMEM) e com log `LOG_*` de cada transição, de modo '
         'que toda decisão da FSM seja auditável em campo.')

add_heading(doc, '3.2 Núcleo de simulação e discretização', 2)
add_para(doc, 'O núcleo físico é um cabeçalho C++23 livre de dependências '
         '(`tupan_core.hpp`), consumido por cinco clientes: CLI, GUI Qt5, '
         'módulo pybind11, servidor Flask e firmware (via espelho de '
         'fórmulas). A integração temporal usa passo analítico fechado para a '
         'sorção (solução exata da EDO) e passo discreto explícito para a '
         'energia, com conservação de massa verificada por teste:')
add_formula(doc, 'm_{n+1} = m_n + Δt · k (M q − m_n)',
            'Discretização Euler explícita (equivalente à solução fechada em 1ª ordem)')
add_para(doc, 'A energia do ciclo decompõe-se de forma auditável '
         '(ventoinhas, solenoide, eletrônica e UV-C):')
add_formula(doc, 'E_ciclo = (P_fans·t_noite + P_sol·t_dia + P_ele·24 + P_uv·t_uv)',
            'Energia total do ciclo (kWh após /1000)')
add_formula(doc, 'η_hídrica = V_potável / E_ciclo   [L/kWh]',
            'Eficiência energético-hídrica (conta ambiental)')

add_heading(doc, '3.3 Método de Monte Carlo e geração pseudoaleatória', 2)
add_para(doc, 'Para propagar a incerteza do ruído multiplicativo (±5 %), '
         'emprega-se integração de Monte Carlo [9]. O estimador da média e sua '
         'incerteza padrão, sob o Teorema Central do Limite, são:')
add_formula(doc, 'μ̂ = (1/N) Σ_{i=1..N} x_i,    σ̂² = (1/(N−1)) Σ (x_i − μ̂)²',
            'Estimadores de Monte Carlo (média e variância amostral)')
add_formula(doc, 'erro padrão ≈ σ̂ / √N',
            'Convergência O(N^(−1/2)) do estimador')
add_para(doc, 'Os percentis p05, p50 e p95 são obtidos por interpolação '
         'linear da distribuição ordenada, viabilizando análise de risco '
         'agrícola/hídrico (probabilidade de ciclos improdutivos):')
add_formula(doc, 'idx = q·(N − 1);   x_q = x_⌊idx⌋ + (idx − ⌊idx⌋)(x_⌈idx⌉ − x_⌊idx⌋)',
            'Interpolação de percentil (quantil amostral)')
add_para(doc, 'O gerador pseudoaleatório é o xorshift64*, escolhido por '
         'determinismo, velocidade e período longo [10]:')
add_code(doc, 'state ^= state >> 12;  state ^= state << 25;  state ^= state >> 27;\n'
              'return state * 0x2545F4914F6CDD1DULL;',
         'Quadro 1 — Núcleo do PRNG xorshift64* (mesma semente ⇒ mesma saída).')

add_heading(doc, '3.4 Modelo de aprendizado de máquina em streaming', 2)
add_para(doc, 'O preditor é uma regressão ridge de grau 2 estimada pelas '
         'equações normais regularizadas [13]:')
add_formula(doc, 'w = (XᵀX + λ I)^(−1) Xᵀ y,   λ = 10⁻⁹',
            'Solução ridge (λ evita singularidade e sobreajuste)')
add_para(doc, 'As features polinomiais até grau 2 de x = {UR, T, vazão, η, '
         'T_aq} geram 20 termos; somam-se três features de engenharia com '
         'significado físico, o que introduz os "kinks" da física no modelo '
         'linear:')
add_formula(doc, 'f_ur = (UR/100)·ρ_v(T)/30;   f_sat = m_leito/(M q);   '
                 'f_lib = clamp01((T_aq − 80)/40)',
            'Features de engenharia (conteúdo de vapor, saturação e liberação)')
add_para(doc, 'O treinamento acumula os produtos XᵀX e Xᵀy em streaming — '
         'nenhuma amostra é armazenada — e a avaliação reporta RMSE e R²:')
add_formula(doc, 'RMSE = √( (1/n)Σ(y_i − ŷ_i)² ),   R² = 1 − SSE/SST',
            'Métricas de erro e coeficiente de determinação')
add_code(doc, 'for (int n = 0; n < N; ++n) {\n'
              '    auto phi = features(x);            // 23 features\n'
              '    for (i) { b[i] += a[i]*y; for (j) M[i][j] += a[i]*a[j]; }\n'
              '}\n'
              'for (i) M[i][i] += lambda_ridge;       // regularização\n'
              '// eliminação de Gauss com pivoteamento parcial:\n'
              'w = solve(M, b);',
         'Quadro 2 — Treino em streaming (XᵀX/Xᵀy) e solução por Gauss.')

add_heading(doc, '3.5 Dados climáticos e esteira de análise', 2)
add_para(doc, 'A esteira de dados (`tools/pipeline/analise_dados.py`) '
         'ingere 14.616 horas de reanálise ERA5/Open-Meteo [1] para '
         'Petrolina-PE (9,39° S; 40,50° O), cobrindo variáveis horárias de '
         'umidade relativa e temperatura. As estatísticas noturnas (20h–06h) '
         'alimentam as condições de contorno do núcleo; a projeção anual usa '
         'agregação horária ponderada. O custo de energia é calculado por:')
add_formula(doc, 'C = E_ano · (τ + β) · (1 − δ),   E_ano = E_ciclo · 365',
            'Custo anual (τ = tarifa média; β = bandeira; δ = desconto TSEE)')
add_para(doc, 'Premissas: τ = R$ 0,95/kWh (média residencial faturada, com '
         'tributos); bandeiras ANEEL em R$/MWh (vermelha P1 = 4,463; P2 = '
         '7,877) [27]; TSEE = 65 % de desconto para consumo ≤ 80 kWh/mês '
         '[24]. A escala de adoção agrega N unidades sequencialmente:')
add_formula(doc, 'V_total = N · v · 365;   E_total = N · E_ciclo · 365;   '
                 'M_sal = N · M_leito · (T/T_vida)',
            'Impactos agregados (água, energia e massa de sal exaurido)')

add_heading(doc, '3.6 Validação e reprodutibilidade', 2)
add_para(doc, 'A validação combina 35 testes unitários em C++ (psicrometria, '
         'sorção, destilação, ciclo, pós-tratamento, RNG, ML, frota, Monte '
         'Carlo e binlog) e 21 testes em Python (pytest), executados contra o '
         'módulo nativo quando disponível e contra o espelho Python quando '
         'não. Esse arranjo garante paridade física entre linguagens e '
         'satisfaz o requisito de reprodutibilidade [17]:')
add_code(doc, '$ cd src/core && cmake --build build --target tupan_tests && ./build/tupan_tests   # 35 testes C++\n'
              '$ cd tools/tests && python3 -m pytest -q                              # 21 testes\n'
              '$ ./build/tupan_sim --night 8 --day 6 --ur 68 --temp 24 --json',
         'Quadro 3 — Comandos de verificação.')

add_page_break(doc)

# ===========================================================================
# 4 RESULTADOS E DISCUSSÃO
# ===========================================================================
add_heading(doc, '4 Resultados e Discussão', 1)

add_heading(doc, '4.1 Climatologia noturna de Petrolina-PE', 2)
add_para(doc, 'A análise das 14.616 horas indica umidade relativa noturna '
         'média de 68,65 % a 24,64 °C, com sazonalidade marcada (máximos no '
         'período chuvoso e mínimos no auge da estiagem). Esse resultado '
         'confirma quantitativamente a hipótese de assincronismo: existe '
         'vapor disponível à noite e calor disponível ao dia, na mesma '
         'localidade e com regularidade estatística [1], [20].')
add_image(doc, GRAF / 'grafico_ml_vs_fisica.png',
          'Figura 1 — Modelo de ML versus física determinística (validação '
          'do preditor de produção).')

add_heading(doc, '4.2 Produção de água, energia e custo', 2)
add_para(doc, 'Sob o ciclo padrão (8 h de noite + 6 h de dia), o núcleo '
         'reporta massa sorvida de 0,75 kg, 0,69 L destilados e 0,68 L '
         'potáveis (após filtro de recuperação 0,98 e limite de bacia de '
         '2 L). A decomposição energética é dominada pela solenoide:')
add_table(doc, ['Etapa', 'Potência', 'Duração', 'Energia (kWh)', 'Fração'],
          [['Solenoide', '250 W', '6 h', '1,500', '89,1 %'],
           ['Eletrônica (Mega + sensores)', '5 W', '24 h', '0,120', '7,1 %'],
           ['Ventoinhas', '7,5 W', '8 h', '0,060', '3,6 %'],
           ['UV-C', '6 W', '0,5 h', '0,003', '0,2 %'],
           ['TOTAL', '—', '—', '1,683', '100 %']],
          widths=[5.2, 2.4, 2.0, 2.8, 2.0])
add_para(doc, 'A eficiência energético-hídrica resultante é de 0,43 L/kWh. '
         'Com a tarifa média brasileira, o custo anual (365 ciclos) é de '
         'R$ 583,58–588,42 (R$ 2,36–2,38 por litro); com Tarifa Social '
         '(consumo ≈ 51,2 kWh/mês, dentro da faixa ≤ 80 kWh), cai para '
         'R$ 204,25–205,21/ano (R$ 0,83/L). A comparação de mercado: galão de '
         '20 L ≈ R$ 0,60/L; garrafinha de 500 mL ≈ R$ 4,00/L. A conclusão é '
         'explícita: o Tupan é mais caro que a água envasada em rede, porém '
         'mais barato que a garrafinha e socialmente competitivo sob Tarifa '
         'Social — seu valor é autonomia, não preço.')

add_heading(doc, '4.3 Desempenho do modelo preditivo', 2)
add_para(doc, 'A regressão ridge de grau 2 com 23 features atinge R² = 0,991 '
         'e RMSE = 0,064 L, superando o baseline de rede neural (MLP 64/64, '
         'R² = 0,877) e a regressão polinomial sem features de engenharia '
         '(R² = 0,947). O ganho decorre da injeção dos kinks físicos '
         '(saturação do leito e fração de liberação), evidência de que '
         'mecanismo e dados são complementares, não substitutos [11], [12].')

add_heading(doc, '4.4 Impacto de adoção em massa e advertências', 2)
add_para(doc, 'A modelagem de N = 100.000 unidades em operação contínua '
         'fornece os agregados a seguir, com as respectivas advertências:')
add_table(doc, ['Métrica', 'Valor (100 mil unidades)', 'Advertência'],
          [['Água produzida', '≈ 24,7 ML/ano', 'Relevante para ~100 mil pessoas; irrelevante para rios/aquíferos'],
           ['Energia demandada', '≈ 61 GWh/ano (~11 mil residências)', '⚠ Demanda de pico na rede: solarização como padrão'],
           ['Sal exaurido', '70–100 t por década', '⚠ Salinização do solo se descartado; logística reversa obrigatória'],
           ['Lâmpadas UV-C', '≥ 9.000 h de vida', '⚠ Substituição programada; resíduo de mercúrio'],
           ['Equidade tarifária', 'R$ 2,36/L na tarifa plena', '⚠ Regressivo sem TSEE/PV: pobreza paga mais por litro'],
           ['Confiança sanitária', 'Monitoramento ANVISA', '⚠ Uma unidade contaminada compromete o programa inteiro']],
          widths=[4.0, 5.4, 7.0])
add_callout(doc, 'Advertência central deste trabalho',
            'A escala inverte virtudes. Um ciclo limpo para uma família vira '
            '61 GWh de demanda e 100 t de sal gasto para uma região. '
            'Solarização e logística reversa do dessecante não são acessórios '
            'verdes: são condições de contorno para que o Tupan não recrie o '
            'problema que pretende resolver.', "FFF3E0")

add_heading(doc, '4.5 Comparação de biomas e transferibilidade', 2)
add_para(doc, 'Como o ciclo depende de umidade noturna (combustível) e calor '
         'diurno (regeneração), sua transferibilidade pode ser avaliada por '
         'classificação climática de Köppen–Geiger [15]:')
add_table(doc, ['Região / bioma', 'Köppen', 'UR noturna', 'T noturna', 'Adequação', 'Adaptação'],
          [['Sertão nordestino (BR)', 'BSh', '60–75 %', '22–26 °C', '★★★★★ ideal', 'Projeto-base (Petrolina)'],
           ['Sahel (África)', 'BSh', '70–90 % (chuvas)', '24–30 °C', '★★★★☆ sazonal', 'Poeira do harmatã: pré-filtro lavável'],
           ['Sahara/Arábia', 'BWh', '< 20 %', '15–30 °C', '★☆☆☆☆ inviável', 'Sem vapor: só dessalinização'],
           ['Mediterrâneo (Europa)', 'Csa', '50–70 %', '18–24 °C', '★★★☆☆ estacional', 'Inverno: REGEN longa/auxiliar'],
           ['Sudoeste dos EUA/México', 'BWh/BSh', '30–50 % (monção)', '20–30 °C', '★★☆☆☆ marginal', 'Operar só no monção Jul–Set'],
           ['Atacama/Namibe (névoa)', 'BWk', '80–95 %', '12–20 °C', '★★★★☆ c/ adaptação', 'Noites frias: solenoide extra']],
          widths=[4.4, 1.8, 2.6, 2.2, 2.6, 4.8])
add_para(doc, 'Regra de bolso: UR noturna ≥ 60 % ⇒ projeto-base; 40–60 % ⇒ '
         'estender INTAKE e capacidade do leito; < 40 % ⇒ não instalar. O '
         'sertão não é o pior lugar do mundo para extrair água do ar — é um '
         'dos melhores, porque a noite úmida e o dia quente coincidem.')

add_heading(doc, '4.6 Conformidade regulatória e normativa', 2)
add_para(doc, 'Um dispositivo de água potável no Brasil está sujeito a um '
         'arcabouço denso. O projeto foi concebido para esse arcabouço desde '
         'a arquitetura:')
add_table(doc, ['Esfera', 'Instrumento', 'Aplicação ao Tupan'],
          [['INMETRO', 'Portaria 344/2017 [26]', 'Certificação de sistemas de tratamento de água para consumo humano; rota do produto comercial'],
           ['ANVISA', 'Portaria de Consolidação nº 5, Anexo XX [25]', 'Parâmetros de potabilidade; alvo do pós-tratamento (UV e minerais)'],
           ['ABNT', 'NBR 5410:2004 [29]', 'Instalações elétricas de baixa tensão (segurança elétrica)'],
           ['ABNT', 'NBR 14724:2011 [30]', 'Formatação de trabalho acadêmico (este documento)'],
           ['Saneamento', 'Lei 11.445/2007 e 14.026/2020 [21]', 'Insere o dispositivo como solução complementar descentralizada'],
           ['Resíduos', 'Lei 12.305/2010 (PNRS) [22]', 'Logística reversa do sal exaurido e do REEE'],
           ['Dados', 'Lei 13.709/2018 (LGPD) [23]', 'Telemetria local por projeto; sem dado pessoal para operar'],
           ['Energia', 'Lei 14.541/2023 (TSEE) [24] e ANEEL REN 1.000/2021 [27]', 'Enquadramento tarifário e desconto social'],
           ['Águas', 'CONAMA 357/2005 [28]', 'Referência de classificação de corpos hídricos (contexto de reúso/descarte)']],
          widths=[2.4, 5.6, 8.4])
add_callout(doc, 'Conformidade como projeto, não como burocracia',
            'A câmara UV opaca com intertravamento, o perfil mineral '
            'documentado (Ca 45 / Mg 18 mg/L) e o registro auditável de cada '
            'ciclo são decisões de engenharia orientadas por INMETRO/ANVISA — '
            'e não adaptações posteriores.', VERDE_CLARO)

add_page_break(doc)

# ===========================================================================
# 5 INSTRUÇÕES COMPUTACIONAIS
# ===========================================================================
add_heading(doc, '5 Instruções Computacionais', 1)
add_para(doc, 'A reprodução integral deste trabalho requer apenas um '
         'toolchain GNU com C++23, Python ≥ 3.10, CMake e, opcionalmente, '
         'Qt5. Os comandos abaixo reproduzem todos os resultados das Seções 4:')
add_subheading(doc, '5.1 Núcleo nativo e testes')
add_code(doc, 'cmake -S src/core -B build -DCMAKE_BUILD_TYPE=Release\n'
              'cmake --build build -j"$(nproc)"        # gera src/core e build/tupan_sim\n'
              './build/tupan_tests                     # 35 testes unitários (C++)\n'
              './build/tupan_sim --night 8 --day 6 --ur 68 --temp 24\n'
              './build/tupan_sim --json                # saída legível por máquina',
         'Quadro 4 — Compilação, teste e simulação do núcleo C++23.')
add_subheading(doc, '5.2 Esteira de dados e custo de energia')
add_code(doc, 'cd tools/pipeline\n'
              'python3 analise_dados.py   # ERA5/Open-Meteo + ML + projeções\n'
              'python3 custo_energia.py   # tarifas ANEEL + bandeiras + TSEE',
         'Quadro 5 — Pipeline de dados climáticos e econômicos.')
add_subheading(doc, '5.3 Servidor web e testes Python')
add_code(doc, 'cd tools/server && python3 simulador_tupan.py   # :5000\n'
              'cd tools/tests  && python3 -m pytest -q         # 21 testes',
         'Quadro 6 — Simulador web e suíte Python.')
add_subheading(doc, '5.4 Firmware')
add_code(doc, 'cd src/firmware\n'
              '# Arduino IDE: abrir tupan_firmware.hpp + main.cpp (Mega 2560)\n'
              '# PlatformIO:  pio run && pio run -t upload',
         'Quadro 7 — Compilação do firmware MVC/FSM.')
add_subheading(doc, '5.5 Interface interativa e scripting (Lua)')
add_code(doc, './build/tupan_studio        # UI: DSL Lua (sol2) + Dear ImGui + OpenGL 3.3\n'
              './build/tupan_script        # scripts headless: módulo tupan.* (luaaa)\n'
              '# a cena/menus vivem em src/studio/assets/studio.lua (recarregável)',
         'Quadro 8 — Studio interativo e runner Lua headless.')
add_para(doc, 'A interface gráfica substitui a antiga GUI Qt por um studio cujo '
         'layout é um DSL Lua declarativo (formato de tabelas aninhadas, análogo '
         'a JSON) lido via sol2; a cena 3D usa OpenGL 3.3 e uma camada própria de '
         'álgebra linear (`math.hpp`, escalar `float`, `Mat4` column-major com '
         '`union`). No sentido inverso, o runner headless usa `luaaa` para expor '
         'o núcleo físico ao Lua. Ambos consomem `full_cycle(...)`, preservando a '
         'paridade numérica com CLI, pybind11 e serviço web.')
add_para(doc, 'Os contratos de dados entre serviços são JSON/CSV estáveis '
         '(`data/`), e o desenho de microsserviços garante que o '
         'mesmo núcleo alimente CLI, studio, web e firmware — requisito de '
         'manutenibilidade conforme ISO/IEC 25010 [17].')

# ===========================================================================
# 6 CONSIDERAÇÕES FINAIS
# ===========================================================================
add_heading(doc, '6 Considerações Finais', 1)
add_para(doc, 'O trabalho demonstra a viabilidade técnica de um gerador de '
         'água atmosférica sem compressor para o semiárido brasileiro, com '
         'produção de 0,68 L/ciclo, 593,8 L/ano por unidade e eficiência de '
         '0,43 L/kWh. A modelagem físico-química — sorção de CaCl₂, '
         'regeneração por solenoide a 120 °C, destilação em vidraria e '
         'pós-tratamento mineralizante/UV — foi validada por 56 testes '
         'automatizados e por dados climáticos reais. O custo energético varia '
         'de R$ 2,36/L (tarifa plena) a R$ 0,83/L (Tarifa Social).')
add_para(doc, 'A principal contribuição crítica é a advertência de escala: '
         'sem solarização e logística reversa do sal, a adoção massiva '
         'desloca o problema ambiental em vez de resolvê-lo. Trabalhos '
         'futuros incluem ensaio laboratorial de potabilidade segundo '
         'parâmetros ANVISA, protótipo com sensores reais, e avaliação de '
         'ciclo de vida completa.')

# ===========================================================================
# REFERÊNCIAS (ABNT NBR 6023 — mistura brasileira e internacional)
# ===========================================================================
add_heading(doc, 'Referências', 1)
refs = [
    'HERSBACH, H. et al. The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, v. 146, n. 730, p. 1999–2049, 2020.',
    'LAWRENCE, M. G. The relationship between relative humidity and the dewpoint temperature in moist air. Bulletin of the American Meteorological Society, v. 86, n. 2, p. 225–234, 2005.',
    'CENGEL, Y. A.; BOLES, M. A. Thermodynamics: an engineering approach. 9. ed. New York: McGraw-Hill, 2019.',
    'INCROPERA, F. P.; DEWITT, D. P.; BERGMAN, T. L.; LAVINE, A. S. Fundamentals of heat and mass transfer. 8. ed. Hoboken: Wiley, 2018.',
    'GEANKOPLIS, C. J. Transport processes and separation process principles. 5. ed. Upper Saddle River: Prentice Hall, 2018.',
    'MILANI, D. et al. Modeling and simulation of an atmospheric water generator using a liquid desiccant. Applied Thermal Engineering, v. 89, p. 426–436, 2015.',
    'GIDO, B.; FRIEDLER, E.; BRODAY, D. M. Assessment of atmospheric water vapor flux distribution: availability for fresh water extraction. Water Research, v. 105, p. 119–129, 2016.',
    'BEYSENS, D. et al. Dew water collector for potable water in Ajaccio (Corsica Island, France). Atmospheric Research, v. 86, n. 3–4, p. 291–302, 2007.',
    'METROPOLIS, N.; ULAM, S. The Monte Carlo method. Journal of the American Statistical Association, v. 44, n. 247, p. 335–341, 1949.',
    'MARSAAGLIA, G. Xorshift RNGs. Journal of Statistical Software, v. 8, n. 14, p. 1–6, 2003.',
    'PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. Journal of Machine Learning Research, v. 12, p. 2825–2830, 2011.',
    'PASZKE, A. et al. PyTorch: an imperative style, high-performance deep learning library. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS, 32., 2019. Proceedings [...]. 2019.',
    'HOERL, A. E.; KENNARD, R. W. Ridge regression: biased estimation for nonorthogonal problems. Technometrics, v. 12, n. 1, p. 55–67, 1970.',
    'CHICK, H. An investigation of the laws of disinfection. Journal of Hygiene, v. 8, n. 1, p. 92–158, 1908.',
    'PEEL, M. C.; FINLAYSON, B. L.; MCMAHON, T. A. Updated world map of the Köppen-Geiger climate classification. Hydrology and Earth System Sciences, v. 11, p. 1633–1644, 2007.',
    'OASIS. MQTT Version 5.0. OASIS Standard, 2019. Disponível em: https://docs.oasis-open.org/mqtt/mqtt/v5.0/. Acesso em: 2026.',
    'INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. ISO/IEC 25010:2011 — Systems and software engineering: quality requirements and evaluation. Geneva: ISO, 2011.',
    'WORLD METEOROLOGICAL ORGANIZATION. Guide to meteorological instruments and methods of observation. WMO-No. 8. Geneva: WMO, 2021.',
    'AGÊNCIA NACIONAL DE ÁGUAS E SANEAMENTO BÁSICO. Atlas Águas: abastecimento urbano de água. Brasília: ANA, 2021.',
    'MARENGO, J. A.; TORRES, R. R.; ALVES, L. M. Drought in Northeast Brazil: past, present, and future. Theoretical and Applied Climatology, v. 129, p. 1189–1200, 2017.',
    'BRASIL. Lei nº 11.445, de 5 de janeiro de 2007. Estabelece diretrizes nacionais para o saneamento básico. Diário Oficial da União, Brasília, 2007.',
    'BRASIL. Lei nº 12.305, de 2 de agosto de 2010. Institui a Política Nacional de Resíduos Sólidos. Diário Oficial da União, Brasília, 2010.',
    'BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD). Diário Oficial da União, Brasília, 2018.',
    'BRASIL. Lei nº 14.541, de 3 de abril de 2023. Dispõe sobre a Tarifa Social de Energia Elétrica. Diário Oficial da União, Brasília, 2023.',
    'AGÊNCIA NACIONAL DE VIGILÂNCIA SANITÁRIA. Portaria de Consolidação nº 5, de 28 de setembro de 2017, Anexo XX: potabilidade da água para consumo humano. Brasília: ANVISA, 2017.',
    'INSTITUTO NACIONAL DE METROLOGIA, QUALIDADE E TECNOLOGIA. Portaria nº 344, de 25 de julho de 2017: requisitos para sistemas de tratamento de água para consumo humano. Brasília: INMETRO, 2017.',
    'AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA. Resolução Normativa nº 1.000, de 7 de dezembro de 2021. Brasília: ANEEL, 2021.',
    'CONSELHO NACIONAL DO MEIO AMBIENTE. Resolução nº 357, de 17 de março de 2005: classificação dos corpos de água. Brasília: CONAMA, 2005.',
    'ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. NBR 5410: instalações elétricas de baixa tensão. Rio de Janeiro: ABNT, 2004.',
    'ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. NBR 14724: informação e documentação — trabalhos acadêmicos. Rio de Janeiro: ABNT, 2011.',
    'INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA. Censo Demográfico 2022. Rio de Janeiro: IBGE, 2023.',
    'SUPERINTENDÊNCIA DO DESENVOLVIMENTO DO NORDESTE. Delimitação do semiárido brasileiro. Recife: SUDENE, 2021.',
    'REBOUÇAS, A. C. Águas subterrâneas. In: REBOUÇAS, A. C.; BRAGA, B.; TUNDISI, J. G. (org.). Águas doces no Brasil: capital ecológico, uso e conservação. 3. ed. São Paulo: Escrituras, 2006.',
]
for i, ref in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.27)
    p.paragraph_format.first_line_indent = Cm(-1.27)
    p.add_run(f'[{i}] {ref}')

add_page_break(doc)

# ===========================================================================
# APÊNDICES
# ===========================================================================
add_heading(doc, 'Apêndice A — Lista de Materiais (BOM)', 1)
add_table(doc, ['#', 'Item', 'Especificação', 'Qtd', 'R$'],
          [['1', 'Arduino Mega 2560', 'ATmega2560', '1', '120'],
           ['2', 'Ventoinhas 12 V', '120 mm, 2,5 W', '3', '30'],
           ['3', 'Solenoide/resistência', '250 W, 12/24 V', '1', '60'],
           ['4', 'Servo MG996R', 'registo de ar', '1', '35'],
           ['5', 'MOSFET IRLZ44N', 'drive ventoinhas/solenoide', '2', '12'],
           ['6', 'DHT22', 'UR + temperatura', '1', '40'],
           ['7', 'DS18B20 (à prova d\'água)', 'leito e vapor', '2', '30'],
           ['8', 'Sensor de nível capacitivo', 'XKC-Y25-V', '1', '25'],
           ['9', 'CaCl₂ grau técnico', '2 kg (pérolas)', '1', '30'],
           ['10', 'Vidraria de laboratório', 'balão + condensador (reciclado)', '1', '0–80'],
           ['11', 'Filtro mineralizante', 'cartucho com calcita/dolomita', '1', '45'],
           ['12', 'Lâmpada UV-C', '6 W, 254 nm + reator', '1', '40'],
           ['13', 'Fonte 12 V 30 A', '360 W', '1', '90'],
           ['14', 'Módulo HC-05', 'Bluetooth SPP', '1', '25'],
           ['15', 'Estrutura', 'PLA impresso + MDF/acrílico', '—', '30'],
           ['16', 'Bacia com torneira', '2 L, grau alimentício', '1', '15']],
          widths=[1.0, 4.2, 5.2, 1.2, 1.8])
add_para(doc, 'Custo estimado em peças novas ≈ R$ 447; com componentes '
         'comumente já possuídos (Mega, HC-05, servos, ventoinhas), o custo '
         'real tende a R$ 300–350.')

add_heading(doc, 'Apêndice B — Glossário', 1)
glossary = [
    ('AWG', 'Atmospheric Water Generator — gerador de água atmosférica.'),
    ('CaCl₂', 'Cloreto de cálcio, dessecante deliquescente usado no leito.'),
    ('FSM', 'Finite State Machine — máquina de estados finitos.'),
    ('LMTD', 'Log Mean Temperature Difference — diferença média logarítmica de temperatura.'),
    ('LSI', 'Langelier Saturation Index — índice de saturação de carbonato.'),
    ('MVC', 'Model-View-Controller — padrão arquitetural de software.'),
    ('PNRS', 'Política Nacional de Resíduos Sólidos (Lei 12.305/2010).'),
    ('RPN', 'Risk Priority Number — prioridade de risco em FMEA.'),
    ('TSEE', 'Tarifa Social de Energia Elétrica (Lei 14.541/2023).'),
    ('UV-C', 'Radiação ultravioleta germicida em 254 nm.'),
]
add_table(doc, ['Sigla', 'Definição'], [[s, d] for s, d in glossary], widths=[2.5, 13])

add_heading(doc, 'Apêndice C — Pinagem do firmware', 1)
add_table(doc, ['Pino Mega', 'Função', 'Observação'],
          [['D2', 'DHT22 (dados)', 'pull-up 10 kΩ'],
           ['D3 / D4', 'DS18B20 leito / vapor', 'OneWire, pull-up 4,7 kΩ'],
           ['A0', 'Nível da bacia', 'analógico 0–5 V'],
           ['D5', 'Ventoinhas (PWM)', 'MOSFET + R 220 Ω'],
           ['D6', 'Solenoide', 'relé/MOSFET — nunca direto'],
           ['D9', 'Servo-registro', 'fonte 5 V dedicada'],
           ['A2/A3/A4', 'Botões cima/baixo/select', 'pull-up interno'],
           ['D22/23/24', 'LEDs verde/amarelo/vermelho', 'R 330 Ω'],
           ['TX1/RX0', 'HC-05', 'divisor resistivo no RX do Mega']],
          widths=[2.6, 5.2, 7.2])

# --- SALVAR ---------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(str(OUT))
print(f'Relatório científico salvo em: {OUT}')
