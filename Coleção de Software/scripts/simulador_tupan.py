#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan Simulation Dashboard - Simulador com UI Dinâmica Web
Simula um ambiente com múltiplos Tupans e verifica o output de água de cada um.
Abordagem: Data Science + Machine Learning (previsão de produção de água).
"""

import os
import sys
import json
import math
import random
import threading
import time

try:
    from flask import Flask, render_template, request, jsonify
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
except ImportError:
    print("ERRO: Instale as dependências: pip install flask numpy scikit-learn")
    sys.exit(1)

# ============================================================
# DIRETÓRIOS
# ============================================================
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MEDIA_DIR = os.path.join(BASE, "Documentação Oficial", "Arquivo de Mídia")
os.makedirs(MEDIA_DIR, exist_ok=True)

# ============================================================
# MODELO FÍSICO-ESTOCÁSTICO DO TUPAN
# ============================================================
class TupanModel:
    """
    Modelo físico-estocástico para simular a produção de água de um Tupan.
    Fatores que influenciam a produção:
    - Umidade relativa do ar (%)
    - Temperatura (°C)
    - Pressão atmosférica (hPa)
    - Vazão do ventilador (L/min)
    - Eficiência do sistema (%)
    - Temperatura da serpentina (°C)
    """

    def __init__(self, params=None):
        self.params = {
            "relative_humidity": 60.0,   # %
            "temperature": 28.0,         # °C
            "pressure": 1013.0,          # hPa
            "fan_flow": 25.0,            # L/min
            "efficiency": 0.85,          # %
            "coil_temperature": 8.0,     # °C
            "noise": 0.05,               # ruído estocástico
        }
        if params:
            self.params.update(params)

    def calculate_output(self, hours=1.0, seed=None):
        """
        Calcula o volume de água produzido em litros.

        Fórmula simplificada baseada na capacidade de retenção de vapor:
        - Ar a 30°C e 100% UR retém ~27 g/m³ de vapor
        - Ar a 10°C retém ~9 g/m³
        - Diferença = 18 g/m³ condensável
        """
        p = self.params
        if seed is not None:
            random.seed(seed)

        # Capacidade de saturação de vapor (g/m³) via fórmula de Magnus
        def saturation_vapor_density(temp_c):
            a, b, c = 17.27, 237.7, 237.3
            gamma = (a * temp_c) / (b + temp_c) + c
            return 216.7 * math.exp(gamma) / (237.3 + temp_c)

        vapor_in = saturation_vapor_density(p["temperature"])
        vapor_out = saturation_vapor_density(p["coil_temperature"])
        condensable = max(0.0, vapor_in - vapor_out)  # g/m³

        # Volume de ar processado
        air_volume = p["fan_flow"] * hours * 60.0  # litros
        air_volume_m3 = air_volume / 1000.0

        # Massa de água condensável
        water_g = condensable * air_volume_m3 * p["efficiency"]

        # Ruído estocástico (simula turbulência, sujeira, variações)
        noise = random.uniform(-p["noise"], p["noise"])
        output_liters = (water_g / 1000.0) * (1 + noise)

        return round(max(0.0, output_liters), 4)


# ============================================================
# MODELO DE MACHINE LEARNING
# ============================================================
class WaterProductionML:
    """
    Modelo de Machine Learning para prever produção de água.
    Usa regressão polinomial para capturar não-linearidades.
    """

    def __init__(self):
        self.model = None
        self.poly = PolynomialFeatures(degree=2, include_bias=False)
        self.regressor = LinearRegression()

    def train(self, features, targets):
        X = self.poly.fit_transform(features)
        self.regressor.fit(X, targets)
        self.model = True

    def predict(self, features):
        if not self.model:
            return None
        X = self.poly.transform(features)
        return float(self.regressor.predict(X)[0])


# ============================================================
# SIMULADOR DE AMBIENTE
# ============================================================
class EnvironmentSimulator:
    """
    Simula um ambiente com parâmetros modificáveis.
    Permite inserir/remover Tupans e verificar o output de água.
    """

    def __init__(self):
        self.tupans = []
        self.environment = {
            "relative_humidity": 60.0,
            "temperature": 28.0,
            "pressure": 1013.0,
            "fan_flow": 25.0,
            "efficiency": 0.85,
            "coil_temperature": 8.0,
        }
        self.ml_model = WaterProductionML()
        self.history = []
        self._generate_training_data()

    def _generate_training_data(self):
        """
        Gera dados sintéticos para treinar o modelo de ML.
        """
        rng = np.random.default_rng(42)
        n_samples = 500
        features = rng.uniform(
            low=[30, 15, 980, 10, 0.5, 5],
            high=[95, 40, 1035, 40, 1.0, 15],
            size=(n_samples, 6)
        )
        targets = []
        for f in features:
            temp, rh, pressure, fan, eff, coil = f
            # Função física simplificada para gerar alvo realista
            sat_in = 216.7 * math.exp((17.27 * temp) / (237.7 + temp) + 17.625) / (237.3 + temp)
            sat_out = 216.7 * math.exp((17.27 * coil) / (237.7 + coil) + 17.625) / (237.3 + coil)
            output = max(0.0, (sat_in - sat_out) * (fan * 60 / 1000) * eff * 0.001)
            targets.append(output)
        self.ml_model.train(features.tolist(), targets)

    def add_tupan(self, params=None):
        model = TupanModel(params or {})
        tupan_id = len(self.tupans) + 1
        tupan = {"id": tupan_id, "model": model, "output": 0.0, "status": "online"}
        self.tupans.append(tupan)
        return tupan

    def remove_tupan(self, tupan_id):
        self.tupans = [t for t in self.tupans if t["id"] != tupan_id]

    def update_environment(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.environment:
                self.environment[key] = float(value)

    def run_cycle(self, hours=1.0):
        """
        Executa um ciclo de produção de água para todos os Tupans.
        """
        p = self.environment
        results = []
        for tupan in self.tupans:
            seed = random.randint(1, 10**9)
            output = tupan["model"].calculate_output(hours=hours, seed=seed)
            tupan["output"] = output
            tupan["status"] = "producing" if output > 0 else "idle"
            results.append({
                "tupan_id": tupan["id"],
                "output_liters": output,
                "status": tupan["status"],
            })
            self.history.append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "hours": hours,
                "relative_humidity": p["relative_humidity"],
                "temperature": p["temperature"],
                "pressure": p["pressure"],
                "output": output,
            })
        return results

    def predict_output(self, tupan_id, hours=1.0):
        """
        Usa o modelo de ML para prever a produção de água.
        """
        tupan = next((t for t in self.tupans if t["id"] == tupan_id), None)
        if not tupan:
            return None
        p = self.environment
        features = [
            p["relative_humidity"],
            p["temperature"],
            p["pressure"],
            p["fan_flow"],
            p["efficiency"],
            p["coil_temperature"],
        ]
        return self.ml_model.predict(features) * hours


# ============================================================
# APP FLASK
# ============================================================
app = Flask(__name__)
simulator = EnvironmentSimulator()


@app.route("/")
def index():
    return render_template("simulacao.html", simulator=simulator, tupans=simulator.tupans)


@app.route("/api/environment", methods=["GET", "POST"])
def api_environment():
    if request.method == "GET":
        return jsonify(simulator.environment)
    data = request.get_json() or {}
    simulator.update_environment(**data)
    return jsonify({"status": "ok", "environment": simulator.environment})


@app.route("/api/tupans/add", methods=["POST"])
def api_add_tupan():
    data = request.get_json() or {}
    tupan = simulator.add_tupan(data.get("params"))
    return jsonify({"status": "ok", "tupan": tupan}), 201


@app.route("/api/tupans/<int:tupan_id>/remove", methods=["DELETE"])
def api_remove_tupan(tupan_id):
    simulator.remove_tupan(tupan_id)
    return jsonify({"status": "ok"})


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json() or {}
    hours = float(data.get("hours", 1.0))
    results = simulator.run_cycle(hours=hours)
    predictions = []
    for r in results:
        predicted = simulator.predict_output(r["tupan_id"], hours)
        predictions.append({
            "tupan_id": r["tupan_id"],
            "predicted": round(predicted, 4) if predicted else None,
            "actual": r["output_liters"],
        })
    return jsonify({
        "status": "ok",
        "hours": hours,
        "results": results,
        "predictions": predictions,
        "total_output": round(sum(r["output_liters"] for r in results), 4),
    })


@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify(simulator.history[-100:])


@app.route("/api/ml/accuracy", methods=["GET"])
def api_ml_accuracy():
    """
    Calcula a acurácia do modelo de ML em dados de teste.
    """
    rng = np.random.default_rng(123)
    n_samples = 100
    features = rng.uniform(
        low=[30, 15, 980, 10, 0.5, 5],
        high=[95, 40, 1035, 40, 1.0, 15],
        size=(n_samples, 6)
    )
    targets = []
    for f in features:
        temp, rh, pressure, fan, eff, coil = f
        sat_in = 216.7 * math.exp((17.27 * temp) / (237.7 + temp) + 17.625) / (237.3 + temp)
        sat_out = 216.7 * math.exp((17.27 * coil) / (237.7 + coil) + 17.625) / (237.3 + coil)
        targets.append(max(0.0, (sat_in - sat_out) * (fan * 60 / 1000) * eff * 0.001))
    predictions = []
    for f in features:
        pred = simulator.ml_model.predict(f.tolist())
        predictions.append(pred if pred is not None else 0.0)
    mse = np.mean(np.square(np.array(targets) - np.array(predictions)))
    rmse = math.sqrt(mse)
    r2 = 1 - (np.sum(np.square(np.array(targets) - np.array(predictions))) / np.sum(np.square(np.array(targets) - np.mean(targets))))
    return jsonify({"rmse": round(rmse, 6), "r2": round(r2, 6)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
