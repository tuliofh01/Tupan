#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Gerador de CAD/3D
=============================================================================
DIDÁTICA: sem depender de CAD proprietário, este script escreve formatos
abertos a partir das MESMAS dimensões do projeto (carcaça 34 × 24 × 32 cm):

  tupan_carcaca.dxf   — desenho técnico 2D (vista frontal, linhas + cotas)
  tupan_pecas.stl     — malha 3D ASCII dos blocos (leito, bacia, filtro…)
  tupan.scad          — modelo paramétrico OpenSCAD (editável)
  tupan_cad.png       — prancha com vistas frontal/superior/lateral

Saída: docs/midia/cad/
Uso:   python3 tools/cad/gerar_cad.py
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BASE: Final[Path] = Path(__file__).resolve().parents[2]
OUT: Final[Path] = BASE / "docs" / "midia" / "cad"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# DIMENSÕES (cm) — fonte única; o mesmo dicionário alimenta todos os formatos.
# Sistema 0..34 (x) × 0..24 (y) × 0..32 (z).
# ---------------------------------------------------------------------------
CARCACA = (34.0, 24.0, 32.0)
# nome: (x, y, z, largura, profundidade, altura)
PECAS: Final[dict[str, tuple[float, float, float, float, float, float]]] = {
    "ventoinhas": (1.0, 4.0, 16.0, 3.0, 14.0, 10.0),
    "leito_CaCl2": (5.0, 3.0, 8.0, 16.0, 16.0, 12.0),
    "vidraria": (10.0, 6.0, 20.0, 10.0, 10.0, 12.0),
    "solenoide": (8.0, 9.0, 6.0, 16.0, 4.0, 2.0),
    "filtro_mineral": (22.0, 8.0, 8.0, 5.0, 5.0, 9.0),
    "bacia": (27.0, 6.0, 4.0, 12.0, 10.0, 8.0),
    "arduino_e_sensores": (5.0, 0.5, 26.0, 12.0, 6.0, 3.0),
}


# ===========================================================================
# DXF (R12 ASCII) — linhas + textos, aberto em qualquer CAD/viewer
# ===========================================================================
def _dxf_line(f, x1, y1, x2, y2) -> None:
    f.write(f"0\nLINE\n8\n0\n10\n{x1}\n20\n{y1}\n11\n{x2}\n21\n{y2}\n")


def _dxf_rect(f, x, y, w, h) -> None:
    _dxf_line(f, x, y, x + w, y)
    _dxf_line(f, x + w, y, x + w, y + h)
    _dxf_line(f, x + w, y + h, x, y + h)
    _dxf_line(f, x, y + h, x, y)


def _dxf_text(f, x, y, h, txt) -> None:
    f.write(f"0\nTEXT\n8\n0\n10\n{x}\n20\n{y}\n40\n{h}\n1\n{txt}\n")


def gerar_dxf() -> Path:
    path = OUT / "tupan_carcaca.dxf"
    with path.open("w", encoding="ascii") as f:
        f.write("0\nSECTION\n2\nENTITIES\n")
        _dxf_rect(f, 0, 0, CARCACA[0], CARCACA[2])  # vista frontal (x × z)
        for nome, (x, _y, z, w, _d, h) in PECAS.items():
            _dxf_rect(f, x, z, w, h)
            _dxf_text(f, x + 0.3, z + 0.3, 0.9, nome.replace("_", " "))
        _dxf_text(f, 0.5, CARCACA[2] + 1.5, 1.2, "TUPAN - vista frontal (cm)")
        _dxf_line(f, 0, -1.5, CARCACA[0], -1.5)  # cota inferior
        f.write("0\nENDSEC\n0\nEOF\n")
    return path


# ===========================================================================
# STL ASCII — blocos fechados (12 triângulos cada) unidos em uma malha
# ===========================================================================
def _box_triangles(x, y, z, sx, sy, sz):
    """Devolve os 12 triângulos (cada um = 3 vértices) de uma caixa."""
    x2, y2, z2 = x + sx, y + sy, z + sz
    v = [
        (x, y, z), (x2, y, z), (x2, y2, z), (x, y2, z),      # base (z)
        (x, y, z2), (x2, y, z2), (x2, y2, z2), (x, y2, z2),  # topo (z2)
    ]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7),      # z- / z+
             (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),      # y- / y+
             (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]      # x- / x+
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def _normal(p, q, r):
    ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / n, ny / n, nz / n


def gerar_stl() -> Path:
    path = OUT / "tupan_pecas.stl"
    with path.open("w", encoding="ascii") as f:
        f.write("solid tupan\n")
        for x, y, z, sx, sy, sz in PECAS.values():
            for p, q, r in _box_triangles(x, y, z, sx, sy, sz):
                nx, ny, nz = _normal(p, q, r)
                f.write(f"facet normal {nx:.4f} {ny:.4f} {nz:.4f}\n outer loop\n")
                for vx, vy, vz in (p, q, r):
                    f.write(f"  vertex {vx:.2f} {vy:.2f} {vz:.2f}\n")
                f.write(" endloop\nendfacet\n")
        f.write("endsolid tupan\n")
    return path


# ===========================================================================
# OpenSCAD — modelo paramétrico (edite os parâmetros e recompile)
# ===========================================================================
def gerar_scad() -> Path:
    path = OUT / "tupan.scad"
    linhas = [
        "// Tupan, Máquina de Chuva — carcaça paramétrica (OpenSCAD)",
        "// Rode: openscad -o tupan.stl tupan.scad",
        "wall = 0.4;  // espessura da parede (cm)",
        f"W = {CARCACA[0]}; D = {CARCACA[1]}; H = {CARCACA[2]};",
        "",
        "module carcaca() {",
        "    difference() {",
        "        cube([W, D, H]);",
        "        translate([wall, wall, wall]) cube([W-2*wall, D-2*wall, H]);",
        "    }",
        "}",
        "",
        "module pecas() {",
    ]
    for nome, (x, y, z, sx, sy, sz) in PECAS.items():
        linhas.append(f"    // {nome}")
        linhas.append(f"    translate([{x}, {y}, {z}]) cube([{sx}, {sy}, {sz}]);")
    linhas += ["}", "", "carcaca();", "pecas();", ""]
    path.write_text("\n".join(linhas), encoding="utf-8")
    return path


# ===========================================================================
# PRANCHA PNG — três vistas ortográficas (frontal, superior, lateral)
# ===========================================================================
def gerar_prancha_png() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    vistas = [
        ("Frontal (x × z)", 0, 2, axes[0]),   # x horizontal, z vertical
        ("Superior (x × y)", 0, 1, axes[1]),  # x horizontal, y vertical
        ("Lateral (y × z)", 1, 2, axes[2]),   # y horizontal, z vertical
    ]
    for titulo, hi, vi, ax in vistas:
        ax.set_title(titulo, color="#1E3A5F", fontweight="bold")
        ax.set_aspect("equal")
        # carcaça
        dims = [CARCACA[hi], CARCACA[vi]]
        ax.add_patch(Rectangle((0, 0), dims[0], dims[1], fill=False,
                               edgecolor="#1E3A5F", lw=2.2))
        for nome, (x, y, z, sx, sy, sz) in PECAS.items():
            c = [x, y, z]
            s = [sx, sy, sz]
            ax.add_patch(Rectangle((c[hi], c[vi]), s[hi], s[vi],
                                   facecolor="#3FB6FF", alpha=0.35,
                                   edgecolor="#1565C0", lw=1.0))
            if s[hi] > 4:
                ax.text(c[hi] + s[hi] / 2, c[vi] + s[vi] / 2,
                        nome.replace("_", " "), ha="center", va="center",
                        fontsize=7, color="#1E3A5F")
        ax.set_xlim(-1, dims[0] + 1)
        ax.set_ylim(-1, dims[1] + 1)
        ax.grid(True, color="#e3e9f0", lw=0.6)
    fig.suptitle("Tupan — prancha técnica (cotas em cm; carcaça 34 × 24 × 32)",
                 fontsize=13, color="#1E3A5F", fontweight="bold")
    path = OUT / "tupan_cad.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    for fn in (gerar_dxf, gerar_stl, gerar_scad, gerar_prancha_png):
        print("[ok]", fn())
    print(f"\nCAD/3D em: {OUT}")


if __name__ == "__main__":
    main()
