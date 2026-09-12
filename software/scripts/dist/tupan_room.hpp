// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Sala animada (RoomWidget, Qt5 QPainter)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: o widget desenha o dispositivo em corte dentro de uma sala e
//  ANIMA A FÍSICA REAL do núcleo (tupan_core.hpp):
//    • modo SORÇÃO (noite): partículas azuis de ar úmido entram, tornam-se
//      claras (secas) ao cruzar o leito químico; nível de água é estático;
//    • modo REGEN/DISTILAÇÃO (dia): o aquecedor fica vermelho, o vapor
//      (partículas brancas) sobe do leito e condensa na vidraria; o nível do
//      reservatório sobe conforme os LITROS produzidos (dados do núcleo);
//    • modo BLUEPRINT: traço técnico único (corte tipo desenho de engenharia).
//  A animação é determinística-ish (sem física caótica): partículas seguem
//  caminhos com fase própria; velocidade ∝ potência/fluxo reais do núcleo.
// ============================================================================
#pragma once
#include "tupan_core.hpp"

#include <QColor>
#include <QPainter>
#include <QPainterPath>
#include <QPaintEvent>
#include <QTimer>
#include <QWidget>

#include <array>
#include <cmath>

// ---------------------------------------------------------------------------
// Partícula — UNIDADE VISUAL mínima (memória fixa: 2 floats + fases).
// ---------------------------------------------------------------------------
struct Particle {
    float x = 0.0f, y = 0.0f;     // posição normalizada (0..1 no widget)
    float phase = 0.0f;           // fase do ciclo da partícula (0..1)
    float speed = 1.0f;           // multiplicador individual
    float jitter = 0.0f;          // desvio lateral senoidal
    std::uint8_t state = 0;       // 0=ar úmido 1=ar seco 2=vapor 3=água destilada
};

class RoomWidget final : public QWidget {
    Q_OBJECT
public:
    enum class Mode { Night, Day, Blueprint };

    explicit RoomWidget(QWidget* parent = nullptr) : QWidget(parent) {
        // 64 partículas fixas — std::array: zero heap, layout contíguo (cache).
        for (std::size_t i = 0; i < kParticles; ++i) {
            auto& p = particles_[i];
            p.x = static_cast<float>(tupan::uniform01(rng_));
            p.y = 0.15f + 0.7f * static_cast<float>(tupan::uniform01(rng_));
            p.phase = static_cast<float>(tupan::uniform01(rng_));
            p.speed = 0.6f + 0.8f * static_cast<float>(tupan::uniform01(rng_));
            p.jitter = static_cast<float>(tupan::uniform01(rng_)) * 6.2831853f;
            p.state = 0;
        }
        // Timer de animação: 33 ms ≈ 30 FPS (suave e barato em CPU).
        connect(&timer_, &QTimer::timeout, this, [this] { ++tick_; update(); });
        timer_.start(33);
    }

    // Injeta o estado FÍSICO do núcleo (chamado pela janela após cada cálculo).
    void setState(tupan::Real umidade, tupan::Real potenciaLeito, tupan::Real litrosNoTanque,
                  tupan::Real litrosMax = 2.0) {
        humidity_ = umidade;
        power_ = potenciaLeito;          // 0..1 (fração de potência do estágio)
        tankLevel_ = static_cast<float>(std::min(1.0, litrosNoTanque / litrosMax));
    }
    void setMode(Mode m) { mode_ = m; update(); }

protected:
    void paintEvent(QPaintEvent*) override {
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing);
        const QRectF area = rect();

        // Fundo: gradiente dia/noite (azul-noite vs. céu-dia) ou blueprint.
        if (mode_ == Mode::Blueprint) {
            p.fillRect(area, QColor(12, 18, 28));
        } else if (mode_ == Mode::Night) {
            QLinearGradient g(0, 0, 0, height());
            g.setColorAt(0.0, QColor(16, 24, 46));
            g.setColorAt(1.0, QColor(30, 44, 72));
            p.fillRect(area, g);
        } else {
            QLinearGradient g(0, 0, 0, height());
            g.setColorAt(0.0, QColor(235, 244, 252));
            g.setColorAt(1.0, QColor(206, 226, 244));
            p.fillRect(area, g);
        }

        // Dimensões da "sala" (margens proporcionais).
        const qreal mx = width() * 0.06, my = height() * 0.08;
        const QRectF room(mx, my, width() - 2 * mx, height() - 2 * my);

        drawRoom(p, room);
        drawDevice(p, room);
        drawParticles(p, room);
        drawLabels(p, room);
    }

private:
    // -----------------------------------------------------------------------
    // GEOMETRIA DO DISPOSITIVO (em frações da sala) — corte lateral:
    //   [ventoinhas]→ [leito químico] → [cúpula/vidraria + aquecedor] → [reservatório]
    // -----------------------------------------------------------------------
    struct Geometry {
        QRectF room;
        QRectF fans;      // entrada de ar
        QRectF bed;       // leito CaCl₂
        QRectF dome;      // cúpula de destilação (vidraria)
        QRectF heater;    // bobina
        QRectF tank;      // reservatório
        QRectF flask;     // vidraria (erlenmeyer estilizado)
    };

    [[nodiscard]] Geometry geo(const QRectF& room) const {
        Geometry g;
        g.room  = room;
        const qreal w = room.width(), h = room.height();
        g.fans   = {room.left() + 0.02 * w, room.top() + 0.30 * h, 0.10 * w, 0.34 * h};
        g.bed    = {room.left() + 0.16 * w, room.top() + 0.28 * h, 0.22 * w, 0.38 * h};
        g.dome   = {room.left() + 0.44 * w, room.top() + 0.10 * h, 0.28 * w, 0.56 * h};
        g.flask  = {room.left() + 0.50 * w, room.top() + 0.44 * h, 0.16 * w, 0.20 * h};
        g.heater = {room.left() + 0.49 * w, room.top() + 0.64 * h, 0.18 * w, 0.045 * h};
        g.tank   = {room.left() + 0.78 * w, room.top() + 0.52 * h, 0.18 * w, 0.34 * h};
        return g;
    }

    void drawRoom(QPainter& p, const QRectF& room) {
        p.setPen(QPen(mode_ == Mode::Blueprint ? QColor(90, 160, 220) : QColor(80, 90, 105),
                      2, Qt::DashLine));
        p.drawRect(room.adjusted(0, 0, -1, -1));
        // Piso (linha dupla = piso técnico).
        p.setPen(QPen(QColor(80, 90, 105), 3));
        p.drawLine(QPointF(room.left(), room.bottom() - 1), QPointF(room.right() - 1, room.bottom() - 1));
    }

    // -----------------------------------------------------------------------
    // DISPOSITIVO — cores e traço mudam por modo; aquecedor "esquenta" com potência.
    // -----------------------------------------------------------------------
    void drawDevice(QPainter& p, const QRectF& room) {
        const Geometry g = geo(room);
        const bool bp = (mode_ == Mode::Blueprint);
        const QColor ink   = bp ? QColor(120, 190, 255) : QColor(40, 50, 62);
        const QColor bed   = bp ? QColor(70, 130, 190)  : QColor(46, 125, 50);
        const QColor glass = bp ? QColor(90, 150, 210)  : QColor(160, 200, 235);
        const QColor tankc = bp ? QColor(90, 150, 210)  : QColor(21, 101, 192);

        // Ventoinhas (3 pás girando — ângulo ∝ tick e potência).
        p.setPen(QPen(ink, 2));
        p.setBrush(bp ? Qt::NoBrush : QColor(225, 232, 240));
        p.drawRoundedRect(g.fans, 6, 6);
        const qreal cx = g.fans.center().x(), cy = g.fans.center().y();
        const qreal r = std::min(g.fans.width(), g.fans.height()) * 0.32;
        const qreal ang = tick_ * (0.15 + 0.25 * power_) * 0.6;
        for (int i = 0; i < 3; ++i) {
            const qreal a = ang + i * 2.0943951; // 120°
            QPolygonF blade;
            blade << QPointF(cx, cy)
                  << QPointF(cx + r * std::cos(a), cy + r * std::sin(a))
                  << QPointF(cx + r * std::cos(a + 0.9), cy + r * std::sin(a + 0.9));
            p.setBrush(bp ? Qt::NoBrush : QColor(120, 144, 168));
            p.drawPolygon(blade);
        }

        // Leito químico: retângulo com "grãos" (hachura leve).
        p.setPen(QPen(ink, 2));
        p.setBrush(bp ? Qt::NoBrush : QColor(200, 228, 205));
        p.drawRoundedRect(g.bed, 8, 8);
        p.setPen(QPen(bed, 1, Qt::DotLine));
        for (int i = 1; i < 5; ++i) {
            const qreal y = g.bed.top() + g.bed.height() * i / 5.0;
            p.drawLine(QPointF(g.bed.left() + 3, y), QPointF(g.bed.right() - 3, y));
        }

        // Cúpula de vidraria (arco) + erlenmeyer.
        p.setPen(QPen(glass, 3));
        p.setBrush(bp ? Qt::NoBrush : QColor(245, 250, 253, 180));
        p.drawEllipse(g.dome);
        p.drawEllipse(g.flask);

        // Aquecedor (bobina): vermelho ∝ potência; pulsa no modo dia.
        const int heat = bp ? 90 : static_cast<int>(120 + 135 * power_);
        p.setPen(QPen(QColor(heat, 40, 30), 4, Qt::SolidLine, Qt::RoundCap));
        QPainterPath coil;
        const qreal n = 5.0;
        for (int i = 0; i <= 24; ++i) {
            const qreal t = i / 24.0;
            const qreal x = g.heater.left() + g.heater.width() * t;
            const qreal y = g.heater.center().y() + std::sin(t * n * 3.14159) * g.heater.height() * 0.45;
            (i == 0) ? coil.moveTo(x, y) : coil.lineTo(x, y);
        }
        p.drawPath(coil);

        // Reservatório com nível animado (proporcional aos litros reais).
        p.setPen(QPen(ink, 2));
        p.setBrush(Qt::NoBrush);
        p.drawRoundedRect(g.tank, 6, 6);
        const qreal lvlH = g.tank.height() * tankLevel_;
        QRectF water(g.tank.left() + 2, g.tank.bottom() - lvlH - 2, g.tank.width() - 4, lvlH);
        p.setBrush(bp ? Qt::NoBrush : QColor(30, 136, 229, 170));
        p.drawRect(water);
    }

    // -----------------------------------------------------------------------
    // PARTÍCULAS — a alma da animação. Fase avança ∝ velocidade e potência;
    // cada estado tem cor; trajetórias dependem do modo (noite/dia).
    // -----------------------------------------------------------------------
    void drawParticles(QPainter& p, const QRectF& room) {
        const Geometry g = geo(room);
        const bool night = (mode_ == Mode::Night);
        const bool bp = (mode_ == Mode::Blueprint);

        for (auto& q : particles_) {
            // Avanço de fase: noite suga p/ direita; dia sobe vapor do leito.
            const float v = (0.004f + 0.012f * power_) * q.speed;
            q.phase += v;
            if (q.phase > 1.0f) { q.phase -= 1.0f; respawn(q, night); }

            const qreal t = q.phase;
            QPointF pos;
            QColor col;

            if (night) {
                // SORÇÃO: da entrada (fans) → leito → (some = retida).
                const qreal x0 = g.fans.center().x(), x1 = g.bed.center().x();
                pos = {x0 + (x1 - x0) * t,
                       q.y * g.fans.bottom() + (g.bed.center().y() - q.y * g.fans.bottom()) * t
                           + std::sin(t * 6.0 + q.jitter) * 8.0};
                // Mudança de cor: úmido (azul) → seco (claro) ao entrar no leito.
                const bool dentroLeito = (t > 0.55);
                col = dentroLeito ? QColor(200, 224, 240) : QColor(64, 140, 220);
                col.setAlphaF(0.85 * (1.0 - 0.7 * t));
                q.state = dentroLeito ? 1 : 0;
            } else {
                // REGEN: do leito/aquecedor → cúpula → vidraria (condensa).
                const qreal y0 = g.heater.top(), y1 = g.dome.top();
                pos = {g.dome.center().x() + std::sin(t * 4.0 + q.jitter) * (0.12 * g.dome.width()),
                       y0 + (y1 - y0) * t};
                col = QColor(250, 250, 250);
                col.setAlphaF(0.75 * (1.0 - t));
                q.state = 2;
            }
            if (bp) col = QColor(140, 200, 255, col.alpha());

            p.setPen(Qt::NoPen);
            p.setBrush(col);
            p.drawEllipse(pos, 2.4, 2.4);
        }
    }

    // Reposiciona a partícula reciclada (determinístico via rng do tick).
    void respawn(Particle& q, bool night) {
        q.y = 0.15f + 0.7f * static_cast<float>(tupan::uniform01(rng_));
        q.jitter = static_cast<float>(tupan::uniform01(rng_)) * 6.2831853f;
        q.state = night ? 0u : 2u;
    }

    // Rótulos técnicos (PT-BR) + leituras vivas do núcleo.
    void drawLabels(QPainter& p, const QRectF& room) {
        const Geometry g = geo(room);
        p.setPen(QPen(mode_ == Mode::Blueprint ? QColor(140, 200, 255) : QColor(30, 40, 52)));
        QFont f = font(); f.setPointSize(9); p.setFont(f);

        p.drawText(QPointF(g.fans.left(), g.fans.top() - 6), "Ventoinhas");
        p.drawText(QPointF(g.bed.left(), g.bed.top() - 6),
                   QString("Leito CaCl₂ (%1 %)").arg(QString::number(humidity_, 'f', 0)));
        p.drawText(QPointF(g.dome.left(), g.dome.top() - 6), "Cúpula / Vidraria");
        p.drawText(QPointF(g.heater.left(), g.heater.bottom() + 14),
                   QString("Aquecedor %1 W").arg(QString::number(heaterW_, 'f', 0)));
        p.drawText(QPointF(g.tank.left(), g.tank.top() - 6),
                   QString("Reservatório %1 L").arg(QString::number(tankLiters_, 'f', 2)));
    }

    // ---- Estado visual ----
    static constexpr std::size_t kParticles = 64;
    std::array<Particle, kParticles> particles_{};
    QTimer timer_;
    std::uint32_t tick_ = 0;
    tupan::Seed rng_ = 20260912ULL;

    tupan::Real humidity_ = 60.0;
    tupan::Real power_ = 0.5;       // 0..1
    tupan::Real heaterW_ = 250.0;
    tupan::Real tankLiters_ = 0.0;
    float tankLevel_ = 0.0f;
    Mode mode_ = Mode::Night;

public:
    // Ajustes adicionais vindos da janela principal.
    void setHeaterWatts(tupan::Real w) { heaterW_ = w; }
    void setTankLiters(tupan::Real l)  { tankLiters_ = l; tankLevel_ = static_cast<float>(std::min(1.0, l / 2.0)); }
};
