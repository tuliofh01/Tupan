#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Servidor Web do Simulador (Flask, microsserviço WEB)
==============================================================================
Consome o NÚCLEO NATIVO C++ (tupan_native, pybind11) e expõe REST+UI em PT-BR.
Fallback autônomo em Python puro se o módulo compilado não estiver no PATH.

Uso:  python3 simulador_tupan.py   → http://127.0.0.1:5000
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Final

from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# NÚCLEO NATIVO (pybind) com fallback puro-Python — mesmas fórmulas do core.
# ---------------------------------------------------------------------------
DIST: Final[Path] = Path(__file__).resolve().parent / "dist" / "bin"
if str(DIST) not in sys.path:
    sys.path.insert(0, str(DIST))

try:
    import tupan_native as tn
    _NATIVO: Final[bool] = True
except ImportError:
    _NATIVO = False
    import math

    def sorption_intake(hours, humidity, temperature, fan_flow, efficiency) -> float:
        es = 6.1094 * math.exp(17.625 * temperature / (243.04 + temperature))
        rho_sat = 216.7 * es / (temperature + 273.15)
        captura = max(0.0, (humidity / 100.0) * rho_sat - 0.60 * _rho_sat(20.0)) \
            * max(0.0, fan_flow * hours) * min(1.0, max(0.0, efficiency)) / 1000.0
        M, q, k = 2.0, 1.0, 0.55
        return float(min(captura, M * q * (1.0 - math.exp(-k * hours))))

    def _rho_sat(temp_c: float) -> float:
        es = 6.1094 * math.exp(17.625 * temp_c / (243.04 + temp_c))
        return 216.7 * es / (temp_c + 273.15)

    def distillation_output(hours, water_kg, heater_temp_c) -> float:
        if hours <= 0 or water_kg <= 0:
            return 0.0
        release = min(1.0, max(0.0, (heater_temp_c - 80.0) / 40.0))
        released = water_kg * release
        energy_kj = 250.0 * hours * 3.6 * 0.90
        needed = released * (4.186 * 75.0 + 2257.0)
        fator = min(1.0, energy_kj / needed) if needed > 0 else 0.0
        return released * fator * 0.92

    def full_cycle(nh, dh, rh, t, ff, ef, ht):
        w = sorption_intake(nh, rh, t, ff, ef)
        l = distillation_output(dh, w, ht)
        energy = (7.5 * nh + 250.0 * dh) * 3600.0
        return type("CB", (), {"water_kg_sorbed": w, "distilled_l": l,
                               "liters_per_kwh": l / (energy / 3.6e6) if energy else 0.0})

if _NATIVO:
    sorption_intake = tn.sorption_intake
    distillation_output = tn.distillation_output
    full_cycle = tn.full_cycle

# ===========================================================================
# MODELO DE FROTA (compatível com o núcleo: mesmas chaves, ruído determinístico)
# ===========================================================================
import random
import time


class TupanModel:
    """Dispositivo estocástico — envolve o núcleo com ruído multiplicative ±5 %."""

    def __init__(self, env: dict[str, float] | None = None) -> None:
        self.env: dict[str, float] = env or {
            "relative_humidity": 65.0, "temperature": 24.0, "pressure": 1013.0,
            "fan_flow": 25.0, "efficiency": 0.85, "heater_temp_c": 120.0,
        }

    def calculate(self, night_hours: float, day_hours: float, seed: int | None = None) -> float:
        if seed is not None:
            random.seed(seed)
        cb = full_cycle(night_hours, day_hours,
                        self.env["relative_humidity"], self.env["temperature"],
                        self.env["fan_flow"], self.env["efficiency"],
                        self.env["heater_temp_c"])
        noise = random.uniform(-0.05, 0.05)
        return max(0.0, cb.distilled_l * (1.0 + noise))


class Simulador:
    """Frota de Tupans + histórico + contas ambientais (L/kWh auditável)."""

    def __init__(self) -> None:
        self.frota: list[dict[str, Any]] = []
        self.ambiente: dict[str, float] = TupanModel().env.copy()
        self.historico: list[dict[str, Any]] = []

    def adicionar(self) -> int:
        id_ = (self.frota[-1]["id"] + 1) if self.frota else 1
        self.frota.append({"id": id_, "modelo": TupanModel(self.ambiente.copy()),
                           "litros": 0.0, "status": "online"})
        return id_

    def remover(self, id_: int) -> None:
        self.frota = [t for t in self.frota if t["id"] != id_]

    def ciclo(self, night_hours: float, day_hours: float, seed: int | None = None) -> list[dict[str, Any]]:
        resultados = []
        for t in self.frota:
            t["modelo"].env.update(self.ambiente)
            litros = t["modelo"].calculate(night_hours, day_hours, seed)
            t["litros"] = round(litros, 4)
            t["status"] = "produzindo" if litros > 0 else "ocioso"
            resultados.append({"id": t["id"], "litros": t["litros"], "status": t["status"]})
        cb = full_cycle(night_hours, day_hours, self.ambiente["relative_humidity"],
                        self.ambiente["temperature"], self.ambiente["fan_flow"],
                        self.ambiente["efficiency"], self.ambiente["heater_temp_c"])
        self.historico.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "noite_h": night_hours, "dia_h": day_hours,
            "kg_sorvidos": round(cb.water_kg_sorbed, 4),
            "litros": round(cb.distilled_l, 4),
            "l_por_kwh": round(cb.liters_per_kwh, 3),
        })
        return resultados

    def contas(self) -> dict[str, float]:
        cb = full_cycle(8.0, 6.0, self.ambiente["relative_humidity"],
                        self.ambiente["temperature"], self.ambiente["fan_flow"],
                        self.ambiente["efficiency"], self.ambiente["heater_temp_c"])
        return {"kg_sorvidos": round(cb.water_kg_sorbed, 4),
                "litros": round(cb.distilled_l, 4),
                "l_por_kwh": round(cb.liters_per_kwh, 3)}


sim = Simulador()
app = Flask(__name__)


# ===========================================================================
# ROTAS REST — contratos JSON (microsserviço WEB ⇄ UI ⇄ núcleo nativo)
# ===========================================================================
@app.get("/")
def index() -> str:
    return render_template("simulacao.html", sim=sim, nativo=_NATIVO)


@app.get("/api/ambiente")
def api_ambiente() -> Any:
    return jsonify(sim.ambiente)


@app.post("/api/ambiente")
def api_set_ambiente() -> Any:
    dados = request.get_json(silent=True) or {}
    for k, v in dados.items():
        if k in sim.ambiente:
            sim.ambiente[k] = float(v)
    return jsonify({"status": "ok", "ambiente": sim.ambiente})


@app.get("/api/frota")
def api_frota() -> Any:
    return jsonify({"frota": [{"id": t["id"], "litros": t["litros"], "status": t["status"]}
                              for t in sim.frota]})


@app.post("/api/frota/adicionar")
def api_adicionar() -> Any:
    return jsonify({"status": "ok", "id": sim.adicionar()}), 201


@app.post("/api/frota/remover/<int:id_>")
def api_remover(id_: int) -> Any:
    sim.remover(id_)
    return jsonify({"status": "ok"})


@app.post("/api/ciclo")
def api_ciclo() -> Any:
    d = request.get_json(silent=True) or {}
    # Aplica ambiente recebido (UI manda tudo junto) antes do ciclo.
    for k in ("relative_humidity", "temperature", "fan_flow", "heater_temp_c"):
        if k in d:
            sim.ambiente[k] = float(d[k])
    return jsonify({"status": "ok",
                    "resultados": sim.ciclo(float(d.get("noite_h", 8.0)),
                                            float(d.get("dia_h", 6.0))),
                    "contas": sim.contas()})


@app.get("/api/historico")
def api_historico() -> Any:
    return jsonify(sim.historico[-100:])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
