#!/usr/bin/env python3
"""Gera todas as imagens e diagramas do projeto Tupan Water Maker."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os

OUT = '/home/tuliofh01/Documents/Arquivo Acadêmico/PUC-MG/Engenharia de Computação/Disciplinas/2026.2/Iot & PLCs/Tupan Water Maker/Documentação Oficial/Arquivo de Mídia'
os.makedirs(OUT, exist_ok=True)

# 1. Melhorar imagem inicial
src = '/home/tuliofh01/Documents/Arquivo Acadêmico/PUC-MG/Engenharia de Computação/Disciplinas/2026.2/Iot & PLCs/Tupan Water Maker/Documentação Oficial/Arquivo de Mídia/projSketch.jpg'
img = Image.open(src)
img = img.filter(ImageFilter.SHARPEN)
img = ImageEnhance.Contrast(img).enhance(1.15)
img.save(os.path.join(OUT, 'projSketch_melhorada.jpg'), quality=95)
print('Imagem melhorada salva.')

# 2. Gráfico de descarga da bateria
fig, ax = plt.subplots(figsize=(8, 5))
t = np.linspace(0, 24, 200)
levels = {
    'Bateria 12V 60Ah (720Wh)': 100 * np.exp(-t / 20.5),
    'Modo Eco (5W)': 100 * np.exp(-t / 144),
}
for label, y in levels.items():
    ax.plot(t, y, linewidth=2, label=label)
ax.axhline(20, color='red', linestyle='--', alpha=0.6, label='Limite seguro (20%)')
ax.set_xlabel('Tempo (horas)')
ax.set_ylabel('Carga da bateria (%)')
ax.set_title('Curva de Descarga — Sistema de Energia Dual')
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'grafico_descarga_bateria.png'), dpi=150)
plt.close()

# 3. Gráfico de regressão Umidade × Produção de Água
fig, ax = plt.subplots(figsize=(8, 5))
hum = np.array([40, 45, 50, 55, 60, 65, 70, 75, 80, 85])
prod = np.array([60, 75, 90, 105, 120, 135, 150, 165, 180, 195])
coef = np.polyfit(hum, prod, 1)
x = np.linspace(40, 85, 100)
y = coef[0] * x + coef[1]
ax.scatter(hum, prod, color='#1565C0', label='Dados simulados')
ax.plot(x, y, color='#E65100', linestyle='--', label='Regressão linear')
ax.set_xlabel('Umidade Relativa do Ar (%)')
ax.set_ylabel('Produção de Água (mL/24h)')
ax.set_title('Correlação entre Umidade e Produção de Água')
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'grafico_umidade_producao.png'), dpi=150)
plt.close()

# 4. Fluxograma do ciclo de reciclagem química
fig, ax = plt.subplots(figsize=(8, 8))
ax.axis('off')
steps = [
    ('Água coletada', (0.5, 0.95), '#E8F5E9'),
    ('Filtragem inicial', (0.5, 0.82), '#E8F0FE'),
    ('Carvão ativado regenerado', (0.5, 0.69), '#E8F0FE'),
    ('Dessecante (CaCl₂ / Sílica)', (0.5, 0.56), '#FFF3E0'),
    ('Secagem térmica (105–120°C)', (0.5, 0.43), '#FFF3E0'),
    ('Reutilização cíclica', (0.5, 0.30), '#E8F5E9'),
]
for label, (x, y), color in steps:
    ax.text(x, y, label, fontsize=11, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=color, edgecolor='#333', linewidth=1.5))
for i in range(len(steps)-1):
    x, y = steps[i][1]
    x2, y2 = steps[i+1][1]
    ax.annotate('', xy=(x2, y2-0.05), xytext=(x, y-0.05),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
ax.annotate('', xy=(0.82, 0.30), xytext=(0.5, 0.30),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
ax.text(0.82, 0.36, 'Retorno ao processo', fontsize=9, ha='center')
ax.set_title('Fluxograma — Ciclo de Reciclagem Química', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'fluxograma_reciclagem.png'), dpi=150)
plt.close()

# 5. Fluxograma do sistema de energia dual
fig, ax = plt.subplots(figsize=(8, 8))
ax.axis('off')
nodes = [
    ('Tomada 110/220V', (0.2, 0.95), '#FFF3E0'),
    ('Carregador AC 12V', (0.2, 0.82), '#FFF3E0'),
    ('Bateria 12V 60Ah', (0.2, 0.69), '#FFF3E0'),
    ('Controlador MPPT/PWM', (0.2, 0.56), '#FFF3E0'),
    ('Conversor Buck 12V→5V', (0.2, 0.43), '#FFF3E0'),
    ('Arduino Mega + Sensores', (0.55, 0.43), '#E8F5E9'),
    ('Atuadores (Fan, Bomba, Aquecedor)', (0.55, 0.30), '#FCE4EC'),
    ('App Mobile / Dashboard', (0.85, 0.43), '#E1F5FE'),
]
for label, (x, y), color in nodes:
    ax.text(x, y, label, fontsize=10, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=color, edgecolor='#333', linewidth=1.5))
edges = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (5, 7)
]
for i, j in edges:
    x1, y1 = nodes[i][1]
    x2, y2 = nodes[j][1]
    ax.annotate('', xy=(x2, y2+0.05), xytext=(x1, y1-0.05),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
ax.set_title('Fluxograma — Sistema de Energia Dual Power', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'fluxograma_energia_dual.png'), dpi=150)
plt.close()

print('Imagens e diagramas gerados.')
