// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — GUI nativa em Qt5 Widgets (tupan_gui)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: este é o aplicativo desktop "bonito e significativo" do projeto:
//    • Sliders de ambiente (UR, T, vazão, eficiência, serpentina);
//    • Tabela da frota de Tupans (adicionar/remover/ciclo);
//    • Monte Carlo PARALELO (std::jthread no núcleo) com painel p05/p50/p95;
//    • Previsão do modelo de ML e métricas R²/RMSE;
//    • "Prestação de contas ambiental": energia estimada por litro (L/kWh).
//  A GUI é 100% C++: ela consome tupan_core.hpp (mesma física do CLI/pybind)
//  e pode carregar dados exportados pela esteira Python/HF (CSV -> JSON).
// ============================================================================
#include "tupan_core.hpp"
#include "tupan_room.hpp"

#include <QApplication>
#include <QCheckBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QLineEdit>
#include <QMainWindow>
#include <QMessageBox>
#include <QPushButton>
#include <QSpinBox>
#include <QTableWidget>
#include <QVBoxLayout>

#include <memory>

namespace {

// ---------------------------------------------------------------------------
// Utilitário didático: converte um Snapshot do núcleo para JSON (interoperável
// com a saída do CLI e com a esteira de dados Python).
// ---------------------------------------------------------------------------
[[nodiscard]] QJsonObject mcToJson(const tupan::MonteCarloStats& s, double hours, double ml) {
    QJsonObject o;
    o["horas"] = hours;
    o["mc_media"] = s.mean;
    o["mc_p05"] = s.p05;
    o["mc_p50"] = s.p50;
    o["mc_p95"] = s.p95;
    o["ml"] = ml;
    return o;
}

} // namespace

// ---------------------------------------------------------------------------
// MainWindow — janela principal (OOP: herança de QMainWindow).
// ---------------------------------------------------------------------------
class TupanWindow final : public QMainWindow {
    Q_OBJECT
public:
    explicit TupanWindow(QWidget* parent = nullptr) : QMainWindow(parent) {
        setWindowTitle("Tupan, Máquina de Chuva — Simulador Nativo");
        resize(980, 640);

        auto* central = new QWidget(this);
        auto* root = new QVBoxLayout(central);

        // ---------------- Painel de ambiente ----------------
        auto* gbAmb = new QGroupBox("Ambiente (condições climáticas)", central);
        auto* form  = new QFormLayout(gbAmb);

        // DIDÁTICA: cada QDoubleSpinBox limita o domínio físico do parâmetro.
        ur_    = makeSpin(0.0, 100.0, 65.0, " %", form, "Umidade relativa (noite)");
        temp_  = makeSpin(-5.0, 55.0, 24.0, " °C", form, "Temperatura noturna");
        fluxo_ = makeSpin(0.0, 80.0, 25.0, " m³/h", form, "Vazão das ventoinhas");
        aquec_ = makeSpin(80.0, 180.0, 120.0, " °C", form, "Temperatura do aquecedor (dia)");
        efic_  = makeSpin(0.0, 1.0, 0.85, "", form, "Eficiência do leito (0-1)");
        noite_ = makeSpin(1.0, 14.0, 8.0, " h", form, "Horas de sorção (noite)");
        dia_   = makeSpin(1.0, 12.0, 6.0, " h", form, "Horas de destilação (dia)");

        root->addWidget(gbAmb);

        // ---------------- Sala animada (dispositivo em movimento) ----------------
        auto* gbSala = new QGroupBox("Sala do dispositivo — visualização do ciclo", central);
        auto* laySala = new QHBoxLayout(gbSala);
        sala_ = new RoomWidget(gbSala);
        sala_->setMinimumHeight(260);
        sala_->setHeaterWatts(tupan::constants().heater_watts);
        laySala->addWidget(sala_, 1);
        auto* colSala = new QVBoxLayout();
        chkBlueprint_ = new QCheckBox("Modo blueprint (corte técnico)", gbSala);
        chkDia_       = new QCheckBox("Fase diurna (regeneração + destilação)", gbSala);
        colSala->addWidget(chkBlueprint_);
        colSala->addWidget(chkDia_);
        colSala->addStretch(1);
        laySala->addLayout(colSala);
        connect(chkBlueprint_, &QCheckBox::toggled, this, [this](bool on) {
            sala_->setMode(on ? RoomWidget::Mode::Blueprint
                              : (chkDia_->isChecked() ? RoomWidget::Mode::Day
                                                      : RoomWidget::Mode::Night));
        });
        connect(chkDia_, &QCheckBox::toggled, this, [this](bool on) {
            if (!chkBlueprint_->isChecked())
                sala_->setMode(on ? RoomWidget::Mode::Day : RoomWidget::Mode::Night);
        });
        root->addWidget(gbSala);

        // ---------------- Frota ----------------
        auto* gbFrota = new QGroupBox("Frota de dispositivos", central);
        auto* layF = new QHBoxLayout(gbFrota);
        tabela_ = new QTableWidget(0, 4, gbFrota);
        tabela_->setHorizontalHeaderLabels({"ID", "Produção (L)", "Status", "ML (L)"});
        tabela_->horizontalHeader()->setStretchLastSection(true);
        tabela_->setMinimumHeight(160);
        layF->addWidget(tabela_, 4);

        auto* colF = new QVBoxLayout();
        btnAdd_    = new QPushButton("Adicionar Tupan", gbFrota);
        btnRemove_ = new QPushButton("Remover selecionado", gbFrota);
        btnCiclo_  = new QPushButton("Rodar ciclo", gbFrota);
        colF->addWidget(btnAdd_);
        colF->addWidget(btnRemove_);
        colF->addWidget(btnCiclo_);
        colF->addStretch(1);
        layF->addLayout(colF, 2);
        root->addWidget(gbFrota);

        // ---------------- Análise ----------------
        auto* gbMC = new QGroupBox("Análise estatística e ML", central);
        auto* formMC = new QFormLayout(gbMC);
        runs_ = new QSpinBox(gbMC);
        runs_->setRange(1000, 1'000'000);
        runs_->setValue(50'000);
        runs_->setGroupSeparatorShown(true);
        formMC->addRow("Corridas Monte Carlo (paralelo):", runs_);

        lblMC_   = new QLabel("—", gbMC);
        lblML_   = new QLabel("—", gbMC);
        lblAmb_  = new QLabel("—", gbMC);
        lblEnerg_= new QLabel("—", gbMC);
        formMC->addRow("Monte Carlo (média/p05/p50/p95):", lblMC_);
        formMC->addRow("Previsão ML (grau 2):", lblML_);
        formMC->addRow("Modelo físico (teórico):", lblAmb_);
        formMC->addRow("Prestação de contas ambiental:", lblEnerg_);
        root->addWidget(gbMC);

        auto* rowBtns = new QHBoxLayout();
        btnMC_      = new QPushButton("Rodar Monte Carlo", central);
        btnExport_  = new QPushButton("Exportar JSON", central);
        rowBtns->addWidget(btnMC_);
        rowBtns->addWidget(btnExport_);
        rowBtns->addStretch(1);
        root->addLayout(rowBtns);

        setCentralWidget(central);

        // ---------------- Conexões sinal→slot ----------------
        connect(btnAdd_,    &QPushButton::clicked, this, &TupanWindow::onAdd);
        connect(btnRemove_, &QPushButton::clicked, this, &TupanWindow::onRemove);
        connect(btnCiclo_,  &QPushButton::clicked, this, &TupanWindow::onCycle);
        connect(btnMC_,     &QPushButton::clicked, this, &TupanWindow::onMonteCarlo);
        connect(btnExport_, &QPushButton::clicked, this, &TupanWindow::onExport);
    }

private slots:
    // Adiciona um Tupan à frota e reflete na tabela.
    void onAdd() {
        const int id = sim_.add_tupan();
        const int r = tabela_->rowCount();
        tabela_->insertRow(r);
        tabela_->setItem(r, 0, new QTableWidgetItem(QString::number(id)));
        tabela_->setItem(r, 1, new QTableWidgetItem("—"));
        tabela_->setItem(r, 2, new QTableWidgetItem("online"));
        tabela_->setItem(r, 3, new QTableWidgetItem("—"));
    }

    // Remove a unidade selecionada (se houver).
    void onRemove() {
        const auto sel = tabela_->currentRow();
        if (sel < 0) return;
        const int id = tabela_->item(sel, 0)->text().toInt();
        sim_.remove_tupan(id);
        tabela_->removeRow(sel);
    }

    // Roda um ciclo determinístico para a frota inteira.
    void onCycle() {
        syncEnv();
        const auto res = sim_.run_cycle(noite_->value(), dia_->value(), 42ULL);
        for (const auto& r : res) {
            for (int row = 0; row < tabela_->rowCount(); ++row) {
                if (tabela_->item(row, 0)->text().toInt() == r.tupan_id) {
                    tabela_->item(row, 1)->setText(QString::number(r.output_liters, 'f', 4));
                    tabela_->item(row, 2)->setText(QString::fromStdString(r.status));
                    tabela_->item(row, 3)->setText(
                        QString::number(sim_.predict_output(r.tupan_id, noite_->value(), dia_->value()), 'f', 4));
                }
            }
        }
        refreshTeoria();
        refreshSala();
    }

    // Monte Carlo paralelo (executa no núcleo com std::jthread).
    void onMonteCarlo() {
        syncEnv();
        const auto mc = sim_.monte_carlo(runs_->value(), noite_->value(), dia_->value(), 42ULL);
        const int id = sim_.count() > 0 ? sim_.units().front().id : sim_.add_tupan();
        const double ml = sim_.predict_output(id, noite_->value(), dia_->value());
        lblMC_->setText(QString("%1 / %2 / %3 / %4 L")
                            .arg(mc.mean, 0, 'f', 3).arg(mc.p05, 0, 'f', 3)
                            .arg(mc.p50, 0, 'f', 3).arg(mc.p95, 0, 'f', 3));
        lblML_->setText(QString::number(ml, 'f', 4) + " L");
        double rmse = 0.0, r2 = 0.0;
        sim_.ml_accuracy(rmse, r2);
        lblML_->setToolTip(QString("RMSE %1 | R² %2").arg(rmse, 0, 'f', 4).arg(r2, 0, 'f', 4));
        refreshTeoria();
        refreshSala();
    }

    // Exporta o estado atual em JSON (mesma forma do CLI --json).
    void onExport() {
        syncEnv();
        const auto mc = sim_.monte_carlo(runs_->value(), noite_->value(), dia_->value(), 42ULL);
        const double ml = sim_.count() ? sim_.predict_output(sim_.units().front().id, noite_->value(), dia_->value()) : 0.0;
        const QJsonDocument doc(mcToJson(mc, noite_->value(), ml));
        QMessageBox::information(this, "JSON do estado", QString::fromUtf8(doc.toJson(QJsonDocument::Indented)));
    }

private:
    // Fábrica de spinboxes com sufixo de unidade — menos duplicação na UI.
    [[nodiscard]] QDoubleSpinBox* makeSpin(double lo, double hi, double v,
                                           const QString& suffix, QFormLayout* f,
                                           const QString& label) {
        auto* s = new QDoubleSpinBox(this);
        s->setRange(lo, hi);
        s->setValue(v);
        s->setDecimals(2);
        s->setSingleStep(0.25);
        s->setSuffix(suffix);
        f->addRow(label, s);
        return s;
    }

    // Copia a UI -> núcleo (single source of truth do estado físico).
    void syncEnv() {
        auto& e = sim_.env();
        e.relative_humidity = ur_->value();
        e.temperature       = temp_->value();
        e.fan_flow          = fluxo_->value();
        e.efficiency        = efic_->value();
        e.heater_temp_c     = aquec_->value();
    }

    // Espelha o estado do núcleo na sala animada (partículas/nível/etapa).
    void refreshSala() {
        const auto& e = sim_.env();
        const auto cb = tupan::full_cycle(noite_->value(), dia_->value(), e.relative_humidity,
                                          e.temperature, e.fan_flow, e.efficiency,
                                          e.heater_temp_c);
        sala_->setState(e.relative_humidity,
                        e.heater_temp_c / 180.0,                 // fração de potência visual
                        cb.distilled_l, 2.0);                    // litros reais no tanque
        sala_->setTankLiters(cb.distilled_l);
    }

    // Teoria + contas ambientais (L/kWh): ventoinhas (noite) + aquecedor (dia).
    void refreshTeoria() {
        const auto& e = sim_.env();
        const auto cb = tupan::full_cycle(noite_->value(), dia_->value(), e.relative_humidity,
                                          e.temperature, e.fan_flow, e.efficiency,
                                          e.heater_temp_c);
        lblAmb_->setText(QString("%1 kg sorvidos · %2 L destilados")
                             .arg(cb.water_kg_sorbed, 0, 'f', 3)
                             .arg(cb.distilled_l, 0, 'f', 4));

        const double kwh = cb.energy_kj_total / 3.6e6;
        lblEnerg_->setText(QString("%1 kWh/ciclo · %2 L/kWh")
                               .arg(kwh, 0, 'f', 3)
                               .arg(cb.liters_per_kwh, 0, 'f', 2));
    }

    // ---- Estado / núcleo ----
    tupan::Simulator sim_;

    // ---- Widgets ----
    QDoubleSpinBox* ur_ = nullptr;
    QDoubleSpinBox* temp_ = nullptr;
    QDoubleSpinBox* fluxo_ = nullptr;
    QDoubleSpinBox* noite_ = nullptr;
    QDoubleSpinBox* dia_ = nullptr;
    QDoubleSpinBox* aquec_ = nullptr;
    QDoubleSpinBox* efic_ = nullptr;
    QSpinBox* runs_ = nullptr;
    QTableWidget* tabela_ = nullptr;
    QPushButton* btnAdd_ = nullptr;
    QPushButton* btnRemove_ = nullptr;
    QPushButton* btnCiclo_ = nullptr;
    QPushButton* btnMC_ = nullptr;
    QPushButton* btnExport_ = nullptr;
    QLabel* lblMC_ = nullptr;
    QLabel* lblML_ = nullptr;
    QLabel* lblAmb_ = nullptr;
    QLabel* lblEnerg_ = nullptr;
    RoomWidget* sala_ = nullptr;
    QCheckBox* chkBlueprint_ = nullptr;
    QCheckBox* chkDia_ = nullptr;
};

#include "tupan_gui.moc"

int main(int argc, char** argv) {
    QApplication app(argc, argv);
    app.setApplicationName("Tupan, Máquina de Chuva — Simulador Nativo");
    TupanWindow w;
    w.show();
    return app.exec();
}
