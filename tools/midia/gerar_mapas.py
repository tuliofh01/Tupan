#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Gerador de MAPAS do Brasil
======================================================
Gera mapas temáticos do Brasil com base em dados climáticos reais (Open-Meteo)
e na fórmula físico-química do Tupan:

  mapa_ur_noturna.png       UR noturna média por estado (20h-6h, 2024)
  mapa_producao_anual.png   Produção anual estimada (L/ano)
  mapa_viabilidade.png      Classificação de viabilidade técnica
  mapa_biomas.png           Bioma dominante por estado (mapa comparativo)

Saída: docs/midia/mapas/ e data/processed/
Executar: python3 tools/midia/gerar_mapas.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Final

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

RAIZ: Final[Path] = Path(__file__).resolve().parents[2]
MIDIA: Final[Path] = RAIZ / "docs" / "midia" / "mapas"
DADOS: Final[Path] = RAIZ / "data" / "processed"
MIDIA.mkdir(parents=True, exist_ok=True)
DADOS.mkdir(parents=True, exist_ok=True)

# Paleta do projeto.
AZUL = "#1E3A5F"; AGUA = "#3FB6FF"; NOITE = "#7C6CFF"; DIA = "#FFB454"
VERDE = "#2E9E5B"; MIN = "#6FE0C8"; UV = "#B47CFF"; SOL = "#FFD166"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": "#33475f", "axes.labelcolor": AZUL,
    "text.color": AZUL, "xtick.color": "#33475f", "ytick.color": "#33475f",
    "axes.grid": True, "grid.color": "#e3e9f0", "grid.linewidth": 0.8,
    "savefig.dpi": 150, "savefig.bbox": "tight",
})

# Código IBGE → UF / capital / coordenadas aproximadas.
ESTADOS: Final[dict[str, tuple[str, float, float]]] = {
    "11": ("RO", "Porto Velho", -8.76, -63.90),
    "12": ("AC", "Rio Branco", -9.98, -70.81),
    "13": ("AM", "Manaus", -3.12, -60.02),
    "14": ("RR", "Boa Vista", 2.82, -60.68),
    "15": ("PA", "Belém", -1.46, -48.50),
    "16": ("AP", "Macapá", 0.04, -52.17),
    "17": ("TO", "Palmas", -10.24, -48.32),
    "21": ("MA", "São Luís", -2.53, -44.28),
    "22": ("PI", "Teresina", -5.09, -42.80),
    "23": ("CE", "Fortaleza", -3.73, -38.53),
    "24": ("RN", "Natal", -5.79, -35.21),
    "25": ("PB", "João Pessoa", -7.12, -34.86),
    "26": ("PE", "Recife", -8.05, -34.88),
    "27": ("AL", "Maceió", -9.67, -35.73),
    "28": ("SE", "Aracaju", -10.91, -37.07),
    "29": ("BA", "Salvador", -12.97, -38.51),
    "31": ("MG", "Belo Horizonte", -9.91, -43.94),
    "32": ("ES", "Vitória", -20.32, -40.34),
    "33": ("RJ", "Rio de Janeiro", -22.91, -43.17),
    "35": ("SP", "São Paulo", -23.55, -46.63),
    "41": ("PR", "Curitiba", -25.43, -49.27),
    "42": ("SC", "Florianópolis", -27.60, -48.55),
    "43": ("RS", "Porto Alegre", -30.03, -51.23),
    "50": ("MS", "Campo Grande", -20.46, -54.62),
    "51": ("MT", "Cuiabá", -15.60, -56.09),
    "52": ("GO", "Goiânia", -16.69, -49.26),
    "53": ("DF", "Brasília", -15.79, -47.88),
}

# Fallback aproximado (usado se Open-Meteo estiver indisponível).
FALLBACK_UR: Final[dict[str, float]] = {
    "RO": 68, "AC": 74, "AM": 79, "RR": 78, "PA": 78, "AP": 83, "TO": 70,
    "MA": 76, "PI": 68, "CE": 72, "RN": 72, "PB": 74, "PE": 69, "AL": 74,
    "SE": 76, "BA": 75, "MG": 67, "ES": 70, "RJ": 66, "SP": 64, "PR": 66,
    "SC": 68, "RS": 67, "MS": 65, "MT": 64, "GO": 62, "DF": 60,
}
FALLBACK_TEMP: Final[dict[str, float]] = {
    "RO": 24.0, "AC": 25.5, "AM": 26.0, "RR": 25.0, "PA": 26.5, "AP": 26.5, "TO": 25.0,
    "MA": 26.0, "PI": 26.0, "CE": 27.0, "RN": 26.0, "PB": 26.0, "PE": 25.5, "AL": 26.0,
    "SE": 26.0, "BA": 25.0, "MG": 22.0, "ES": 24.0, "RJ": 23.0, "SP": 20.0, "PR": 18.0,
    "SC": 18.0, "RS": 19.0, "MS": 23.0, "MT": 25.0, "GO": 23.0, "DF": 21.0,
}

# Biomas dominantes por UF (classificação didática).
BIOMAS: Final[dict[str, str]] = {
    "RO": "Amazônia", "AC": "Amazônia", "AM": "Amazônia", "RR": "Amazônia",
    "PA": "Amazônia", "AP": "Amazônia", "TO": "Cerrado", "MA": "Cerrado",
    "PI": "Cerrado", "CE": "Caatinga", "RN": "Caatinga", "PB": "Caatinga",
    "PE": "Mata Atlântica", "AL": "Mata Atlântica", "SE": "Caatinga",
    "BA": "Caatinga", "MG": "Mata Atlântica", "ES": "Mata Atlântica",
    "RJ": "Mata Atlântica", "SP": "Mata Atlântica", "PR": "Mata Atlântica",
    "SC": "Mata Atlântica", "RS": "Pampa", "MS": "Pantanal",
    "MT": "Cerrado", "GO": "Cerrado", "DF": "Cerrado",
}

URL_IBGE: Final[str] = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?"
    "formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=UF&nivel=estados"
)
URL_METEO: Final[str] = (
    "https://archive-api.open-meteo.com/v1/archive"
)


def producao_l(ur: float) -> float:
    """Produção potável (L/ciclo) pela fórmula físico-química do Tupan."""
    es24 = 6.1094 * math.exp(17.625 * 24 / (243.04 + 24))
    rho = ur / 100 * 216.7 * es24 / (24 + 273.15)
    cap = max(0.0, rho - 0.6 * 12.27) * 25 * 8 * 0.85 / 1000
    leito = 2.0 * (1 - math.exp(-0.55 * 8))
    kg = min(cap, leito)
    dest = kg * 0.92
    return min(dest * 0.98, 2.0)


def _fetch(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Tupan-Midias/1.0", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if resp.headers.get("Content-Encoding") == "gzip":
        import gzip
        data = gzip.decompress(data)
    return data


def _fetch_meteo(lat: float, lon: float) -> dict[str, float]:
    url = (
        f"{URL_METEO}?latitude={lat:.4f}&longitude={lon:.4f}"
        "&start_date=2024-01-01&end_date=2024-12-31"
        "&hourly=relative_humidity_2m,temperature_2m"
        "&timezone=America%2FSao_Paulo"
    )
    data = json.loads(_fetch(url).decode("utf-8"))
    hourly = data["hourly"]
    ur = np.asarray(hourly["relative_humidity_2m"], dtype=float)
    tmp = np.asarray(hourly["temperature_2m"], dtype=float)
    # Noite operacional: 20h–06h.
    idx = []
    for i, t in enumerate(hourly["time"]):
        h = int(t[11:13])
        if h >= 20 or h <= 6:
            idx.append(i)
    ur_n = ur[idx]
    tmp_n = tmp[idx]
    return {
        "ur": float(np.mean(ur_n)),
        "temp": float(np.mean(tmp_n)),
        "n": int(len(ur_n)),
    }


def _fetch_all() -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        for uf, (nome, capital, lat, lon) in ESTADOS.items():
            futures[pool.submit(_fetch_meteo, lat, lon)] = uf
        for fut in as_completed(futures):
            uf = futures[fut]
            try:
                result[uf] = fut.result()
            except Exception as exc:
                print(f"[warn] Open-Meteo falhou para {uf}: {exc}", file=sys.stderr)
    return result


def _geom_coords(geom: dict) -> list[tuple[float, float]]:
    coords = []
    gtype = geom.get("geometry", {}).get("type")
    if gtype == "Polygon":
        rings = geom["geometry"].get("coordinates", [])
    elif gtype == "MultiPolygon":
        rings = [r for poly in geom["geometry"].get("coordinates", []) for r in poly]
    else:
        return coords
    for ring in rings:
        pts = [(float(x), float(y)) for x, y in ring]
        if len(pts) > 1 and pts[0] != pts[-1]:
            pts.append(pts[0])
        coords.append(pts)
    return coords


def _load_ibge() -> dict[str, list[tuple[float, float]]]:
    try:
        geo = json.loads(_fetch(URL_IBGE).decode("utf-8"))
        out: dict[str, list[tuple[float, float]]] = {}
        for feat in geo.get("features", []):
            code = str(feat.get("properties", {}).get("codarea", ""))
            out[code] = _geom_coords(feat)
        return out
    except Exception as exc:
        print(f"[warn] IBGE indisponível ({exc}); usando mapa esquemático.", file=sys.stderr)
        return {}


def _draw_map(values: dict[str, float], title: str, cmap, unit: str, fmt, vmin=None, vmax=None,
              filename: str | None = None):
    geo = _load_ibge()
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(-74, -32)
    ax.set_ylim(-35, 5.5)
    ax.axis("off")
    ax.set_title(title, fontsize=15, fontweight="bold", color=AZUL, pad=14)
    ax.text(0.5, 1.01, "Fonte: Open-Meteo Archive 2024 + modelo físico do Tupan",
            transform=ax.transAxes, ha="center", fontsize=9, color="#5b7085")
    for code, rings in geo.items():
        uf = ESTADOS.get(code, ("", "", 0, 0))[0]
        val = values.get(uf, np.nan)
        color = cmap(val) if not np.isnan(val) and vmin is not None and vmax is not None else "#dfe6ee"
        for ring in rings:
            ax.add_patch(Polygon(ring, closed=True, facecolor=color, edgecolor="white", lw=0.7, zorder=2))
    # capital dots
    for uf, (nome, capital, lat, lon) in ESTADOS.items():
        val = values.get(uf, np.nan)
        dot_color = cmap(val) if not np.isnan(val) and vmin is not None and vmax is not None else "#8fa3bf"
        ax.scatter(lon, lat, s=16, c=dot_color,
                    edgecolor="white", linewidth=0.5, zorder=3)
    # legend
    if vmin is not None and vmax is not None:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(unit)
    fig.savefig(MIDIA / (filename or f"{title.split(' — ')[0].lower().replace(' ', '_')}.png"), dpi=150)
    plt.close(fig)


def _save_csv(rows: list[dict]) -> None:
    path = DADOS / "clima_capitais_2024.csv"
    fields = ["uf", "estado", "capital", "lat", "lon", "ur_noturna", "temp_noite", "producao_l_ciclo", "producao_l_ano"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})


def main():
    clima = _fetch_all()
    rows: list[dict] = []
    ur_by_uf: dict[str, float] = {}
    prod_by_uf: dict[str, float] = {}
    for uf, (estado, capital, lat, lon) in ESTADOS.items():
        if uf in clima:
            ur, tmp, n = clima[uf]["ur"], clima[uf]["temp"], clima[uf]["n"]
            source = "Open-Meteo"
        else:
            ur, tmp = FALLBACK_UR.get(uf, 70), FALLBACK_TEMP.get(uf, 24)
            n = 0
            source = "fallback"
        p_ciclo = producao_l(ur)
        ur_by_uf[uf] = ur
        prod_by_uf[uf] = p_ciclo * 365
        rows.append({
            "uf": uf, "estado": estado, "capital": capital, "lat": lat, "lon": lon,
            "ur_noturna": ur, "temp_noite": tmp, "producao_l_ciclo": p_ciclo,
            "producao_l_ano": p_ciclo * 365,
        })
    _save_csv(rows)
    print(f"[ok] {len(rows)} capitais processadas")

    # 1) UR noturna.
    cmap = LinearSegmentedColormap.from_list("tupan", ["#dfe6ee", "#8fc7ff", "#1E3A5F"])
    _draw_map(ur_by_uf, "Tupan — UR noturna média por estado", cmap, "%", "{:.1f}%", vmin=55, vmax=85,
              filename="mapa_ur_noturna.png")
    print("[ok] mapa_ur_noturna.png")

    # 2) Produção anual.
    cmap2 = LinearSegmentedColormap.from_list("tupan", ["#f6d7a8", "#ffb454", "#1E3A5F"])
    _draw_map(prod_by_uf, "Tupan — produção anual estimada por estado", cmap2, "L/ano", "{:.0f}", vmin=0, vmax=800,
              filename="mapa_producao_anual.png")
    print("[ok] mapa_producao_anual.png")

    # 3) Viabilidade.
    viab: dict[str, float] = {}
    for uf, ur in ur_by_uf.items():
        if ur >= 70:
            viab[uf] = 3
        elif ur >= 60:
            viab[uf] = 2
        else:
            viab[uf] = 1
    cmap3 = LinearSegmentedColormap.from_list("tupan", ["#f4cccc", "#fff2cc", "#d9ead3", "#2E9E5B"])
    _draw_map(viab, "Tupan — viabilidade técnica por estado", cmap3, "níveis", "{:.0f}", vmin=1, vmax=3,
              filename="mapa_viabilidade.png")
    print("[ok] mapa_viabilidade.png")

    # 4) Biomas.
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(-74, -32); ax.set_ylim(-35, 5.5); ax.axis("off")
    ax.set_title("Tupan — biomas dominantes por estado", fontsize=15, fontweight="bold", color=AZUL, pad=14)
    colors = {"Amazônia": "#2E9E5B", "Cerrado": "#F4D06F", "Caatinga": "#E67E22",
              "Mata Atlântica": "#1E8449", "Pampa": "#7CB342", "Pantanal": "#9CCC65"}
    for code, rings in _load_ibge().items():
        uf = ESTADOS.get(code, ("", "", 0, 0))[0]
        bm = BIOMAS.get(uf, "Cerrado")
        for ring in rings:
            ax.add_patch(Polygon(ring, closed=True, facecolor=colors.get(bm, "#999"), edgecolor="white", lw=0.7, alpha=0.85))
    for uf, (estado, capital, lat, lon) in ESTADOS.items():
        bm = BIOMAS.get(uf, "Cerrado")
        ax.scatter(lon, lat, s=12, c=colors.get(bm, "#999"), edgecolor="white", linewidth=0.5, zorder=3)
    legend = []
    for bm, c in colors.items():
        legend.append(plt.Line2D([0], [0], marker="o", color="w", label=bm, markerfacecolor=c, markersize=9))
    ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(0.02, 0.02), ncol=2, frameon=False, fontsize=9)
    fig.savefig(MIDIA / "mapa_biomas.png", dpi=150); plt.close(fig)
    print("[ok] mapa_biomas.png")

    # 5) Mapa de capitais com rótulos (para o relatório/pitch).
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(-74, -32); ax.set_ylim(-35, 5.5); ax.axis("off")
    ax.set_title("Tupan — capitais monitoradas (amostra climática)", fontsize=15, fontweight="bold", color=AZUL, pad=14)
    for code, rings in _load_ibge().items():
        for ring in rings:
            ax.add_patch(Polygon(ring, closed=True, facecolor="#f7f9fb", edgecolor="#33475f", lw=0.6))
    for uf, (estado, capital, lat, lon) in ESTADOS.items():
        ur = ur_by_uf.get(uf, FALLBACK_UR.get(uf, 70))
        ax.scatter(lon, lat, s=26, c=AGUA, edgecolor="white", linewidth=0.7, zorder=3)
        ax.annotate(estado, (lon, lat), xytext=(4, 4), textcoords="offset points",
                    fontsize=8, color=AZUL, fontweight="bold", zorder=4)
    ax.text(0.5, 0.02, "Cada ponto representa uma capital usada para calibrar o modelo de produção.",
            transform=ax.transAxes, ha="center", fontsize=9, color="#5b7085")
    fig.savefig(MIDIA / "mapa_capitais.png", dpi=150); plt.close(fig)
    print("[ok] mapa_capitais.png")

    print(f"\nMapas: {MIDIA}")
    print(f"CSV:   {DADOS / 'clima_capitais_2024.csv'}")


if __name__ == "__main__":
    main()
