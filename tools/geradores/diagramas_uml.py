#!/usr/bin/env python3
"""Gera diagramas UML para o projeto Tupan Water Maker."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = str(BASE / "docs" / "midia" / "diagramas")
os.makedirs(OUT, exist_ok=True)

def draw_uml_use_case():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('Diagrama de Casos de Uso — Sistema Tupan', fontsize=14, fontweight='bold')

    actor_x, actor_y = 15, 40
    ax.text(actor_x, actor_y, 'Usuário\n(Túlio)', fontsize=10, ha='center', va='center',
            bbox=dict(boxstyle='ellipse', facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=2))

    cases = [
        ('Monitorar\nSensoriamento', (55, 75)),
        ('Configurar\nAparelho', (55, 60)),
        ('Controlar\nAtuadores', (55, 45)),
        ('Coletar\nÁgua', (55, 30)),
        ('Reciclar\nReagentes', (55, 15)),
    ]
    for label, (x, y) in cases:
        ax.text(x, y, label, fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='ellipse', facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=1.5))
        ax.annotate('', xy=(x-5, y), xytext=(actor_x+5, actor_y),
                     arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))

    # Sistema boundary
    rect = mpatches.FancyBboxPatch((45, 10), 45, 75, boxstyle="round,pad=0.3",
                                    facecolor='none', edgecolor='#333', linestyle='--', linewidth=1)
    ax.add_patch(rect)
    ax.text(70, 88, 'Sistema Tupan', fontsize=11, ha='center', fontweight='bold')

    # Relacionamentos
    ax.annotate('', xy=(62, 50), xytext=(62, 40),
                arrowprops=dict(arrowstyle='->', lw=1, color='#888'))
    ax.annotate('', xy=(62, 35), xytext=(62, 25),
                arrowprops=dict(arrowstyle='->', lw=1, color='#888'))

    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'uml_caso_uso.png'), dpi=150)
    plt.close()

def draw_uml_sequence():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('Diagrama de Sequência — Comunicação Bluetooth/MQTT', fontsize=14, fontweight='bold')

    participants = [
        ('Usuário', (15, 95)),
        ('App Mobile', (15, 78)),
        ('HC-05 Bluetooth', (15, 61)),
        ('Arduino Mega\n(Model/Controller)', (15, 38)),
        ('Atuadores', (15, 20)),
    ]
    for name, (x, y) in participants:
        ax.text(x, y, name, fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=1.5))
        ax.plot([x+40, x+40], [y-5, y-18], color='#333', lw=1.5)

    messages = [
        (50, 95, 78, 'Solicitar\nStatus'),
        (50, 78, 61, 'JSON via\nUART'),
        (50, 61, 38, 'lerSensores()'),
        (50, 38, 38, 'processar()', 'Controller'),
        (50, 38, 20, 'ativarCompressor()\nativarValvula()'),
        (50, 20, 38, 'Feedback\nOK'),
        (50, 38, 61, 'enviarStatus()'),
        (50, 61, 78, 'JSON ativo'),
        (50, 78, 95, 'Atualizar\nDashboard'),
    ]
    for msg in messages:
        y1, y2 = msg[1], msg[2]
        ax.annotate('', xy=(y2, 95-y2+15), xytext=(y1, 95-y1+15),
                     arrowprops=dict(arrowstyle='->', lw=1.5, color='#1565C0',
                                    connectionstyle='arc3,rad=0.15'))
        label_x = (y1 + y2) / 2 + 8
        label_y = 95 - (y1 + y2) / 2 + 15
        ax.text(label_x, label_y, msg[3], fontsize=7, ha='center', color='#333')

    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'uml_sequencia.png'), dpi=150)
    plt.close()

def draw_uml_class():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('Diagrama de Classes — Arquitetura MVC C++20', fontsize=14, fontweight='bold')

    classes = [
        ('«enum» SystemState\n{IDLE, INIT, COOLING,\nCONDENSING, FULL,\nERROR, MAINTENANCE}', (15, 75), '#E8F5E9'),
        ('«struct» SensorData\nfloat temp\nfloat humidity\nfloat pressure\nuint32_t timestamp', (50, 80), '#E3F2FD'),
        ('«struct» SystemConfig\nfloat tempThreshold\nfloat humidityThreshold\nuint16_t cycleDuration', (80, 80), '#FFF3E0'),
        ('Model', (15, 55), '#E8F5E9'),
        ('View', (50, 55), '#E1F5FE'),
        ('Controller', (80, 55), '#FCE4EC'),
        ('+update()', (15, 40), '#E8F5E9'),
        ('+showData()\n+showState()', (50, 40), '#E1F5FE'),
        ('+update()\n+handleComm()\n+manageActuators()', (80, 40), '#FCE4EC'),
    ]

    for label, (x, y), color in classes:
        ax.text(x, y, label, fontsize=8, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, edgecolor='#333', linewidth=1.5))

    # Inheritance/Composition arrows
    arrows = [
        ((15, 75), (15, 60)),  # enum → Model
        ((50, 80), (50, 62)),  # SensorData → Model
        ((80, 80), (80, 62)),  # SystemConfig → Model
        ((15, 55), (15, 47)),  # Model → impl
        ((50, 55), (50, 47)),  # View → impl
        ((80, 55), (80, 47)),  # Controller → impl
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate('', xy=(x2, y2-3), xytext=(x1, y1+3),
                     arrowprops=dict(arrowstyle='->', lw=1.5, color='#555'))

    # Composition arrows (Controller → Model, Controller → View)
    ax.annotate('', xy=(30, 55), xytext=(65, 55),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#C62828', connectionstyle='arc3,rad=0.2'))
    ax.text(48, 60, 'usa', fontsize=8, color='#C62828')

    ax.annotate('', xy=(65, 55), xytext=(65, 55),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#C62828'))

    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'uml_classes.png'), dpi=150)
    plt.close()

def draw_firmware_flowchart():
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('Fluxograma — Firmware MVP (C++20, FSM)', fontsize=14, fontweight='bold')

    states = [
        ('Início\nsetup()', (50, 95), '#E8F5E9'),
        ('IDLE\nAguardando', (50, 80), '#E3F2FD'),
        ('INIT\nLer Sensores\n(DHT22, DS18B20,\nBMP280)', (50, 66), '#E3F2FD'),
        ('COOLING\nResfriar Serpentina\n(Relé Compressor)', (50, 52), '#FFF3E0'),
        ('CONDENSING\nRelé + Válvula\nSolenóide (PWM)', (50, 38), '#FCE4EC'),
        ('FULL\nReservatório Cheio', (50, 24), '#FCE4EC'),
        ('ERROR / MAINTENANCE\nFalha detectada', (50, 12), '#FFEBEE'),
    ]
    for label, (x, y), color in states:
        ax.text(x, y, label, fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.4', facecolor=color, edgecolor='#333', linewidth=1.5))

    # Arrows principais
    for i in range(len(states)-1):
        x1, y1 = states[i][1]
        x2, y2 = states[i+1][1]
        ax.annotate('', xy=(x2, y2+5), xytext=(x1, y1-5),
                     arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))

    # Loop back: COOLING → IDLE (thresholds não atendidos)
    ax.annotate('', xy=(50, 80), xytext=(50, 52),
                arrowprops=dict(arrowstyle='->', lw=1, color='#888', linestyle='--',
                               connectionstyle='arc3,rad=-0.2'))
    ax.text(64, 66, 'Condições\nnão atendidas', fontsize=7, ha='center', color='#888')

    # Loop back: FULL → IDLE (ciclo completo / esvaziamento)
    ax.annotate('', xy=(50, 80), xytext=(50, 24),
                arrowprops=dict(arrowstyle='->', lw=1, color='#888', linestyle='--',
                               connectionstyle='arc3,rad=-0.5'))
    ax.text(66, 52, 'Esvaziamento\nconcluído', fontsize=7, ha='center', color='#888')

    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'fluxograma_firmware.png'), dpi=150)
    plt.close()

if __name__ == '__main__':
    draw_uml_use_case()
    draw_uml_sequence()
    draw_uml_class()
    draw_firmware_flowchart()
    print('Todos os diagramas UML e fluxogramas gerados.')