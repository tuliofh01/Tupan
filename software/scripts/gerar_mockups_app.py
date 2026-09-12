#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan, Máquina de Chuva — Gerador de Mockups do App Companheiro (IoT/BT)
========================================================================

DIDÁTICA (linha de raciocínio):
  O app é a "ala remota" do Tupan: conversa com o HC-05 (Serial/Bluetooth)
  via ponte MQTT local. Em vez de desenhar telas no dedo, GERAMOS HTML real
  (as mesmas telas que um app React Native/expo renderizaria) e fotografamos
  cada uma com Chromium headless. Vantagem tripla:
    1) o mockup é executável — dá para validar fluxo e legibilidade já agora;
    2) o mesmo HTML vira spec visual para o PWA futuro (mesmo design token);
    3) tudo versionado: regenerar é `python3 gerar_mockups_app.py`.

  Telas (fluxo completo do usuário):
    01 Painel (status do ciclo FSM + água da bacia)
    02 Ciclo (timeline noite/dia: INTAKE → REGEN → DESTIL → pós-tratamento)
    03 Sensores (DHT22, DS18B20 leito/vapor, nível)
    04 Controles (ventoinhas PWM, solenoide, servo-registro, agendar ciclo)
    05 Histórico (litros/ciclo, energia, exportar CSV)
    06 Pareamento BT (HC-05: conectar, pin, diagnóstico)

  Saída: documentacao/midia/mockups/app_XX_*.png (480×960, 2× DPR).
"""

from __future__ import annotations

import html
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "documentacao" / "midia" / "mockups"
CHROME = next(
    (c for c in ("/usr/sbin/chromium", "/usr/bin/chromium")
     if Path(c).exists()), "chromium")

# ---- Design tokens (iguais aos do simulador web — spec única) --------------
CSS = """
:root{--bg:#0e1726;--painel:#16233a;--linha:#233450;--txt:#e8eef7;
--dim:#8fa3bf;--agua:#3fb6ff;--noite:#7c6cff;--dia:#ffb454;
--ok:#3ddc97;--warn:#ffd166;--erro:#ff6b6b;--uv:#b47cff;--min:#6fe0c8}
*{margin:0;padding:0;box-sizing:border-box;font-family:'DejaVu Sans',sans-serif}
body{background:var(--bg);color:var(--txt);width:480px;height:960px;
display:flex;flex-direction:column}
header{padding:26px 24px 14px;display:flex;justify-content:space-between;
align-items:center;border-bottom:1px solid var(--linha)}
header h1{font-size:22px;letter-spacing:.4px}
header .bt{font-size:12px;color:var(--ok);display:flex;gap:6px;align-items:center}
header .bt.off{color:var(--erro)}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor;
box-shadow:0 0 8px currentColor}
main{flex:1;padding:18px 24px;display:flex;flex-direction:column;gap:16px}
.card{background:var(--painel);border:1px solid var(--linha);border-radius:14px;
padding:16px}
.card h2{font-size:13px;color:var(--dim);text-transform:uppercase;
letter-spacing:1.2px;margin-bottom:10px}
.kpi{display:flex;gap:12px}
.kpi .card{flex:1;text-align:center}
.grande{font-size:34px;font-weight:700;color:var(--agua)}
.grande span{font-size:15px;color:var(--dim)}
.linha{display:flex;justify-content:space-between;padding:7px 0;
font-size:15px;border-bottom:1px dashed var(--linha)}
.linha:last-child{border-bottom:none}
.linha b{color:var(--dim);font-weight:400}
nav{display:flex;border-top:1px solid var(--linha)}
nav a{flex:1;text-align:center;padding:16px 0;font-size:11px;color:var(--dim);
text-decoration:none;border-top:2px solid transparent}
nav a.on{color:var(--agua);border-top-color:var(--agua)}
.fsm{display:flex;gap:6px;margin-top:4px}
.fsm span{flex:1;text-align:center;font-size:10px;padding:6px 0;border-radius:8px;
background:#1c2a44;color:var(--dim)}
.fsm span.on{background:var(--agua);color:#04263d;font-weight:700}
.timeline{display:flex;flex-direction:column;gap:10px}
.passo{display:flex;gap:12px;align-items:stretch}
.passo .hora{width:54px;font-size:11px;color:var(--dim);padding-top:14px}
.passo .bola{width:14px;display:flex;justify-content:center;position:relative}
.passo .bola i{width:12px;height:12px;border-radius:50%;background:var(--linha)}
.passo.on .bola i{background:var(--noite);box-shadow:0 0 10px var(--noite)}
.passo.dia.on .bola i{background:var(--dia);box-shadow:0 0 10px var(--dia)}
.passo .bola:after{content:'';position:absolute;top:12px;bottom:-12px;width:2px;
background:var(--linha)}
.passo:last-child .bola:after{display:none}
.passo .info{flex:1;background:var(--painel);border:1px solid var(--linha);
border-radius:12px;padding:10px 14px}
.passo.on .info{border-color:var(--noite)}
.passo.dia.on .info{border-color:var(--dia)}
.passo .info h3{font-size:14px;margin-bottom:3px}
.passo .info p{font-size:12px;color:var(--dim)}
.slider{height:6px;border-radius:3px;background:var(--linha);position:relative}
.slider i{position:absolute;top:-6px;left:var(--x,50%);width:18px;height:18px;
border-radius:50%;background:var(--agua);transform:translateX(-50%)}
.btn{display:block;text-align:center;padding:13px;border-radius:12px;
font-size:15px;font-weight:700;background:var(--agua);color:#04263d;
margin-top:4px}
.btn.ghost{background:none;border:1px solid var(--linha);color:var(--txt)}
.graf{height:120px;display:flex;align-items:flex-end;gap:5px;padding-top:6px}
.graf i{flex:1;border-radius:3px 3px 0 0;background:linear-gradient(180deg,
var(--agua),#1c5d8f);opacity:.85}
.graf i.noite{background:linear-gradient(180deg,var(--noite),#3a3470)}
.tag{display:inline-block;font-size:10px;padding:3px 8px;border-radius:20px;
margin-left:6px;vertical-align:2px}
.tag.uv{background:var(--uv);color:#fff}
.tag.min{background:var(--min);color:#06302a}
footer{text-align:center;font-size:10px;color:var(--dim);padding:10px}
"""

# ---- Helpers --------------------------------------------------------------

def cabecalho(titulo: str, bt: str = "HC-05 · conectado") -> str:
    return f"""<header><h1>{html.escape(titulo)}</h1>
<div class="bt {'off' if 'não' in bt else ''}"><span class="dot"></span>{html.escape(bt)}</div></header>"""


def nav(ativo: str) -> str:
    itens = [("painel", "Painel"), ("ciclo", "Ciclo"), ("sensores", "Sensores"),
             ("controles", "Controles"), ("hist", "Histórico"), ("bt", "BT")]
    li = "".join(
        f'<a class="{"on" if k == ativo else ""}" href="#">{rot}</a>'
        for k, rot in itens)
    return f"<nav>{li}</nav>"


# ---- Telas ----------------------------------------------------------------

def tela_painel() -> str:
    return f"""{cabecalho("Tupan · Painel")}
<main>
  <div class="card"><h2>Máquina de estados</h2>
    <div class="fsm">
      <span class="on">OCIOSO</span><span>INTAKE</span><span>REGEN</span>
      <span>DESTIL</span><span>CHEIO</span><span>ERRO</span>
    </div>
    <p style="font-size:12px;color:var(--dim);margin-top:8px">
      Sorção noturna inicia às 20:12 — previsão do clima (Open-Meteo)</p>
  </div>
  <div class="kpi">
    <div class="card"><div class="grande">0.75<span> kg</span></div>
      <h2>água no leito</h2></div>
    <div class="card"><div class="grande">691<span> mL</span></div>
      <h2>bacia (torneira)</h2></div>
    <div class="card"><div class="grande">0.44<span> L/kWh</span></div>
      <h2>eficiência</h2></div>
  </div>
  <div class="card"><h2>Pós-tratamento</h2>
    <div class="linha"><b>Filtro mineralizante</b><span>ativo · Ca/Mg ok
      <span class="tag min">MIN</span></span></div>
    <div class="linha"><b>Lâmpada UV-C</b><span>esterilização 254 nm ok
      <span class="tag uv">UV</span></span></div>
    <div class="linha"><b>Última troca do filtro</b><span>há 23 ciclos</span></div>
  </div>
</main>{nav("painel")}{RODAPE}"""


def tela_ciclo() -> str:
    passos = [
        ("20:12", "noite", True,  "INTAKE — sorção",
         "Ventoinhas 100% puxando ar úmido pelo leito de CaCl₂"),
        ("06:00", "noite", False, "Fechamento — servo-registro",
         "Servo fecha a entrada de ar e abre o duto de destilação"),
        ("06:05", "dia",   False, "REGEN — solenoide",
         "Leito a 120 °C libera a água retida como vapor"),
        ("06:40", "dia",   False, "DESTIL — vidraria",
         "Vapor condensa na vidraria; ~691 mL projetados"),
        ("07:10", "dia",   False, "Pós-tratamento",
         "Filtro mineralizante + UV-C → bacia com torneira"),
    ]
    linhas = ""
    for hora, periodo, on, titulo, desc in passos:
        linhas += f"""<div class="passo {periodo} {'on' if on else ''}">
<div class="hora">{hora}</div><div class="bola"><i></i></div>
<div class="info"><h3>{titulo}</h3><p>{desc}</p></div></div>"""
    return f"""{cabecalho("Ciclo Tupan")}
<main>
  <div class="card"><h2>Timeline de hoje</h2>
    <div class="timeline">{linhas}</div>
  </div>
  <div class="card"><h2>Agendar</h2>
    <div class="linha"><b>Início da sorção</b><span>20:12 (automático)</span></div>
    <div class="linha"><b>Início da regeneração</b><span>06:00 (automático)</span></div>
    <a class="btn ghost" href="#">Executar ciclo de teste agora</a>
  </div>
</main>{nav("ciclo")}{RODAPE}"""


def tela_sensores() -> str:
    return f"""{cabecalho("Sensores")}
<main>
  <div class="kpi">
    <div class="card"><div class="grande">68<span> %</span></div>
      <h2>UR do ar (DHT22)</h2></div>
    <div class="card"><div class="grande">24.6<span> °C</span></div>
      <h2>temp. ambiente</h2></div>
  </div>
  <div class="card"><h2>Leito químico (DS18B20)</h2>
    <div class="linha"><b>Temperatura do leito</b><span>22.3 °C</span></div>
    <div class="linha"><b>Massa de água retida</b><span>0.751 kg</span></div>
    <div class="linha"><b>Saturação</b><span>37.5% (0.751 / 2.0 kg)</span></div>
  </div>
  <div class="card"><h2>Duto de vapor + bacia</h2>
    <div class="linha"><b>DS18B20 vapor</b><span>— (aguardando REGEN)</span></div>
    <div class="linha"><b>Nível da bacia (capacitivo)</b><span>691 / 2000 mL</span></div>
    <div class="linha"><b>Leitura bruta ADC</b><span>354 / 1023</span></div>
  </div>
  <div class="card"><h2>Últimas 12 h — UR %</h2>
    <div class="graf">{"".join(f'<i class="{"noite" if i < 7 else ""}" style="height:{h}%"></i>' for i, h in enumerate((42, 40, 44, 51, 58, 63, 68, 66, 62, 55, 48, 43)))}</div>
  </div>
</main>{nav("sensores")}{RODAPE}"""


def tela_controles() -> str:
    return f"""{cabecalho("Controles")}
<main>
  <div class="card"><h2>Ventoinhas (PWM)</h2>
    <div class="slider" style="--x:100%"><i></i></div>
    <div class="linha"><b>Duty atual</b><span>100% (INTAKE noturno)</span></div>
  </div>
  <div class="card"><h2>Solenoide do leito</h2>
    <div class="linha"><b>Alvo de regeneração</b><span>120 °C (histerese ±2 °C)</span></div>
    <div class="linha"><b>Estado</b><span>desligada (ocioso)</span></div>
    <a class="btn ghost" href="#">Forçar 5 min de teste térmico</a>
  </div>
  <div class="card"><h2>Servo-registro de ar</h2>
    <div class="linha"><b>Posição</b><span>0° — ar novo (sorção)</span></div>
    <div class="linha"><b>Alternativa</b><span>90° — duto de destilação</span></div>
  </div>
  <div class="card"><h2>Limites</h2>
    <div class="linha"><b>Corte por bacia cheia</b><span>2000 mL</span></div>
    <div class="linha"><b>Corte térmico</b><span>135 °C (segurança)</span></div>
  </div>
  <a class="btn" href="#">Aplicar no Tupan (HC-05)</a>
</main>{nav("controles")}{RODAPE}"""


def tela_historico() -> str:
    return f"""{cabecalho("Histórico")}
<main>
  <div class="kpi">
    <div class="card"><div class="grande">593.8<span> L</span></div>
      <h2>projeção anual</h2></div>
    <div class="card"><div class="grande">0.97<span> L/dia</span></div>
      <h2>média diária</h2></div>
  </div>
  <div class="card"><h2>Últimos 7 ciclos (litros)</h2>
    <div class="graf">{"".join(f'<i style="height:{h}%"></i>' for h in (72, 81, 65, 90, 84, 77, 88))}</div>
  </div>
  <div class="card"><h2>Registro auditável</h2>
    <div class="linha"><b>Ciclo #42</b><span>0.691 L · 1.56 kWh · 0.443 L/kWh</span></div>
    <div class="linha"><b>Ciclo #41</b><span>0.702 L · 1.58 kWh · 0.444 L/kWh</span></div>
    <div class="linha"><b>Ciclo #40</b><span>0.610 L · 1.39 kWh · 0.440 L/kWh</span></div>
    <a class="btn ghost" href="#">Exportar CSV / compartilhar</a>
  </div>
</main>{nav("hist")}{RODAPE}"""


def tela_bt() -> str:
    return f"""{cabecalho("Bluetooth / IoT", "pareando…")}
<main>
  <div class="card"><h2>HC-05 (Serial Profile)</h2>
    <div class="linha"><b>MAC</b><span>98:DA:50:xx:xx:xx</span></div>
    <div class="linha"><b>PIN padrão</b><span>1234 (trocar no pareamento)</span></div>
    <div class="linha"><b>UART</b><span>9600 8N1 (AT+UART?)</span></div>
    <a class="btn" href="#">Conectar</a>
  </div>
  <div class="card"><h2>Ponte MQTT local</h2>
    <div class="linha"><b>Broker</b><span>mqtt://192.168.0.42:1883</span></div>
    <div class="linha"><b>Tópicos</b><span>tupan/telemetria · tupan/cmd</span></div>
    <div class="linha"><b>QoS</b><span>1 (telemetria), 2 (comandos)</span></div>
  </div>
  <div class="card"><h2>Diagnóstico</h2>
    <div class="linha"><b>Latência BT</b><span>38 ms</span></div>
    <div class="linha"><b>Firmware do Tupan</b><span>v0.3 (C++20, MVC)</span></div>
    <div class="linha"><b>Logs (LOG_*)</b><span>[CICLO] fsm: INTAKE…</span></div>
  </div>
</main>{nav("bt")}{RODAPE}"""


RODAPE = "<footer>Tupan, Máquina de Chuva · app companheiro IoT/BT · mockup v1</footer>"


TELAS = [
    ("app_01_painel", tela_painel),
    ("app_02_ciclo", tela_ciclo),
    ("app_03_sensores", tela_sensores),
    ("app_04_controles", tela_controles),
    ("app_05_historico", tela_historico),
    ("app_06_bluetooth", tela_bt),
]


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, geradora in TELAS:
        arq_html = SAIDA / f"{nome}.html"
        arq_html.write_text(
            f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>{geradora()}</body></html>",
            encoding="utf-8")
        png = SAIDA / f"{nome}.png"
        subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
             f"--screenshot={png}", "--window-size=480,960",
             "--force-device-scale-factor=2", "--hide-scrollbars",
             str(arq_html)],
            check=True, capture_output=True, timeout=60)
        print(f"[ok] {png.name}")
    print(f"\nMockups em: {SAIDA}")


if __name__ == "__main__":
    main()
