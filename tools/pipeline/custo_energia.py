#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Estimativa de Custo de Energia Elétrica (Brasil)
===========================================================================
DIDÁTICA (linha de raciocínio):
  O custo de operar o Tupan é ~100 % elétrico (sem combustível, sem insumo
  além do sal de Cloreto de Cálcio, que dura anos). Este módulo encadeia:

      1. ENERGIA DO CICLO  → vem do núcleo nativo (tupan_native.full_cycle),
         que já soma ventoinhas + solenoide + UV-C. A eletrônica (Mega +
         sensores) entra como consumo contínuo de 24 h.
      2. TARIFA RESIDENCIAL MÉDIA (Brasil) → R$ 0,95/kWh (premissa: média
         nacional faturada 2024–2026, já com TUSD + TE + tributos; ANEEL
         Ranking das Tarifas varia R$ 0,80–1,20/kWh entre distribuidoras).
      3. BANDEIRAS TARIFÁRIAS (ANEEL 2026) → adicional sobre 100 kWh
         faturados: VERDE R$ 0 · VERMELHA P1 R$ 4,463/MWh ·
         VERMELHA P2 R$ 7,877/MWh (valores oficiais mantidos pela ANEEL).
      4. TARIFA SOCIAL (TSEE) → famílias de baixa renda (≤ ½ salário per
         capita) com consumo mensal ≤ 80 kWh recebem 65 % de desconto —
         o Tupan consome ~51 kWh/mês, dentro da faixa.
      5. COMPARAÇÃO → R$/litro do Tupan × galão de 20 L × garrafinha 500 mL.

  SAÍDAS: data/results/custo_energia.json (métricas) +
          data/processed/custo_energia.csv (série por bandeira).
  Executar:  python3 custo_energia.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# Caminhos — pipeline vive em tools/pipeline/ (raiz = parents[2])
# ---------------------------------------------------------------------------
RAIZ: Final[Path] = Path(__file__).resolve().parents[2]
DADOS: Final[Path] = RAIZ / "data" / "results"
PROC: Final[Path] = RAIZ / "data" / "processed"
DADOS.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

# Núcleo nativo (pybind) com fallback Python — mesma física, contas idênticas.
DIST: Final[Path] = RAIZ / "build"
if str(DIST) not in sys.path:
    sys.path.insert(0, str(DIST))
try:
    import tupan_native as tn  # type: ignore[import-not-found]
    full_cycle = tn.full_cycle
    _NATIVO: Final[bool] = True
except ImportError:  # fallback: fórmulas espelhadas do servidor Flask
    sys.path.insert(0, str(RAIZ / "tools" / "server"))
    from simulador_tupan import full_cycle  # type: ignore[no-redef]
    _NATIVO = False

# ---------------------------------------------------------------------------
# PREMISSAS (documentadas — audite e ajuste se a ANEEL revisar os valores)
# ---------------------------------------------------------------------------
TARIFA_MEDIA_BRL_KWH: Final[float] = 0.95  # média residencial faturada (R$/kWh)

# Adicional das bandeiras (R$/kWh sobre o consumo faturado):
BANDEIRAS: Final[dict[str, float]] = {
    "verde":         0.000000,   # chuvas normais nos reservatórios
    "vermelha_p1":   0.004463,   # R$ 4,463/MWh (ANEEL)
    "vermelha_p2":   0.007877,   # R$ 7,877/MWh (ANEEL)
}

# Tarifa Social de Energia Elétrica (TSEE): desconto p/ consumo ≤ 80 kWh/mês
TSEE_DESCONTO: Final[float] = 0.65     # 65 % de desconto (Lei 14.541/2023)
TSEE_TETO_MENSAL_KWH: Final[float] = 80.0

# Comparação de mercado (premissas nacionais médias):
GALAO_20L_BRL: Final[float] = 12.00    # galão de água mineral (R$ 0,60/L)
GARRAFINHA_500ML_BRL: Final[float] = 2.00  # garrafinha de mercado (R$ 4,00/L)

# Eletrônica em modo de espera (Mega + sensores + OLED): contínua 24 h/7
ELETRONICA_W: Final[float] = 5.0

# Ciclo padrão de projeto (esteira de dados Petrolina-PE):
NOITE_H: Final[float] = 8.0
DIA_H: Final[float] = 6.0
UR: Final[float] = 68.0       # UR noturna média (ERA5)
TEMP_C: Final[float] = 24.0   # T noturna média (ERA5)
VAZAO: Final[float] = 25.0    # m³/h das ventoinhas
EFICIENCIA: Final[float] = 0.85
AQUECEDOR_C: Final[float] = 120.0  # solenoide


def energia_ciclo() -> dict[str, float]:
    """Decomposição auditável da energia de UM ciclo completo (kWh)."""
    cb = full_cycle(NOITE_H, DIA_H, UR, TEMP_C, VAZAO, EFICIENCIA, AQUECEDOR_C)
    fans_kwh = 7.5 * NOITE_H / 1000.0          # ventoinhas (só à noite)
    aquecedor_kwh = 250.0 * DIA_H / 1000.0     # solenoide (só de dia)
    uv_kwh = 6.0 * 0.5 / 1000.0                # UV-C 30 min pós-destilação
    eletronica_kwh = ELETRONICA_W * 24.0 / 1000.0  # Mega 24 h/dia
    total_kwh = fans_kwh + aquecedor_kwh + uv_kwh + eletronica_kwh
    return {
        "ventoinhas_kwh": round(fans_kwh, 4),
        "solenoide_kwh": round(aquecedor_kwh, 4),
        "uv_c_kwh": round(uv_kwh, 4),
        "eletronica_kwh": round(eletronica_kwh, 4),
        "total_kwh": round(total_kwh, 4),
        "potavel_l": round(cb.potable_l, 4),
        "kwh_por_litro": round(total_kwh / max(cb.potable_l, 1e-9), 3),
    }


def custo_anual(bandeira: str, tsee: bool = False) -> dict[str, float]:
    """Custo anual p/ 365 ciclos, numa bandeira, com/sem Tarifa Social."""
    e = energia_ciclo()
    tarifa = TARIFA_MEDIA_BRL_KWH + BANDEIRAS[bandeira]
    if tsee:
        tarifa *= (1.0 - TSEE_DESCONTO)
    consumo_ano_kwh = e["total_kwh"] * 365.0
    consumo_mes_kwh = consumo_ano_kwh / 12.0
    litros_ano = e["potavel_l"] * 365.0
    custo_ano = consumo_ano_kwh * tarifa
    return {
        "bandeira": bandeira,
        "tarifa_social": tsee,
        "tarifa_brl_kwh": round(tarifa, 4),
        "consumo_ano_kwh": round(consumo_ano_kwh, 1),
        "consumo_mes_kwh": round(consumo_mes_kwh, 1),
        "litros_ano": round(litros_ano, 1),
        "custo_ano_brl": round(custo_ano, 2),
        "custo_litro_brl": round(custo_ano / max(litros_ano, 1e-9), 2),
    }


def main() -> None:
    e = energia_ciclo()
    cenarios = [custo_anual(b) for b in BANDEIRAS]
    tsee = [custo_anual(b, tsee=True) for b in ("verde", "vermelha_p1")]

    # Comparação de mercado (R$/litro):
    comparacao = {
        "tupan_bandeira_verde": next(c["custo_litro_brl"] for c in cenarios
                                     if c["bandeira"] == "verde"),
        "tupan_tsee_65pct": tsee[0]["custo_litro_brl"],
        "galao_20l": round(GALAO_20L_BRL / 20.0, 2),
        "garrafinha_500ml": round(GARRAFINHA_500ML_BRL / 0.5, 2),
    }

    resultado: dict[str, Any] = {
        "_fonte": ("ANEEL — bandeiras tarifárias (R$/MWh: vermelha P1 4,463; "
                   "P2 7,877) e tarifa residencial média nacional como premissa "
                   "(R$ 0,95/kWh faturado, inclui tributos). TSEE: 65 % p/ "
                   "consumo ≤ 80 kWh/mês (Lei 14.541/2023)."),
        "_nativo": _NATIVO,
        "premissas": {
            "tarifa_media_brl_kwh": TARIFA_MEDIA_BRL_KWH,
            "ciclo": {"noite_h": NOITE_H, "dia_h": DIA_H, "ur_pct": UR,
                      "temp_c": TEMP_C, "vazao_m3h": VAZAO,
                      "eficiencia": EFICIENCIA, "solenoide_c": AQUECEDOR_C},
        },
        "energia_ciclo": e,
        "cenarios_anuais": cenarios + tsee,
        "comparacao_brl_por_litro": comparacao,
    }
    (DADOS / "custo_energia.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV — série por bandeira (facilita o gráfico do relatório/pitch):
    with (PROC / "custo_energia.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cenarios[0].keys()))
        w.writeheader()
        w.writerows(cenarios + tsee)

    # Impressão didática (mesmos números do JSON):
    print("Tupan — custo de energia elétrica (valores médios do Brasil)")
    print(f"  energia/ciclo : {e['total_kwh']:.3f} kWh "
          f"(solenoide {e['solenoide_kwh']} · ventoinhas {e['ventoinhas_kwh']} · "
          f"eletrônica {e['eletronica_kwh']} · UV {e['uv_c_kwh']})")
    print(f"  água potável  : {e['potavel_l']:.3f} L/ciclo → "
          f"{e['kwh_por_litro']:.2f} kWh/L")
    print(f"  consumo       : {cenarios[0]['consumo_mes_kwh']:.1f} kWh/mês "
          f"(TSEE ≤ {TSEE_TETO_MENSAL_KWH:.0f} kWh ⇒ desconto de 65 %)")
    print("  cenário anual (365 ciclos):")
    for c in cenarios + tsee:
        etiqueta = f"{c['bandeira']}" + (" + TSEE" if c["tarifa_social"] else "")
        print(f"    {etiqueta:<20} R$ {c['tarifa_brl_kwh']:.4f}/kWh → "
              f"R$ {c['custo_ano_brl']:>7.2f}/ano · "
              f"R$ {c['custo_litro_brl']:.2f}/litro")
    print(f"  comparação R$/L: Tupan verde {comparacao['tupan_bandeira_verde']:.2f}"
          f" · Tupan+TSEE {comparacao['tupan_tsee_65pct']:.2f}"
          f" · galão 20 L {comparacao['galao_20l']:.2f}"
          f" · garrafinha {comparacao['garrafinha_500ml']:.2f}")
    print(f"\nSaída: {DADOS / 'custo_energia.json'} e custo_energia.csv")


if __name__ == "__main__":
    main()
