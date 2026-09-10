#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes unitários do simulador Tupan (TupanModel, ML e API Flask)."""
import math
import os
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import simulador_tupan as st


# ============================================================
# TESTES DO MODELO FÍSICO (TupanModel)
# ============================================================
class TestTupanModel:
    def test_default_output_is_positive_and_small(self):
        out = st.TupanModel().calculate_output(hours=1.0, seed=1)
        assert out > 0.0
        assert out < 1.0

    def test_output_never_negative(self):
        model = st.TupanModel({"relative_humidity": 10, "coil_temperature": 20})
        assert model.calculate_output(hours=1.0, seed=1) >= 0.0

    def test_deterministic_with_same_seed(self):
        model = st.TupanModel()
        assert model.calculate_output(hours=1.0, seed=7) == model.calculate_output(hours=1.0, seed=7)

    def test_zero_fan_flow_produces_zero(self):
        model = st.TupanModel({"fan_flow": 0.0})
        assert model.calculate_output(hours=1.0) == 0.0

    def test_zero_efficiency_produces_zero(self):
        model = st.TupanModel({"efficiency": 0.0})
        assert model.calculate_output(hours=1.0) == 0.0

    def test_coil_at_air_temperature_produces_zero(self):
        model = st.TupanModel({"coil_temperature": 28.0, "temperature": 28.0})
        assert model.calculate_output(hours=1.0) == 0.0

    def test_output_is_rounded_to_four_decimals(self):
        out = st.TupanModel().calculate_output(hours=0.5, seed=3)
        assert isinstance(out, float)
        assert round(out, 4) == out

    def test_higher_humidity_increases_output(self):
        low = st.TupanModel({"relative_humidity": 40}).calculate_output(hours=1.0, seed=5)
        high = st.TupanModel({"relative_humidity": 80}).calculate_output(hours=1.0, seed=5)
        assert low < high

    def test_higher_temperature_increases_output(self):
        low = st.TupanModel({"temperature": 24}).calculate_output(hours=1.0, seed=5)
        high = st.TupanModel({"temperature": 34}).calculate_output(hours=1.0, seed=5)
        assert low < high

    def test_higher_fan_flow_increases_output(self):
        low = st.TupanModel({"fan_flow": 15}).calculate_output(hours=1.0, seed=5)
        high = st.TupanModel({"fan_flow": 35}).calculate_output(hours=1.0, seed=5)
        assert low < high

    def test_colder_coil_increases_output(self):
        low = st.TupanModel({"coil_temperature": 12}).calculate_output(hours=1.0, seed=5)
        high = st.TupanModel({"coil_temperature": 4}).calculate_output(hours=1.0, seed=5)
        assert low < high

    def test_duration_scales_output_linearly(self):
        model = st.TupanModel()
        one_hour = model.calculate_output(hours=1.0, seed=9)
        two_hours = model.calculate_output(hours=2.0, seed=9)
        assert two_hours == pytest.approx(2 * one_hour, rel=1e-6)

    def test_noise_zeroed_is_deterministic_without_seed(self):
        model = st.TupanModel({"noise": 0.0})
        assert model.calculate_output(hours=1.0) == model.calculate_output(hours=1.0)


# ============================================================
# TESTES DA FÍSICA DETERMINÍSTICA
# ============================================================
class TestTheoreticalOutput:
    def test_returns_positive_value_for_typical_conditions(self):
        out = st.theoretical_output(1.0, humidity=60, temperature=28, fan_flow=25, efficiency=0.85, coil_temperature=8)
        assert out > 0.0
        assert out < 1.0

    def test_zero_when_no_condensable_vapor(self):
        out = st.theoretical_output(1.0, humidity=10, temperature=20, fan_flow=25, efficiency=0.85, coil_temperature=20)
        assert out == 0.0

    def test_monotonic_in_humidity(self):
        values = [
            st.theoretical_output(1.0, h, 30, 25, 0.85, 8)
            for h in [30, 50, 70, 90]
        ]
        assert values == sorted(values)

    def test_linear_in_duration(self):
        v1 = st.theoretical_output(1.0, 60, 28, 25, 0.85, 8)
        v3 = st.theoretical_output(3.0, 60, 28, 25, 0.85, 8)
        assert v3 == pytest.approx(3 * v1, rel=1e-9)


# ============================================================
# TESTES DO MODELO DE MACHINE LEARNING
# ============================================================
class TestWaterProductionML:
    def test_predict_before_training_returns_none(self):
        ml = st.WaterProductionML()
        assert ml.predict([[60, 28, 1013, 25, 0.85, 8]]) is None

    def test_predict_after_training_returns_float(self):
        ml = st.WaterProductionML()
        features = [[60, 28, 1013, 25, 0.85, 8]]
        targets = [st.theoretical_output(1.0, 60, 28, 25, 0.85, 8)]
        ml.train(features, targets)
        pred = ml.predict(features)
        assert isinstance(pred, float)
        assert math.isfinite(pred)

    def test_trained_model_baseline_direction(self):
        ml = st.WaterProductionML()
        train = [
            [h, 28, 1013, 25, 0.85, 8]
            for h in range(30, 96, 5)
        ]
        targets = [st.theoretical_output(1.0, h, 28, 25, 0.85, 8) for h, *_ in train]
        ml.train(train, targets)
        p_low = ml.predict([[35, 28, 1013, 25, 0.85, 8]])
        p_high = ml.predict([[85, 28, 1013, 25, 0.85, 8]])
        assert p_low is not None and p_high is not None
        assert p_low < p_high


# ============================================================
# TESTES DO SIMULADOR DE AMBIENTE
# ============================================================
class TestEnvironmentSimulator:
    @pytest.fixture(autouse=True)
    def _reset(self):
        self.sim = st.EnvironmentSimulator()
        random.seed(1234)
        yield

    def test_starts_empty(self):
        assert self.sim.tupans == []

    def test_add_tupan_assigns_incremental_ids(self):
        t1 = self.sim.add_tupan()
        t2 = self.sim.add_tupan()
        assert t1["id"] == 1
        assert t2["id"] == 2
        assert len(self.sim.tupans) == 2

    def test_remove_tupan(self):
        self.sim.add_tupan()
        self.sim.add_tupan()
        self.sim.remove_tupan(1)
        assert len(self.sim.tupans) == 1
        assert self.sim.tupans[0]["id"] == 2

    def test_remove_unknown_id_is_ignored(self):
        self.sim.add_tupan()
        self.sim.remove_tupan(99)
        assert len(self.sim.tupans) == 1

    def test_update_environment(self):
        self.sim.update_environment(relative_humidity=80.0, temperature=32.0)
        assert self.sim.environment["relative_humidity"] == 80.0
        assert self.sim.environment["temperature"] == 32.0

    def test_update_environment_ignores_unknown_keys(self):
        self.sim.update_environment(relative_humidity=70.0, unknown_key=123)
        assert self.sim.environment["relative_humidity"] == 70.0
        assert "unknown_key" not in self.sim.environment

    def test_run_cycle_empty_simulator_returns_empty(self):
        assert self.sim.run_cycle(hours=1.0) == []

    def test_run_cycle_populates_results_and_history(self):
        self.sim.add_tupan()
        self.sim.add_tupan()
        results = self.sim.run_cycle(hours=1.0)
        assert len(results) == 2
        for r in results:
            assert r["output_liters"] >= 0.0
            assert r["status"] in ("producing", "idle")
        assert len(self.sim.history) == 2

    def test_run_cycle_updates_tupan_state(self):
        self.sim.add_tupan()
        self.sim.run_cycle(hours=1.0)
        tupan = self.sim.tupans[0]
        assert isinstance(tupan["output"], float)
        assert tupan["output"] >= 0.0
        assert tupan["status"] in ("producing", "idle")

    def test_environment_state_carries_to_cycle(self):
        self.sim.update_environment(relative_humidity=90.0)
        self.sim.add_tupan()
        wet = self.sim.run_cycle(hours=1.0)[0]["output_liters"]
        self.sim.update_environment(relative_humidity=20.0)
        self.sim.tupans[0]["output"] = 0.0
        dry = self.sim.run_cycle(hours=1.0)[0]["output_liters"]
        assert wet > 0.0
        assert dry < wet
        assert wet >= dry

    def test_predict_output_unknown_id_returns_none(self):
        self.sim.add_tupan()
        assert self.sim.predict_output(99, hours=1.0) is None

    def test_predict_output_returns_positive_float(self):
        self.sim.update_environment(relative_humidity=80.0, temperature=30.0)
        self.sim.add_tupan()
        pred = self.sim.predict_output(1, hours=1.0)
        assert pred is not None
        assert pred > 0.0


# ============================================================
# TESTES DA API FLASK
# ============================================================
class TestFlaskAPI:
    @pytest.fixture(autouse=True)
    def _client(self):
        st.simulator = st.EnvironmentSimulator()
        st.app.config["TESTING"] = True
        client = st.app.test_client()
        yield client

    def test_index_returns_ok(self, _client):
        resp = _client.get("/")
        assert resp.status_code == 200
        assert b"Tupan" in resp.data or b"tupan" in resp.data

    def test_get_environment(self, _client):
        resp = _client.get("/api/environment")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "relative_humidity" in data
        assert data["relative_humidity"] == 60.0

    def test_post_environment_updates(self, _client):
        resp = _client.post("/api/environment", json={"relative_humidity": 75.0})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "ok"
        assert body["environment"]["relative_humidity"] == 75.0

    def test_add_tupan_endpoint(self, _client):
        resp = _client.post("/api/tupans/add", json={})
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "ok"
        assert body["tupan"]["id"] == 1

    def test_add_tupan_with_params(self, _client):
        resp = _client.post("/api/tupans/add", json={"params": {"efficiency": 0.9}})
        assert resp.status_code == 201
        assert st.simulator.tupans[0]["model"].params["efficiency"] == 0.9

    def test_remove_tupan_endpoint(self, _client):
        _client.post("/api/tupans/add", json={})
        resp = _client.delete("/api/tupans/1/remove")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_run_endpoint(self, _client):
        _client.post("/api/tupans/add", json={})
        resp = _client.post("/api/run", json={"hours": 1.0})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "ok"
        assert len(body["results"]) == 1
        assert body["total_output"] >= 0.0
        assert body["predictions"][0]["actual"] == body["results"][0]["output_liters"]

    def test_history_endpoint(self, _client):
        resp = _client.get("/api/history")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_ml_accuracy_endpoint(self, _client):
        resp = _client.get("/api/ml/accuracy")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["rmse"] > 0.0
        assert body["r2"] > 0.0

    def test_missing_json_body_is_tolerated(self, _client):
        resp = _client.post("/api/environment")
        assert resp.status_code == 200