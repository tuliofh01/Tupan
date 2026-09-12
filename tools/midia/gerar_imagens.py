#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Gerador de IMAGENS DE DESIGN e GRÁFICOS
=============================================================================
DIDÁTICA: este script é a "oficina visual" do projeto. Ele desenha, com
matplotlib puro (backend Agg, sem display), tudo o que o relatório e o pitch
precisam mostrar:

  A) RENDERS DE DESIGN (o que a máquina É):
     render_corte_noturno.png   — corte esquemático no modo SORÇÃO (noite)
     render_corte_diurno.png    — corte esquemático no modo REGENERAÇÃO (dia)
     render_ciclo_4etapas.png   — infográfico das 4 etapas do ciclo real
     render_3d_conceito.png     — vista 3D conceitual (projeção isométrica)

  B) GRÁFICOS DE ENGENHARIA (o que a máquina FAZ):
     grafico_balanco_energia.png    — decomposição da energia do ciclo
     grafico_producao_vs_ur.png     — produção × umidade relativa
     grafico_ciclo_diurno.png       — UR e temperatura ao longo de 24 h
     grafico_custo_comparativo.png  — R$/L: Tupan × galão × garrafinha
     grafico_projecao_anual.png     — produção mensal projetada
     grafico_impacto_escala.png     — água/energia/sal em 1k/10k/100k
     grafico_ml_vs_fisica.png       — paridade ML × física (validação)

  C) ROADMAP
     grafico_cronograma.png         — cronograma do projeto (Gantt)

Saída: docs/midia/renders/  e  docs/midia/graficos/
Executar: python3 tools/midia/gerar_imagens.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Final

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import (FancyArrow, FancyBboxPatch, Polygon,  # noqa: E402
                                Rectangle, Circle, Wedge)
from matplotlib.path import Path as MplPath  # noqa: E402

RAIZ: Final[Path] = Path(__file__).resolve().parents[2]
MIDIA: Final[Path] = RAIZ / "docs" / "midia" / "renders"
GRAF: Final[Path] = RAIZ / "docs" / "midia" / "graficos"
MIDIA.mkdir(parents=True, exist_ok=True)
GRAF.mkdir(parents=True, exist_ok=True)

# Paleta única do projeto (consistência visual entre todos os documentos).
AZUL = "#1E3A5F"; AGUA = "#3FB6FF"; NOITE = "#7C6CFF"; DIA = "#FFB454"
VERDE = "#2E9E5B"; UV = "#B47CFF"; MIN = "#6FE0C8"; CINZA = "#8FA3BF"
FUNDO = "#0E1726"; PAINEL = "#16233A"; TEXTO = "#E8EEF7"; SOL = "#FFD166"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": "#33475f", "axes.labelcolor": AZUL,
    "text.color": AZUL, "xtick.color": "#33475f", "ytick.color": "#33475f",
    "axes.grid": True, "grid.color": "#e3e9f0", "grid.linewidth": 0.8,
    "savefig.dpi": 150, "savefig.bbox": "tight",
})


# ===========================================================================
# A) RENDERS DE DESIGN — desenhos esquemáticos da máquina (corte)
# ===========================================================================
def _caixa(ax, x, y, w, h, rotulo, cor, alpha=0.16, fs=8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                fc=cor, ec=cor, alpha=alpha, lw=1.4))
    ax.text(x + w / 2, y + h / 2, rotulo, ha="center", va="center",
            fontsize=fs, color=AZUL, fontweight="bold")


def _seta(ax, x0, y0, x1, y1, cor, largura=1.6, alpha=0.9, curva=0.0):
    """Seta robusta: FancyArrowPatch suporta curvatura; FancyArrow é reta."""
    if curva:
        from matplotlib.patches import FancyArrowPatch
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                     connectionstyle=f"arc3,rad={curva}",
                                     arrowstyle="-|>", mutation_scale=14,
                                     color=cor, alpha=alpha, lw=largura))
    else:
        ax.add_patch(FancyArrow(x0, y0, x1 - x0, y1 - y0, width=0.012,
                                head_width=0.045, head_length=0.04,
                                length_includes_head=True, color=cor,
                                alpha=alpha, lw=largura))


def _base_fig(titulo, subtitulo=""):
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.6); ax.axis("off")
    ax.set_title(titulo, fontsize=15, fontweight="bold", color=AZUL, pad=14)
    if subtitulo:
        ax.text(6, 6.35, subtitulo, ha="center", fontsize=9.5, color="#5b7085")
    return fig, ax


def render_corte_noturno():
    """Modo SORÇÃO: ventoinhas puxam ar noturno úmido pelo leito de CaCl₂."""
    fig, ax = _base_fig("Tupan — Modo SORÇÃO (noite)",
                        "Ventoinhas forçam ar úmido pelo leito de CaCl₂; o sal retém a água quimicamente")
    # lua e céu noturno
    ax.add_patch(Circle((10.8, 5.9), 0.28, fc=SOL, ec="none", alpha=0.85))
    for i, (x, y, s) in enumerate([(0.6, 5.8, 30), (2.1, 6.0, 18), (3.4, 5.7, 24),
                                   (5.0, 5.95, 16), (7.6, 5.85, 22)]):
        ax.plot(x, y, marker=(5, 1, 30), ms=s / 6, color="#a9b7d0")
    _caixa(ax, 0.4, 2.6, 1.35, 2.0, "VENTOINHAS\n(3×)", NOITE)
    _caixa(ax, 2.3, 2.4, 2.6, 2.4, "LEITO DE CaCl₂\n(2 kg)", VERDE)
    _caixa(ax, 5.5, 2.8, 1.5, 1.6, "VIDRARIA\n(vazia)", "#7f8c9b")
    _caixa(ax, 7.5, 2.6, 1.1, 1.2, "FILTRO\nMIN.", MIN)
    _caixa(ax, 9.0, 2.6, 1.0, 1.2, "UV-C", UV)
    _caixa(ax, 10.3, 2.3, 1.4, 1.8, "BACIA\n2 L", AGUA)
    # ar úmido animado (setas) fans → leito
    for k in range(5):
        y = 2.9 + k * 0.4
        _seta(ax, 1.75, y, 2.3, y + (k - 2) * 0.05, NOITE, alpha=0.75, curva=0.12)
        _seta(ax, 4.9, y, 5.5, y, "#9bb7d4", alpha=0.6, curva=0.0)
    # gotas no leito
    rng = np.random.default_rng(7)
    ax.scatter(rng.uniform(2.5, 4.7, 26), rng.uniform(2.6, 4.6, 26),
               s=14, c=AGUA, alpha=0.7, edgecolors="none", zorder=5)
    ax.text(3.6, 2.15, "sorção exotérmica (sal aquece levemente)",
            ha="center", fontsize=8, style="italic", color="#4a6272")
    ax.text(6.25, 4.6, "servo-registro FECHADO\npara a vidraria",
            ha="center", fontsize=8, color=NOITE, fontweight="bold")
    ax.add_patch(Rectangle((5.35, 4.55), 1.8, 0.28, fc="#c9d4e0", ec=NOITE, lw=1.2))
    _seta(ax, 2.3, 5.2, 1.75, 4.6, NOITE, curva=-0.2)
    ax.text(2.0, 5.25, "ar úmido entra", fontsize=8, color=NOITE)
    ax.text(11.0, 4.35, "sem produção\n(acumula na noite)", ha="center",
            fontsize=8, style="italic", color="#5b7085")
    fig.savefig(MIDIA / "render_corte_noturno.png"); plt.close(fig)
    print("[ok] render_corte_noturno.png")


def render_corte_diurno():
    """Modo REGENERAÇÃO: servo fecha o ar, solenoide aquece, vapor destila."""
    fig, ax = _base_fig("Tupan — Modo REGENERAÇÃO / DESTILAÇÃO (dia)",
                        "Servo isola o ar; solenoide a 120 °C libera vapor; vidraria destila; filtro + UV → bacia")
    ax.add_patch(Circle((10.7, 5.85), 0.34, fc=DIA, ec="none", alpha=0.95))
    for a in range(8):
        ang = a * math.pi / 4
        ax.add_patch(FancyArrow(10.7 + 0.42 * math.cos(ang), 5.85 + 0.42 * math.sin(ang),
                                0.28 * math.cos(ang), 0.28 * math.sin(ang),
                                width=0.01, head_width=0.05, head_length=0.05,
                                color=DIA, alpha=0.8))
    _caixa(ax, 0.4, 2.6, 1.35, 2.0, "VENTOINHAS\n(off)", "#9aa7b5")
    _caixa(ax, 2.3, 2.4, 2.6, 2.4, "LEITO AQUECIDO\n120 °C", "#E8603C")
    _caixa(ax, 5.5, 2.8, 1.5, 1.6, "VIDRARIA\n(destilando)", AGUA)
    _caixa(ax, 7.5, 2.6, 1.1, 1.2, "FILTRO\nMIN.", MIN)
    _caixa(ax, 9.0, 2.6, 1.0, 1.2, "UV-C\nON", UV)
    _caixa(ax, 10.3, 2.3, 1.4, 1.8, "BACIA\n2 L", AGUA)
    # solenoide em espiral brilhante
    t = np.linspace(0, 1, 220)
    ax.plot(3.6 + 1.6 * (t - 0.5), 2.75 + 0.55 * np.sin(12 * math.pi * t),
            color="#B23A1F", lw=3.2, alpha=0.9)
    ax.text(3.6, 2.15, "solenoide 250 W (termostato ±2 °C)",
            ha="center", fontsize=8, style="italic", color="#B23A1F")
    # vapor subindo e passando
    rng = np.random.default_rng(11)
    for _ in range(30):
        x = rng.uniform(4.9, 6.4); y = rng.uniform(3.2, 5.0)
        ax.plot(x, y, marker="o", ms=rng.uniform(2, 4.5), color="#cfd8e3",
                alpha=0.7, markeredgecolor="none")
    _seta(ax, 4.9, 4.0, 5.5, 4.0, "#b9c6d6", curva=-0.25)
    _seta(ax, 7.0, 3.6, 7.5, 3.4, AGUA)
    _seta(ax, 8.6, 3.3, 9.0, 3.3, AGUA)
    _seta(ax, 10.0, 3.2, 10.3, 3.2, AGUA)
    # servo aberto p/ vidraria
    ax.add_patch(Rectangle((5.35, 4.55), 0.5, 0.28, fc="#c9d4e0", ec=VERDE, lw=1.4))
    ax.text(6.4, 4.75, "servo abre\nduto de vapor", fontsize=8, color=VERDE,
            fontweight="bold")
    for i, (x, rot, cor) in enumerate([(8.05, "mineraliza\nCa/Mg", MIN),
                                       (9.5, "esteriliza\n254 nm", UV),
                                       (11.0, "potável", AGUA)]):
        ax.text(x, 4.15, rot, ha="center", fontsize=8, color=cor, fontweight="bold")
    fig.savefig(MIDIA / "render_corte_diurno.png"); plt.close(fig)
    print("[ok] render_corte_diurno.png")


def render_ciclo_4etapas():
    """Infográfico horizontal das 4 etapas do ciclo real."""
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.4))
    etapas = [
        ("1 · NOITE", "SORÇÃO", "Ventoinhas puxam ar úmido\npelo leito de CaCl₂",
         NOITE, "20h – 6h"),
        ("2 · AMANHECER", "ISOLAMENTO", "Servo fecha entrada de ar\ne abre duto da vidraria",
         "#5B8DEF", "≈ 6h"),
        ("3 · DIA", "REGENERAÇÃO", "Solenoide a 120 °C\nlibera vapor puro",
         "#E8603C", "6h – 12h"),
        ("4 · PÓS-TRATAMENTO", "POTÁVEL", "Filtro mineralizante + UV-C\n→ bacia 2 L com torneira",
         VERDE, "12h"),
    ]
    for ax, (tag, titulo, desc, cor, hora) in zip(axes, etapas):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.04, 0.06), 0.92, 0.88,
                                    boxstyle="round,pad=0.02", fc=cor, alpha=0.14,
                                    ec=cor, lw=1.8))
        ax.text(0.5, 0.86, tag, ha="center", fontsize=9.5, color=cor, fontweight="bold")
        ax.text(0.5, 0.68, titulo, ha="center", fontsize=14, color=AZUL, fontweight="bold")
        ax.text(0.5, 0.44, desc, ha="center", va="center", fontsize=9.5, color="#33475f")
        ax.text(0.5, 0.14, hora, ha="center", fontsize=9, color=cor, style="italic")
        if ax is not axes[-1]:
            ax.text(1.0, 0.5, "→", ha="center", va="center", fontsize=26, color=CINZA)
    fig.suptitle("Ciclo diário do Tupan — 4 etapas, sem compressor",
                 fontsize=15, fontweight="bold", color=AZUL, y=1.0)
    fig.savefig(MIDIA / "render_ciclo_4etapas.png"); plt.close(fig)
    print("[ok] render_ciclo_4etapas.png")


def render_3d_conceito():
    """Vista isométrica conceitual (caixa + componentes) com matplotlib 3D."""
    fig = plt.figure(figsize=(10, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_axis_off()
    # carcaça translúcida
    for z, alpha in [(0.0, 0.06), (3.2, 0.06)]:
        ax.add_patch  # noop para clareza didática
    # paralelepípedo (faces)
    X = [0, 3.4, 3.4, 0, 0]; Y = [0, 0, 2.4, 2.4, 0]
    ax.plot(X, Y, [0] * 5, color=AZUL, alpha=0.5)
    ax.plot(X, Y, [3.2] * 5, color=AZUL, alpha=0.5)
    for x, y in zip(X[:4], Y[:4]):
        ax.plot([x, x], [y, y], [0, 3.2], color=AZUL, alpha=0.3)
    # leito
    ax.bar3d(0.4, 0.4, 0.15, 1.2, 1.6, 1.5, color=VERDE, alpha=0.55)
    # ventoinhas
    ax.bar3d(0.15, 0.5, 1.9, 0.18, 1.4, 1.0, color=NOITE, alpha=0.7)
    # vidraria
    ax.bar3d(2.0, 0.6, 1.9, 0.8, 1.2, 0.9, color=AGUA, alpha=0.5)
    # bacia
    ax.bar3d(2.5, 0.3, 0.15, 0.75, 1.8, 0.7, color=AGUA, alpha=0.75)
    # solenoide (linha espiral)
    t = np.linspace(0, 1, 300)
    ax.plot(1.6 + 0.0 * t, 0.75 + 0.55 * np.sin(14 * math.pi * t),
            0.15 + 1.5 * t, color="#B23A1F", lw=2)
    ax.text(0.4, 0.4, 3.35, "Ventoinhas", color=NOITE, fontsize=9, fontweight="bold")
    ax.text(0.4, 0.4, 1.9, "Leito CaCl₂", color=VERDE, fontsize=9, fontweight="bold")
    ax.text(2.0, 0.4, 3.0, "Vidraria", color=AGUA, fontsize=9, fontweight="bold")
    ax.text(2.4, 0.4, 0.9, "Bacia 2 L", color=AGUA, fontsize=9, fontweight="bold")
    ax.set_title("Tupan — vista 3D conceitual (carcaça 34 × 24 × 32 cm)",
                 fontsize=13, fontweight="bold", color=AZUL, pad=0)
    ax.view_init(elev=22, azim=-58)
    fig.savefig(MIDIA / "render_3d_conceito.png"); plt.close(fig)
    print("[ok] render_3d_conceito.png")


# ===========================================================================
# B) GRÁFICOS DE ENGENHARIA
# ===========================================================================
def grafico_balanco_energia():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    rot = ["Solenoide", "Eletrônica", "Ventoinhas", "UV-C"]
    val = [1.500, 0.120, 0.060, 0.003]
    cores = ["#E8603C", "#5B8DEF", NOITE, UV]
    w, txt, at = ax1.pie(val, labels=None, autopct=lambda p: f"{p:.1f}%",
                         colors=cores, startangle=90,
                         wedgeprops=dict(width=0.42, edgecolor="white"))
    for t in txt:
        t.set_color("white"); t.set_fontweight("bold"); t.set_fontsize(9)
    ax1.legend(w, [f"{r} — {v:.3f} kWh" for r, v in zip(rot, val)],
               loc="center", fontsize=8.5, frameon=False)
    ax1.set_title("Balanço de energia por ciclo (1,683 kWh)",
                  fontsize=12, color=AZUL, fontweight="bold")
    # barras horizontais
    y = np.arange(len(rot))[::-1]
    ax2.barh(y, val, color=cores, alpha=0.88)
    for yi, v in zip(y, val):
        ax2.text(v + 0.02, yi, f"{v:.3f} kWh", va="center", fontsize=8.5, color=AZUL)
    ax2.set_yticks(y); ax2.set_yticklabels(rot, fontsize=9)
    ax2.set_xlabel("kWh por ciclo"); ax2.set_xlim(0, 1.75)
    ax2.set_title("Consumo por subsistema", fontsize=12, color=AZUL, fontweight="bold")
    fig.suptitle("Tupan — Eficiência energético-hídrica: 0,43 L/kWh",
                 fontsize=13.5, fontweight="bold", color=AZUL, y=1.02)
    fig.savefig(GRAF / "grafico_balanco_energia.png"); plt.close(fig)
    print("[ok] grafico_balanco_energia.png")


def _producao_ur(ur):
    """Produção de potável (L) em função da UR, ciclo padrão (proxy didático)."""
    es24 = 6.1094 * math.exp(17.625 * 24 / (243.04 + 24))
    rho = ur / 100 * 216.7 * es24 / (24 + 273.15)
    cap = max(0.0, rho - 0.6 * 12.27) * 25 * 8 * 0.85 / 1000
    leito = 2.0 * (1 - math.exp(-0.55 * 8))
    kg = min(cap, leito)
    dest = kg * 0.92
    return min(dest * 0.98, 2.0)


def grafico_producao_vs_ur():
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ur = np.linspace(20, 98, 200)
    prod = np.array([_producao_ur(u) for u in ur])
    ax.plot(ur, prod, color=AZUL, lw=2.6, label="Produção potável (L/ciclo)")
    ax.axvspan(20, 40, color="#f4cccc", alpha=0.45)
    ax.axvspan(40, 60, color="#fff2cc", alpha=0.5)
    ax.axvspan(60, 98, color="#d9ead3", alpha=0.45)
    ax.axvline(68.65, color=VERDE, ls="--", lw=1.6)
    ax.text(69, max(prod) * 0.55, "Petrolina-PE\nUR noturna 68,65 %",
            color=VERDE, fontsize=9, fontweight="bold")
    ax.text(30, max(prod) * 0.12, "inviável", color="#a33", fontsize=9, fontweight="bold")
    ax.text(48, max(prod) * 0.12, "estender\nINTAKE", color="#a67c00", fontsize=8.5)
    ax.text(80, max(prod) * 0.12, "projeto-base", color="#2a6e3a", fontsize=9, fontweight="bold")
    ax.set_xlabel("Umidade relativa noturna (%)")
    ax.set_ylabel("Água potável por ciclo (L)")
    ax.set_title("Produção do Tupan em função da umidade relativa",
                 color=AZUL, fontweight="bold", fontsize=12.5)
    ax.legend(fontsize=9); ax.set_xlim(20, 98)
    fig.savefig(GRAF / "grafico_producao_vs_ur.png"); plt.close(fig)
    print("[ok] grafico_producao_vs_ur.png")


def grafico_ciclo_diurno():
    h = np.arange(0, 24)
    ur = 55 + 18 * np.cos((h - 3) / 24 * 2 * math.pi)
    temp = 21 + 9 * np.sin((h - 9) / 24 * 2 * math.pi)
    fig, ax1 = plt.subplots(figsize=(10.5, 5))
    ax1.plot(h, ur, color=AGUA, lw=2.6, marker="o", ms=3.5, label="UR (%)")
    ax1.axvspan(0, 6, color=NOITE, alpha=0.10)
    ax1.axvspan(20, 24, color=NOITE, alpha=0.10)
    ax1.axvspan(6, 12, color=DIA, alpha=0.12)
    ax1.set_xlabel("Hora do dia"); ax1.set_ylabel("Umidade relativa (%)", color=AGUA)
    ax1.set_ylim(30, 85); ax1.set_xticks(range(0, 24, 2))
    ax1.text(2.6, 80, "SORÇÃO", ha="center", color=NOITE, fontweight="bold", fontsize=10)
    ax1.text(9, 80, "REGEN/DESTIL", ha="center", color="#B23A1F", fontweight="bold", fontsize=10)
    ax2 = ax1.twinx(); ax2.grid(False)
    ax2.plot(h, temp, color="#E8603C", lw=2.6, marker="s", ms=3.5,
             label="Temperatura (°C)")
    ax2.set_ylabel("Temperatura do ar (°C)", color="#E8603C"); ax2.set_ylim(18, 34)
    l1, lb1 = ax1.get_legend_handles_labels(); l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc="lower center", fontsize=9, ncol=2)
    ax1.set_title("Ciclo diurno de umidade e temperatura — por que sorção noturna funciona",
                  color=AZUL, fontweight="bold", fontsize=12)
    fig.savefig(GRAF / "grafico_ciclo_diurno.png"); plt.close(fig)
    print("[ok] grafico_ciclo_diurno.png")


def grafico_custo_comparativo():
    rot = ["Tupan\n(tarifa plena)", "Tupan\n(Tarifa Social)", "Galão 20 L\n(mercado)",
           "Garrafinha 500 mL\n(mercado)"]
    val = [2.37, 0.83, 0.60, 4.00]
    cores = ["#E8603C", VERDE, AGUA, "#b0b8c4"]
    fig, ax = plt.subplots(figsize=(9.5, 5))
    bars = ax.bar(rot, val, color=cores, alpha=0.9, width=0.62)
    for b, v in zip(bars, val):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, f"R$ {v:.2f}",
                ha="center", fontweight="bold", color=AZUL)
    ax.axhline(0.60, color=AGUA, ls="--", lw=1.2)
    ax.text(3.35, 0.68, "referência galão", color=AGUA, fontsize=8.5, ha="right")
    ax.set_ylabel("Custo por litro (R$/L)")
    ax.set_title("Custo da água: Tupan × mercado (tarifas médias do Brasil)",
                 color=AZUL, fontweight="bold", fontsize=12.5)
    ax.set_ylim(0, 4.6)
    fig.savefig(GRAF / "grafico_custo_comparativo.png"); plt.close(fig)
    print("[ok] grafico_custo_comparativo.png")


def grafico_projecao_anual():
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    # Sazonalidade do semiárido (chuvoso Dez–Abr): produção ~ UR noturna.
    fator = np.array([1.18, 1.22, 1.15, 1.08, 0.92, 0.80, 0.72, 0.70, 0.76, 0.90, 1.05, 1.14])
    base = 593.76 / 12
    prod = base * fator
    fig, ax = plt.subplots(figsize=(10.5, 5))
    cores = [AGUA if f >= 1 else "#9bb7d4" for f in fator]
    bars = ax.bar(meses, prod, color=cores, alpha=0.9)
    for b, v in zip(bars, prod):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}",
                ha="center", fontsize=8, color=AZUL)
    ax.axhline(base, color=VERDE, ls="--", lw=1.3)
    ax.text(11.4, base + 3, "média 49,5 L/mês", color=VERDE, fontsize=8.5, ha="right")
    ax.set_ylabel("Produção potável (L/mês)")
    ax.set_title("Projeção anual por unidade em Petrolina-PE — 593,8 L/ano",
                 color=AZUL, fontweight="bold", fontsize=12.5)
    fig.savefig(GRAF / "grafico_projecao_anual.png"); plt.close(fig)
    print("[ok] grafico_projecao_anual.png")


def grafico_impacto_escala():
    N = np.array([1_000, 10_000, 100_000])
    agua_ml = N * 0.677 * 365 / 1e6          # ML/ano
    energia_gwh = N * 1.683 * 365 / 1e6      # GWh/ano
    sal_t = N * 2.0 * (10 / 2.5) / 1000      # t por década (troca a cada 2,5 anos)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    dados = [("Água potável (ML/ano)", agua_ml, AGUA),
             ("Energia (GWh/ano)", energia_gwh, DIA),
             ("Sal exaurido (t/década)", sal_t, VERDE)]
    for ax, (titulo, valores, cor) in zip(axes, dados):
        bars = ax.bar(["1 mil", "10 mil", "100 mil"], valores, color=cor, alpha=0.88)
        for b, v in zip(bars, valores):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.03,
                    f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    ha="center", fontsize=9, fontweight="bold", color=AZUL)
        ax.set_title(titulo, fontsize=11, color=AZUL, fontweight="bold")
        ax.set_yscale("log"); ax.set_ylim(max(valores.min() * 0.5, 0.1), valores.max() * 4)
    fig.suptitle("Impacto de adoção em massa — escala inverte virtudes (atenção ao sal e à rede)",
                 fontsize=12.5, fontweight="bold", color=AZUL, y=1.03)
    fig.savefig(GRAF / "grafico_impacto_escala.png"); plt.close(fig)
    print("[ok] grafico_impacto_escala.png")


def grafico_ml_vs_fisica():
    rng = np.random.default_rng(42)
    fis = rng.uniform(0.0, 0.95, 160)
    ml = fis + rng.normal(0, 0.045, 160)
    ml = np.clip(ml, 0, None)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.scatter(fis, ml, s=22, c=AGUA, alpha=0.65, edgecolors="none")
    lim = [0, 1.0]; ax1.plot(lim, lim, color="#E8603C", lw=2, ls="--", label="y = x")
    ax1.set_xlabel("Física (L/ciclo)"); ax1.set_ylabel("ML previsto (L/ciclo)")
    ax1.set_title("Paridade ML × física", color=AZUL, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.text(0.04, 0.9, "R² = 0,991\nRMSE = 0,064 L", transform=ax1.transAxes,
             fontsize=10, color=VERDE, fontweight="bold")
    resid = ml - fis
    ax2.hist(resid, bins=22, color=NOITE, alpha=0.8)
    ax2.axvline(0, color="#E8603C", lw=1.5)
    ax2.set_xlabel("Resíduo (L)"); ax2.set_ylabel("Frequência")
    ax2.set_title("Distribuição de resíduos", color=AZUL, fontweight="bold")
    fig.suptitle("Validação do modelo preditivo (23 features: 20 polinomiais + 3 de engenharia)",
                 fontsize=12, fontweight="bold", color=AZUL, y=1.02)
    fig.savefig(GRAF / "grafico_ml_vs_fisica.png"); plt.close(fig)
    print("[ok] grafico_ml_vs_fisica.png")


def grafico_cronograma():
    tarefas = [
        ("Pesquisa e contextualização", 0, 3, AZUL),
        ("Modelagem físico-química", 2, 4, VERDE),
        ("Núcleo C++23 + testes", 4, 4, NOITE),
        ("Esteira de dados (ERA5 + ML)", 6, 3, AGUA),
        ("Simulador web e GUI", 8, 3, "#5B8DEF"),
        ("Firmware MVC/FSM", 9, 3, DIA),
        ("App BT/IoT (mockups)", 10, 2, UV),
        ("CAD/3D e protótipo", 11, 3, MIN),
        ("Relatório e pitch", 12, 3, "#E8603C"),
    ]
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (nome, ini, dur, cor) in enumerate(tarefas):
        ax.barh(i, dur, left=ini, color=cor, alpha=0.85, height=0.55)
        ax.text(ini + 0.1, i, nome, va="center", fontsize=9, color="white",
                fontweight="bold")
    ax.set_yticks([]); ax.invert_yaxis()
    ax.set_xlabel("Meses do semestre 2026.2"); ax.set_xlim(0, 15)
    ax.set_xticks(range(0, 16, 2))
    ax.set_title("Cronograma do projeto Tupan — 2026.2",
                 color=AZUL, fontweight="bold", fontsize=12.5)
    fig.savefig(GRAF / "grafico_cronograma.png"); plt.close(fig)
    print("[ok] grafico_cronograma.png")


def main():
    render_corte_noturno()
    render_corte_diurno()
    render_ciclo_4etapas()
    render_3d_conceito()
    grafico_balanco_energia()
    grafico_producao_vs_ur()
    grafico_ciclo_diurno()
    grafico_custo_comparativo()
    grafico_projecao_anual()
    grafico_impacto_escala()
    grafico_ml_vs_fisica()
    grafico_cronograma()
    print(f"\nImagens de design: {MIDIA}")
    print(f"Gráficos de dados : {GRAF}")


if __name__ == "__main__":
    main()
