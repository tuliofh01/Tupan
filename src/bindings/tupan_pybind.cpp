// ============================================================================
//  TUPAN, MÁQUINA DE CHUVA — Módulo Python nativo via pybind11 (tupan_native)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: pybind11 expõe as classes C++ ao Python. API espelha o novo ciclo:
//      from tupan_native import Simulator
//      s = Simulator(); s.add_tupan(); s.run_cycle(night_hours=8, day_hours=6)
//  MEMÓRIA: todo dado cruza a fronteira como tipos fixos (double/int32).
// ============================================================================
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "tupan_core.hpp"

namespace py = pybind11;

PYBIND11_MODULE(tupan_native, m) {
    m.doc() = "Núcleo nativo do simulador Tupan, Máquina de Chuva (C++23/pybind11)";

    py::class_<tupan::Environment>(m, "Environment")
        .def(py::init<>())
        .def_readwrite("relative_humidity", &tupan::Environment::relative_humidity)
        .def_readwrite("temperature",       &tupan::Environment::temperature)
        .def_readwrite("pressure",          &tupan::Environment::pressure)
        .def_readwrite("fan_flow",          &tupan::Environment::fan_flow)
        .def_readwrite("efficiency",        &tupan::Environment::efficiency)
        .def_readwrite("heater_temp_c",     &tupan::Environment::heater_temp_c);

    py::class_<tupan::CycleBreakdown>(m, "CycleBreakdown")
        .def(py::init<>())
        .def_readonly("water_kg_sorbed", &tupan::CycleBreakdown::water_kg_sorbed)
        .def_readonly("distilled_l",     &tupan::CycleBreakdown::distilled_l)
        .def_readonly("potable_l",       &tupan::CycleBreakdown::potable_l)
        .def_readonly("ca_mg_l",         &tupan::CycleBreakdown::ca_mg_l)
        .def_readonly("mg_mg_l",         &tupan::CycleBreakdown::mg_mg_l)
        .def_readonly("basin_full",      &tupan::CycleBreakdown::basin_full)
        .def_readonly("energy_kj_total", &tupan::CycleBreakdown::energy_kj_total)
        .def_readonly("liters_per_kwh",  &tupan::CycleBreakdown::liters_per_kwh);

    py::class_<tupan::PostTreatment>(m, "PostTreatment")
        .def(py::init<>())
        .def_readonly("water_l",     &tupan::PostTreatment::water_l)
        .def_readonly("ca_mg_l",     &tupan::PostTreatment::ca_mg_l)
        .def_readonly("mg_mg_l",     &tupan::PostTreatment::mg_mg_l)
        .def_readonly("uv_energy_j", &tupan::PostTreatment::uv_energy_j)
        .def_readonly("basin_full",  &tupan::PostTreatment::basin_full);

    py::class_<tupan::Simulator::CycleResult>(m, "CycleResult")
        .def(py::init<>())
        .def_readonly("tupan_id",      &tupan::Simulator::CycleResult::tupan_id)
        .def_readonly("output_liters", &tupan::Simulator::CycleResult::output_liters)
        .def_readonly("status",        &tupan::Simulator::CycleResult::status);

    py::class_<tupan::MonteCarloStats>(m, "MonteCarloStats")
        .def(py::init<>())
        .def_readonly("mean", &tupan::MonteCarloStats::mean)
        .def_readonly("p05",  &tupan::MonteCarloStats::p05)
        .def_readonly("p50",  &tupan::MonteCarloStats::p50)
        .def_readonly("p95",  &tupan::MonteCarloStats::p95);

    // DIDÁTICA: enum class precisa de py::enum_ p/ virar enum Python real.
    py::enum_<tupan::LogLevel>(m, "LogLevel")
        .value("INFO",    tupan::LogLevel::INFO)
        .value("WARN",    tupan::LogLevel::WARN)
        .value("ERROR",   tupan::LogLevel::ERROR)
        .value("ROUTINE", tupan::LogLevel::ROUTINE)
        .export_values();

    py::class_<tupan::Simulator>(m, "Simulator")
        .def(py::init<>())
        .def("add_tupan", &tupan::Simulator::add_tupan, "Registra um Tupan; devolve id")
        .def("remove_tupan", &tupan::Simulator::remove_tupan, py::arg("tupan_id"))
        .def("count", &tupan::Simulator::count)
        .def("env", py::overload_cast<>(&tupan::Simulator::env),
             py::return_value_policy::reference_internal)
        .def("run_cycle", &tupan::Simulator::run_cycle,
             py::arg("night_hours") = 8.0, py::arg("day_hours") = 6.0, py::arg("seed") = 0,
             "Executa ciclo completo (sorção noturna + destilação diurna)")
        .def("monte_carlo", &tupan::Simulator::monte_carlo,
             py::arg("runs"), py::arg("night_hours") = 8.0, py::arg("day_hours") = 6.0,
             py::arg("seed") = 0, "Monte Carlo paralelo com percentis")
        .def("predict_output", &tupan::Simulator::predict_output,
             py::arg("tupan_id"), py::arg("night_hours") = 8.0, py::arg("day_hours") = 6.0)
        .def("ml_accuracy", [](const tupan::Simulator& s) {
                 double rmse = 0.0, r2 = 0.0;
                 s.ml_accuracy(rmse, r2);
                 return py::make_tuple(rmse, r2);
             }, "Devolve (rmse, r2) do modelo de ML")
        .def("attach_logger", &tupan::Simulator::attach_logger, py::arg("path"),
             "Anexa binlog não-crítico (rotinas/erros)")
        .def("log", &tupan::Simulator::blog, py::arg("level"), py::arg("tag"), py::arg("msg"),
             "Escreve no binlog (0=INFO 1=WARN 2=ERROR 3=ROUTINE)");

    m.def("full_cycle", &tupan::full_cycle, py::arg("night_hours"), py::arg("day_hours"),
          py::arg("humidity"), py::arg("temperature"), py::arg("fan_flow"),
          py::arg("efficiency"), py::arg("heater_temp_c"),
          "Ciclo completo determinístico (sorção + destilação)");
    m.def("sorption_intake", &tupan::sorption_intake, "Água sorvida no leito (kg)");
    m.def("distillation_output", &tupan::distillation_output, "Água destilada na vidraria (L)");
    m.def("post_treatment", &tupan::post_treatment, py::arg("distilled_l"),
          "Pós-tratamento: filtro mineralizante + UV-C → bacia (L potáveis)");
    m.def("saturation_vapor_density", &tupan::saturation_vapor_density,
          "Densidade de vapor saturado (g/m³) — Magnus");
}
