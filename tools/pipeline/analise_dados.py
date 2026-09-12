#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Esteira de Dados & ML (microsserviço de ANALÍTICA)
=============================================================================
Responsabilidades (arquitetura de microsserviços):
  1. INGESTÃO  : baixa clima real (Open-Meteo/ERA5 → CSV em data/raw);
  2. CURADORIA : pandas — limpeza, janela noturna, engenharia de atributos;
  3. MODELAGEM : PyTorch (MLP) vs. polinômio grau 2 (baseline do núcleo C++);
  4. EXPORT    : CSV de projeções + JSON de métricas para o relatório/GUI.

Uso:
  python3 analise_dados.py                    # tudo: ingestão+curadoria+ML+export
  python3 analise_dados.py --skip-download    # usa os CSVs já baixados

DIDÁTICA (pandas/torch): tudo tipado com pandas-stubs e anotações; o pipeline
é determinístico (seeds fixos) e auditável (salva métricas e gráficos).
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

# ---------------------------------------------------------------------------
# CAMINHOS (repo root = ../../ a partir deste arquivo)
# ---------------------------------------------------------------------------
REPO: Final[Path] = Path(__file__).resolve().parents[2]
RAW: Final[Path] = REPO / "data" / "raw"
PROC: Final[Path] = REPO / "data" / "processed"
RESULTS: Final[Path] = REPO / "data" / "results"
GRAF: Final[Path] = REPO / "docs" / "midia" / "graficos"
for _d in (RAW, PROC, RESULTS, GRAF):
    _d.mkdir(parents=True, exist_ok=True)
CSV_CLIMA: Final[Path] = RAW / "clima_semiarido_petrolina.csv"
OUT_CSV: Final[Path] = RESULTS / "projetoes_tupan.csv"
OUT_JSON: Final[Path] = RESULTS / "metricas_ml.json"
OUT_FIG: Final[Path] = GRAF / "grafico_ml_vs_fisica.png"

# ---------------------------------------------------------------------------
# NÚCLEO NATIVO (pybind) com FALLBACK puro-Python (microsserviço tolerante).
# ---------------------------------------------------------------------------
import sys as _sys
DIST: Final[Path] = REPO / "build"
if str(DIST) not in _sys.path:
    _sys.path.insert(0, str(DIST))

try:
    import tupan_native as tn  # pybind (rápido)
    _NATIVO: Final[bool] = True
    sorption_intake = tn.sorption_intake
    distillation_output = tn.distillation_output
except ImportError:
    _NATIVO = False
    import math

    def sorption_intake(hours, humidity, temperature, fan_flow, efficiency) -> float:
        es = 6.1094 * math.exp(17.625 * temperature / (243.04 + temperature))
        rho_sat = 216.7 * es / (temperature + 273.15)
        captured = max(0.0, (humidity / 100.0) * rho_sat - 0.60 * 17.3) * max(0.0, fan_flow * hours) * min(1.0, max(0.0, efficiency)) / 1000.0
        M, q, k = 2.0, 1.0, 0.55
        return float(min(captured, M * q * (1.0 - math.exp(-k * hours))))

    def distillation_output(hours, water_kg, heater_temp_c) -> float:
        if hours <= 0 or water_kg <= 0:
            return 0.0
        release = min(1.0, max(0.0, (heater_temp_c - 80.0) / 40.0))
        released = water_kg * release
        energy_kj = 250.0 * hours * 3.6 * 0.90
        needed = released * (4.186 * 75.0 + 2257.0)
        factor = min(1.0, energy_kj / needed) if needed > 0 else 0.0
        return released * factor * 0.92

    def full_cycle(nh, dh, rh, t, ff, ef, ht):
        w = sorption_intake(nh, rh, t, ff, ef)
        l = distillation_output(dh, w, ht)
        energy = (7.5 * nh + 250.0 * dh) * 3600.0
        return type("CB", (), {"water_kg_sorbed": w, "distilled_l": l,
                               "liters_per_kwh": l / (energy / 3.6e6) if energy else 0.0})

    # -- Fallback Python: mesmas fórmulas do tupan_core.hpp ------------------
    def _rho_sat(temp_c: float) -> float:
        es = 6.1094 * np.exp(17.625 * temp_c / (243.04 + temp_c))
        return 216.7 * es / (temp_c + 273.15)

    def _sorption_intake(hours, humidity, temperature, fan_flow, efficiency) -> float:
        rho_air = (humidity / 100.0) * _rho_sat(temperature)
        rho_out = 0.60 * _rho_sat(20.0)  # saída do leito ~20 °C/60 % (didático)
        captured = max(0.0, rho_air - rho_out) * max(0.0, fan_flow * hours) * min(1.0, max(0.0, efficiency)) / 1000.0
        M, q, k = 2.0, 1.0, 0.55
        kinetic = M * q * (1.0 - np.exp(-k * hours))
        return float(min(captured, kinetic))

    sorption_intake = _sorption_intake

    def _distillation_output(hours, water_kg, heater_temp_c) -> float:
        if hours <= 0 or water_kg <= 0:
            return 0.0
        release = min(1.0, max(0.0, (heater_temp_c - 80.0) / 40.0))
        released = water_kg * release
        energy_kj = 250.0 * hours * 3.6 * 0.90
        needed = released * (4.186 * 75.0 + 2257.0)
        factor = min(1.0, energy_kj / needed) if needed > 0 else 0.0
        return released * factor * 0.92

    distillation_output = _distillation_output

    class _FallbackSim:
        @staticmethod
        def full_cycle(nh, dh, rh, t, ff, ef, ht):
            w = sorption_intake(nh, rh, t, ff, ef)
            l = distillation_output(dh, w, ht)
            energy = (7.5 * nh + 250.0 * dh) * 3600.0
            return type("CB", (), {"water_kg_sorbed": w, "distilled_l": l,
                                   "liters_per_kwh": l / (energy / 3.6e6) if energy else 0.0})

    full_cycle = _FallbackSim.full_cycle

if _NATIVO:
    full_cycle = tn.full_cycle

# ===========================================================================
# 1) INGESTÃO — Open-Meteo Archive (ERA5), Petrolina-PE (semiárido).
# ===========================================================================
def ingestao(force: bool = False) -> pd.DataFrame:
    if CSV_CLIMA.exists() and not force:
        return pd.read_csv(CSV_CLIMA, parse_dates=["time"])
    url: Final[str] = (
        "https://archive-api.open-meteo.com/v1/archive"
        "?latitude=-9.39&longitude=-40.50"
        "&start_date=2024-01-01&end_date=2025-08-31"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation,surface_pressure"
        "&timezone=America%2FBahia&format=csv"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "tupan-academico/1.0"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    lines = raw.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("time,"))
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    df.columns = [re.sub(r"\s*\(.*\)$", "", c.strip("' ")) for c in df.columns]
    df = df.dropna(subset=["temperature_2m"])
    df["time"] = pd.to_datetime(df["time"])
    df.to_csv(CSV_CLIMA, index=False)
    return df


# ===========================================================================
# 2) CURADORIA — janela noturna (sorção) + engenharia de atributos + Δρ.
# ===========================================================================
def curadoria(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hora"] = df["time"].dt.hour
    # Janela de SORÇÃO: 20h–06h (mais úmida e fria — melhor Δρ para o leito).
    df["janela"] = np.where((df["hora"] >= 20) | (df["hora"] < 6), "sorcao", "dia")
    df["rho_sat_g_m3"] = df["temperature_2m"].map(_rho_sat if not _NATIVO else tn.saturation_vapor_density)
    df["vapor_absoluto"] = (df["relative_humidity_2m"] / 100.0) * df["rho_sat_g_m3"]

    # Projeção TUPAN por hora (8 h noite + 6 h dia, padrão do relatório):
    # para cada hora noturna, sorção naquela hora; destilação concentrada ao dia.
    def proj_row(r: pd.Series) -> float:
        if r["janela"] == "sorcao":
            return sorption_intake(1.0, r["relative_humidity_2m"], r["temperature_2m"], 25.0, 0.85)
        return 0.0

    df["kg_sorvidos_h"] = df.apply(proj_row, axis=1)
    df["kg_sorvidos_noite"] = df.groupby(df["time"].dt.date)["kg_sorvidos_h"].transform("sum")

    # Destilação diurna: usa a água da noite anterior (shift para não vazamento).
    mapa_noite = (df.drop_duplicates("time").assign(dia=df["time"].dt.date)
                    .groupby("dia")["kg_sorvidos_noite"].first())
    df["kg_disponivel_dia"] = df["time"].dt.date.map(mapa_noite.shift(1))
    df["litros_potaveis_h"] = df.apply(
        lambda r: distillation_output(1.0, r["kg_disponivel_dia"], 120.0)
        if r["janela"] == "dia" else 0.0, axis=1)
    return df


# ===========================================================================
# 3) MODELAGEM — MLP (PyTorch) vs. grau 2 (baseline nativo C++).
#    Alvo: litros potáveis do ciclo padrão (8 h noite + 6 h dia).
# ===========================================================================
def modelagem() -> dict[str, float]:
    # Envelope = percentis 5–95 do clima real noturno (dados>pressupostos).
    noite = df_clima[df_clima["janela"] == "sorcao"]
    lo = noite[["relative_humidity_2m", "temperature_2m"]].quantile(0.05).to_numpy()
    hi = noite[["relative_humidity_2m", "temperature_2m"]].quantile(0.95).to_numpy()

    rng = np.random.default_rng(42)
    N: Final[int] = 5000
    X = np.column_stack([
        rng.uniform(lo[0], hi[0], N),   # UR %
        rng.uniform(lo[1], hi[1], N),   # T °C
        rng.uniform(10, 40, N),         # vazão m³/h
        rng.uniform(0.5, 1.0, N),       # η leito
        rng.uniform(100, 160, N),       # T aquecedor °C
    ]).astype(np.float32)
    y = np.array([full_cycle(8.0, 6.0, *x).distilled_l for x in X], dtype=np.float32)

    # split 80/20 estratificado pelo zero (para o MLP ver os "kinks").
    idx = rng.permutation(N)
    n_tr = int(0.8 * N)
    Xtr, Xte, ytr, yte = X[idx[:n_tr]], X[idx[n_tr:]], y[idx[:n_tr]], y[idx[n_tr:]]

    # ---- Baseline: polinômio grau 2 (equivalente ao MLPredictor C++) ----
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.linear_model import Ridge
    poly = PolynomialFeatures(2, include_bias=False)
    ridge = Ridge(1e-9).fit(poly.fit_transform(Xtr), ytr)
    r2_poly = float(ridge.score(poly.transform(Xte), yte))
    rmse_poly = float(np.sqrt(np.mean((ridge.predict(poly.transform(Xte)) - yte) ** 2)))

    # ---- MLP PyTorch (2 camadas ocultas 64/64, ReLU, AdamW) ----
    torch.manual_seed(42)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net: nn.Module = nn.Sequential(
        nn.Linear(5, 64), nn.ReLU(),
        nn.Linear(64, 64), nn.ReLU(),
        nn.Linear(64, 1),
    ).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=3e-3, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=300)
    xt = torch.tensor(Xtr, device=dev); yt = torch.tensor(ytr.reshape(-1, 1), device=dev)
    xe = torch.tensor(Xte, device=dev); ye = torch.tensor(yte.reshape(-1, 1), device=dev)
    ds = torch.utils.data.TensorDataset(xt, yt)
    dl = torch.utils.data.DataLoader(ds, batch_size=256, shuffle=True)
    for epoch in range(300):
        net.train()
        for xb, yb in dl:
            opt.zero_grad()
            loss = nn.functional.mse_loss(net(xb), yb)
            loss.backward()
            opt.step()
        sched.step()

    net.eval()
    with torch.no_grad():
        pred = net(xe).cpu().numpy().ravel()
    r2_mlp = float(1 - np.sum((yte - pred) ** 2) / np.sum((yte - yte.mean()) ** 2))
    rmse_mlp = float(np.sqrt(np.mean((yte - pred) ** 2)))

    # ---- Gráfico físico vs. modelos ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(yte, ridge.predict(poly.transform(Xte)), s=8, alpha=0.5,
                   label=f"Grau 2 (R²={r2_poly:.3f})")
        ax.scatter(yte, pred, s=8, alpha=0.5, label=f"MLP 64/64 (R²={r2_mlp:.3f})")
        lim = [0, max(yte.max(), pred.max()) * 1.05]
        ax.plot(lim, lim, "k--", lw=1, label="y = x (perfeito)")
        ax.set_xlabel("Física do núcleo (L/ciclo)")
        ax.set_ylabel("Predição do modelo")
        ax.set_title("Modelos vs. física nativa — ciclo sorção/destilação")
        ax.grid(alpha=0.3); ax.legend()
        fig.tight_layout()
        fig.savefig(OUT_FIG, dpi=150)
        plt.close(fig)
    except Exception as exc:  # gráfico é não-crítico
        print(f"aviso: gráfico falhou ({exc})")

    return {
        "r2_grau2": r2_poly, "rmse_grau2": rmse_poly,
        "r2_mlp": r2_mlp, "rmse_mlp": rmse_mlp,
        "n_treino": n_tr, "n_teste": N - n_tr,
        "envelope_UR": [float(lo[0]), float(hi[0])],
        "envelope_T": [float(lo[1]), float(hi[1])],
        "device": "cuda" if torch.cuda.is_available() else "cpu",
    }


# ===========================================================================
# 4) PROJEÇÃO ANUAL — pandas aplicando o núcleo hora a hora (auditável).
# ===========================================================================
def projecao_anual(df: pd.DataFrame) -> pd.DataFrame:
    # DIDÁTICA pandas: agregação nomeada + filtro de janela noturna ANTES do agg
    # (o índice do grupo é um RangeIndex — .hour deve vir da própria Series).
    noite = df[(df["hora"] >= 20) | (df["hora"] < 6)]
    diario = (noite.groupby(noite["time"].dt.date)
                .agg(ur_noite=("relative_humidity_2m", "mean"),
                     t_noite=("temperature_2m", "mean"))
                .dropna())
    diario["kg_sorvidos"] = [sorption_intake(10.0, ur, t, 25.0, 0.85)
                             for ur, t in zip(diario["ur_noite"], diario["t_noite"])]
    diario["litros"] = [distillation_output(6.0, kg, 120.0) for kg in diario["kg_sorvidos"]]
    diario = diario.reset_index().rename(columns={"time": "data"})
    diario["data"] = pd.to_datetime(diario["data"])
    diario.to_csv(OUT_CSV, index=False)
    return diario


# ===========================================================================
# MAIN — orquestração (ingestão → curadoria → ML → projeção → export)
# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="Esteira de dados & ML do Tupan")
    ap.add_argument("--skip-download", action="store_true", help="usa os CSVs locais")
    args = ap.parse_args()

    global df_clima
    df_clima = ingestao(force=not args.skip_download)
    df_clima = curadoria(df_clima)

    diario = projecao_anual(df_clima)
    metricas = modelagem()

    resumo = {
        "n_horas": int(len(df_clima)),
        "periodo": [str(df_clima["time"].min().date()), str(df_clima["time"].max().date())],
        "noite_UR_media": float(noite := df_clima[df_clima["janela"] == "sorcao"]["relative_humidity_2m"].mean()),
        "noite_T_media": float(df_clima[df_clima["janela"] == "sorcao"]["temperature_2m"].mean()),
        "litros_ano_estimados": float(diario["litros"].sum()),
        "litros_dia_medio": float(diario["litros"].mean()),
        **metricas,
    }
    OUT_JSON.write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
