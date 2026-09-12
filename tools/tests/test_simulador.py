#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Testes unitários do simulador (pytest)
================================================================
Refatorados p/ o CICLO REAL (sem compressor):
    noite: ventoinhas + leito CaCl₂ (sorção) → dia: solenoide 120 °C
    → vidraria (destilação) → filtro mineralizante + UV-C → bacia 2 L.
API atual: TupanModel.calculate(night_hours, day_hours, seed) e
Simulador.ciclo(...) — paridade com o núcleo nativo (pybind) garantida.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

import simulador_tupan as st


# ============================================================
# FÍSICA DETERMINÍSTICA (fallback/nativo — mesmo contrato)
# ============================================================
class TestFisicaDeterministica:
    def test_ciclo_padrao_produz_agua_potavel(self) -> None:
        cb = st.full_cycle(8.0, 6.0, 65.0, 24.0, 25.0, 0.85, 120.0)
        assert cb.potable_l > 0.0
        assert cb.potable_l < 2.0  # cabe na bacia

    def test_potavel_menor_que_destilado(self) -> None:
        """Filtro mineralizante perde ~2 % na purga."""
        cb = st.full_cycle(8.0, 6.0, 68.0, 24.0, 25.0, 0.85, 120.0)
        assert cb.potable_l <= cb.distilled_l

    def test_bacia_limita_em_dois_litros(self) -> None:
        """Ciclo hipotético de alta produção → bacia satura em 2 L."""
        cb = st.full_cycle(12.0, 10.0, 98.0, 30.0, 45.0, 1.0, 160.0)
        assert cb.potable_l <= 2.0 + 1e-9

    def test_ur_baixa_reduz_producao(self) -> None:
        seco = st.full_cycle(8.0, 6.0, 30.0, 24.0, 25.0, 0.85, 120.0)
        umido = st.full_cycle(8.0, 6.0, 90.0, 24.0, 25.0, 0.85, 120.0)
        assert umido.potable_l > seco.potable_l

    def test_solenoide_fria_nao_libera_agua(self) -> None:
        cb = st.full_cycle(8.0, 6.0, 65.0, 24.0, 25.0, 0.85, 60.0)
        assert cb.distilled_l == 0.0
        assert cb.potable_l == 0.0

    def test_mineralizacao_presente_quando_produz(self) -> None:
        cb = st.full_cycle(8.0, 6.0, 68.0, 24.0, 25.0, 0.85, 120.0)
        assert cb.ca_mg_l > 0.0
        assert cb.mg_mg_l > 0.0

    def test_energia_inclui_uv(self) -> None:
        """UV-C 6 W × 30 min = 10 800 J = 10,8 kJ fixos por ciclo (kJ_total)."""
        sem_agua = st.full_cycle(8.0, 6.0, 0.0, 24.0, 25.0, 0.85, 120.0)
        assert sem_agua.energy_kj_total >= 10.8

    def test_l_por_kwh_positivo(self) -> None:
        cb = st.full_cycle(8.0, 6.0, 68.0, 24.0, 25.0, 0.85, 120.0)
        assert cb.liters_per_kwh > 0.0


# ============================================================
# MODELO ESTOCÁSTICO (TupanModel)
# ============================================================
class TestTupanModel:
    def test_mesmo_seed_mesmo_resultado(self) -> None:
        m = st.TupanModel()
        assert m.calculate(8.0, 6.0, 7) == m.calculate(8.0, 6.0, 7)

    def test_ruido_zero_igual_deterministico(self) -> None:
        m = st.TupanModel({"relative_humidity": 68.0, "temperature": 24.0,
                           "fan_flow": 25.0, "efficiency": 0.85,
                           "heater_temp_c": 120.0})
        m.noise = 0.0
        cb = st.full_cycle(8.0, 6.0, 68.0, 24.0, 25.0, 0.85, 120.0)
        assert math.isclose(m.calculate(8.0, 6.0, 99), cb.distilled_l, abs_tol=1e-9)

    def test_sem_vazao_produz_zero(self) -> None:
        m = st.TupanModel({"relative_humidity": 68.0, "temperature": 24.0,
                           "fan_flow": 0.0, "efficiency": 0.85,
                           "heater_temp_c": 120.0})
        assert m.calculate(8.0, 6.0, 1) == 0.0

    def test_nunca_negativo(self) -> None:
        m = st.TupanModel({"relative_humidity": 10.0, "temperature": 15.0,
                           "fan_flow": 10.0, "efficiency": 0.5,
                           "heater_temp_c": 90.0})
        for seed in range(20):
            assert m.calculate(4.0, 3.0, seed) >= 0.0


# ============================================================
# FROTA + HISTÓRICO (Simulador)
# ============================================================
class TestSimulador:
    def test_adicionar_ids_incrementais(self) -> None:
        s = st.Simulador()
        assert s.adicionar() == 1
        assert s.adicionar() == 2
        assert len(s.frota) == 2

    def test_remover(self) -> None:
        s = st.Simulador()
        s.adicionar()
        s.adicionar()
        s.remover(1)
        assert len(s.frota) == 1
        assert s.frota[0]["id"] == 2

    def test_ciclo_popula_resultados_e_historico(self) -> None:
        s = st.Simulador()
        s.adicionar()
        r = s.ciclo(8.0, 6.0)
        assert len(r) == 1
        assert r[0]["litros"] >= 0.0
        assert r[0]["status"] in ("produzindo", "ocioso")
        assert len(s.historico) == 1
        # Histórico auditável com pós-tratamento:
        h = s.historico[0]
        assert "litros_potaveis" in h and "ca_mg_l" in h and "bacia_cheia" in h

    def test_contas_refletem_novo_ciclo(self) -> None:
        s = st.Simulador()
        c = s.contas()
        assert set(c) == {"kg_sorvidos", "litros_destilados", "litros_potaveis",
                          "ca_mg_l", "mg_mg_l", "bacia_cheia", "l_por_kwh"}


# ============================================================
# API FLASK (contrato JSON atualizado)
# ============================================================
class TestFlaskAPI:
    @pytest.fixture(autouse=True)
    def _cliente(self) -> None:
        st.sim = st.Simulador()
        st.app.config["TESTING"] = True
        self.client = st.app.test_client()

    def test_index_ok(self) -> None:
        r = self.client.get("/")
        assert r.status_code == 200
        assert b"Tupan" in r.data or b"tupan" in r.data

    def test_ciclo_retorna_potaveis_e_minerais(self) -> None:
        r = self.client.post("/api/ciclo", json={"relative_humidity": 68.0,
                                                 "temperature": 24.0,
                                                 "fan_flow": 25.0,
                                                 "heater_temp_c": 120.0,
                                                 "noite_h": 8.0, "dia_h": 6.0})
        assert r.status_code == 200
        contas = r.get_json()["contas"]
        assert contas["litros_potaveis"] > 0.0
        assert contas["ca_mg_l"] > 0.0
        assert "bacia_cheia" in contas

    def test_ambiente_post(self) -> None:
        r = self.client.post("/api/ambiente", json={"relative_humidity": 75.0})
        assert r.status_code == 200
        assert r.get_json()["ambiente"]["relative_humidity"] == 75.0

    def test_frota_adicionar_remover(self) -> None:
        r = self.client.post("/api/frota/adicionar", json={})
        assert r.status_code == 201
        assert self.client.post("/api/frota/remover/1").get_json()["status"] == "ok"

    def test_historico(self) -> None:
        self.client.post("/api/ciclo", json={"noite_h": 8.0, "dia_h": 6.0})
        r = self.client.get("/api/historico")
        assert r.status_code == 200
        h = r.get_json()
        assert len(h) == 1 and "litros_potaveis" in h[0]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
