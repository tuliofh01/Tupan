#!/usr/bin/env python3
"""Gera esquemática elétrica do Tupan Water Maker em PNG e SVG."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

def box(x, y, w, h, label, color='#E8F0FE'):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                          facecolor=color, edgecolor='#1565C0', linewidth=2)
    ax.add_patch(rect)
    ax.text(x+w/2, y+h/2, label, ha='center', va='center', fontsize=9, fontweight='bold')

def arrow(x1, y1, x2, y2, label=''):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", lw=1.5, color='#333'))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+0.5, label, fontsize=7, ha='center')

# Título
ax.text(50, 97, 'ESQUEMÁTICA ELÉTRICA — TUPAN WATER MAKER', fontsize=14, fontweight='bold', ha='center')

# Fonte de Energia
box(5, 70, 18, 12, 'FONTE DE ENERGIA\nBATERIA 12V 60Ah\n+ Carregador AC 110/220V', '#FFF3E0')
box(5, 52, 18, 10, 'RELÉ DE TRANSFERÊNCIA\nChaveamento automático', '#FFF3E0')
box(5, 34, 18, 10, 'LM7805\n12V → 5V', '#FFF3E0')

# Arduino Mega
box(30, 70, 20, 14, 'ARDUINO MEGA 2560\nATmega2560\n16MHz / 256KB Flash', '#E8F5E9')

# Sensores
box(55, 70, 14, 8, 'DHT22\nTemperatura/Umidade', '#E3F2FD')
box(72, 70, 14, 8, 'BMP280\nPressão (I²C)', '#E3F2FD')
box(55, 58, 14, 8, 'DS18B20\nTemp. Serpentina', '#E3F2FD')
box(72, 58, 14, 8, 'Nível Capacitivo\nReservatório', '#E3F2FD')

# Atuadores
box(30, 34, 18, 10, 'RELÉ 12V\nCompressor + Ventilador', '#FCE4EC')
box(52, 34, 18, 10, 'MOSFET IRF540N\nVálvula Solenóide', '#FCE4EC')

# Bluetooth / IoT
box(30, 14, 20, 10, 'MÓDULO BLUETOOTH\nHC-05\nUART ↔ App', '#E1F5FE')
box(52, 14, 18, 10, 'DISPLAY OLED 0,96"\nI²C', '#E1F5FE')

# Conexões
arrow(14, 70, 30, 77, 'Alimentação')
arrow(14, 52, 40, 70, '12V')
arrow(14, 34, 40, 52, '5V')
arrow(50, 77, 55, 74, 'Digital')
arrow(50, 77, 72, 74, 'I²C')
arrow(50, 77, 55, 62, '1-Wire')
arrow(50, 77, 72, 62, 'Digital')
arrow(40, 34, 30, 39, 'Relé')
arrow(48, 34, 52, 39, 'PWM')
arrow(40, 14, 30, 24, 'UART')
arrow(40, 14, 52, 24, 'I²C')

# Legenda
legend_elements = [
    mpatches.Patch(facecolor='#E8F0FE', edgecolor='#1565C0', label='Eletrônica'),
    mpatches.Patch(facecolor='#FFF3E0', edgecolor='#E65100', label='Alimentação'),
    mpatches.Patch(facecolor='#E8F5E9', edgecolor='#2E7D32', label='Sensor'),
    mpatches.Patch(facecolor='#FCE4EC', edgecolor='#C62828', label='Atuador'),
    mpatches.Patch(facecolor='#E1F5FE', edgecolor='#0277BD', label='IoT'),
]
ax.legend(handles=legend_elements, loc='lower center', ncol=5, fontsize=8)

plt.tight_layout()
out = '/home/tuliofh01/Documents/Arquivo Acadêmico/PUC-MG/Engenharia de Computação/Disciplinas/2026.2/Iot & PLCs/Tupan Water Maker/Documentação Oficial/Arquivos CAD/esquema_eletrico.png'
plt.savefig(out, dpi=150, bbox_inches='tight')
print('Salvo:', out)