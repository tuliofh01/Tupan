// ============================================================================
//  TUPAN STUDIO — Aplicativo interativo (Lua DSL + Dear ImGui + OpenGL)
//  ---------------------------------------------------------------------------
//  A janela hospeda:
//    • menus e painéis definidos em assets/studio.lua (DSL com cara de JSON);
//    • uma cena 3D do dispositivo desenhada em OpenGL 3.3 (scene.cpp);
//    • a física real do núcleo C++23 (tupan_core.hpp) ligada aos sliders.
//  Substitui a antiga GUI Qt5: sem Qt, com UI trocável em tempo de execução.
// ============================================================================
#include "lua_dsl.hpp"
#include "scene.hpp"

#include "tupan_core.hpp"

#include <GL/glew.h>
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <functional>
#include <map>
#include <string>
#include <unordered_map>

#ifndef TUPAN_STUDIO_DSL
#define TUPAN_STUDIO_DSL "studio.lua"
#endif

namespace {

using tupan::studio::ControlType;
using tupan::studio::Mode;
using tupan::studio::SimState;
using tupan::studio::StudioConfig;

void glfwErrorCallback(int code, const char* desc) {
    std::fprintf(stderr, "[GLFW] erro %d: %s\n", code, desc);
}

void applyTheme(const tupan::studio::Theme& t) {
    ImGuiStyle& s = ImGui::GetStyle();
    ImGui::StyleColorsDark();
    s.WindowRounding = 8.0F;
    s.FrameRounding = 5.0F;
    s.GrabRounding = 5.0F;
    auto col = [](ImVec4 c, float a = 1.0F) { return ImVec4(c.x, c.y, c.z, a); };
    const ImVec4 accent(t.accent.r, t.accent.g, t.accent.b, 1.0F);
    const ImVec4 panel(t.panel.r, t.panel.g, t.panel.b, 0.94F);
    s.Colors[ImGuiCol_WindowBg] = panel;
    s.Colors[ImGuiCol_TitleBg] = panel;
    s.Colors[ImGuiCol_TitleBgActive] = col(accent, 0.85F);
    s.Colors[ImGuiCol_Button] = col(accent, 0.55F);
    s.Colors[ImGuiCol_ButtonHovered] = col(accent, 0.80F);
    s.Colors[ImGuiCol_ButtonActive] = accent;
    s.Colors[ImGuiCol_SliderGrab] = accent;
    s.Colors[ImGuiCol_CheckMark] = accent;
    s.Colors[ImGuiCol_Header] = col(accent, 0.40F);
}

std::string resolveDsl(int argc, char** argv) {
    if (argc > 1) return argv[1];
    return TUPAN_STUDIO_DSL;
}

}  // namespace

int main(int argc, char** argv) {
    glfwSetErrorCallback(glfwErrorCallback);
    if (!glfwInit()) {
        std::fprintf(stderr, "Falha ao iniciar GLFW.\n");
        return 1;
    }
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_SAMPLES, 4);

    GLFWwindow* win = glfwCreateWindow(1280, 800, "Tupan Studio", nullptr, nullptr);
    if (!win) {
        std::fprintf(stderr, "Falha ao criar janela OpenGL.\n");
        glfwTerminate();
        return 1;
    }
    glfwMakeContextCurrent(win);
    glfwSwapInterval(1);
    if (glewInit() != GLEW_OK) {
        std::fprintf(stderr, "Falha ao iniciar GLEW.\n");
        glfwDestroyWindow(win);
        glfwTerminate();
        return 1;
    }

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    ImGui_ImplGlfw_InitForOpenGL(win, true);
    ImGui_ImplOpenGL3_Init("#version 330 core");

    tupan::studio::SceneRenderer scene;
    std::string err;
    if (!scene.init(&err)) {
        std::fprintf(stderr, "Renderer: %s\n", err.c_str());
        return 1;
    }

    const std::string dslPath = resolveDsl(argc, argv);
    StudioConfig cfg;
    try {
        cfg = tupan::studio::loadConfig(dslPath);
    } catch (const std::exception& ex) {
        std::fprintf(stderr, "%s\n", ex.what());
        return 1;
    }
    applyTheme(cfg.theme);
    glfwSetWindowTitle(win, cfg.title.c_str());

    // Valores dos controles (inicializa pelos defaults do DSL).
    std::map<std::string, float> values;
    for (const auto& p : cfg.panels)
        for (const auto& c : p.controls)
            if (c.type == ControlType::Slider) values[c.id] = c.value;

    Mode mode = Mode::Night;
    bool autoSpin = false;
    bool recompute = true;
    SimState sim;

    const tupan::studio::Camera defaultCam = cfg.camera;
    double lastTime = glfwGetTime();
    float simTime = 0.0F;
    bool running = true;

    // Tabela de ações: cada comando do menu vira uma lambda (sem if-chain).
    using Action = std::function<void()>;
    std::unordered_map<std::string, Action> actions;
    actions["quit"] = [&] { running = false; };
    actions["reset_camera"] = [&] { cfg.camera = defaultCam; };
    actions["toggle_spin"] = [&] { autoSpin = !autoSpin; };
    actions["toggle_blueprint"] = [&] {
        mode = (mode == Mode::Blueprint) ? Mode::Day : Mode::Blueprint;
    };
    actions["mode_night"] = [&] { mode = Mode::Night; };
    actions["mode_day"] = [&] { mode = Mode::Day; };
    actions["reload"] = [&] {
        try {
            cfg = tupan::studio::loadConfig(dslPath);
            applyTheme(cfg.theme);
            recompute = true;
        } catch (const std::exception& ex) {
            std::fprintf(stderr, "%s\n", ex.what());
        }
    };

    while (!glfwWindowShouldClose(win) && running) {
        glfwPollEvents();
        const double now = glfwGetTime();
        const float dt = static_cast<float>(now - lastTime);
        lastTime = now;
        simTime += dt;

        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        // ------------------------------- Menu bar ---------------------------
        bool wantQuit = false;
        if (ImGui::BeginMainMenuBar()) {
            for (const auto& m : cfg.menu) {
                if (ImGui::BeginMenu(m.label.c_str())) {
                    for (const auto& it : m.items) {
                        if (ImGui::MenuItem(it.label.c_str())) {
                            const std::string& a = it.action;
                            if (a == "quit") wantQuit = true;
                            else if (a == "reset_camera") cfg.camera = defaultCam;
                            else if (a == "toggle_spin") autoSpin = !autoSpin;
                            else if (a == "toggle_blueprint")
                                mode = (mode == Mode::Blueprint) ? Mode::Day : Mode::Blueprint;
                            else if (a == "mode_night") mode = Mode::Night;
                            else if (a == "mode_day") mode = Mode::Day;
                            else if (a == "reload") {
                                try {
                                    cfg = tupan::studio::loadConfig(dslPath);
                                    applyTheme(cfg.theme);
                                    recompute = true;
                                } catch (const std::exception& ex) {
                                    std::fprintf(stderr, "%s\n", ex.what());
                                }
                            }
                        }
                    }
                    ImGui::EndMenu();
                }
            }
            ImGui::EndMainMenuBar();
        }

        // ------------------------------- Painéis ----------------------------
        for (const auto& p : cfg.panels) {
            ImGui::SetNextWindowPos(ImVec2(12, 40 + 0), ImGuiCond_FirstUseEver);
            ImGui::Begin(p.title.c_str());
            for (const auto& c : p.controls) {
                switch (c.type) {
                    case ControlType::Slider: {
                        float v = values.count(c.id) ? values[c.id] : c.value;
                        if (ImGui::SliderFloat(c.label.c_str(), &v, c.min, c.max)) {
                            values[c.id] = v;
                            recompute = true;
                        }
                        break;
                    }
                    case ControlType::Button:
                        if (ImGui::Button(c.label.c_str())) recompute = true;
                        break;
                    case ControlType::Checkbox: {
                        bool b = c.checked;
                        if (ImGui::Checkbox(c.label.c_str(), &b)) recompute = true;
                        break;
                    }
                    case ControlType::Text: {
                        char buf[96];
                        if (c.id == "sorvido") std::snprintf(buf, sizeof(buf), "%.3f kg", sim.sorbed_kg);
                        else if (c.id == "potavel") std::snprintf(buf, sizeof(buf), "%.3f L", sim.potable_l);
                        else if (c.id == "energia") std::snprintf(buf, sizeof(buf), "%.3f kWh", sim.energy_kwh);
                        else if (c.id == "custo") std::snprintf(buf, sizeof(buf), "R$ %.2f", sim.cost_brl);
                        else if (c.id == "status") std::snprintf(buf, sizeof(buf), "%s", sim.basin_full ? "cheia" : "enchendo");
                        else std::snprintf(buf, sizeof(buf), "-");
                        ImGui::Text("%s: %s", c.label.c_str(), buf);
                        break;
                    }
                }
            }
            ImGui::End();
        }

        // --------------------------- Física do núcleo -----------------------
        if (recompute) {
            const auto det = tupan::full_cycle(values["noite"], values["dia"], values["ur"],
                                               values["temp"], 25.0, 0.85, 120.0);
            sim.potable_l = static_cast<float>(det.potable_l);
            sim.distilled_l = static_cast<float>(det.distilled_l);
            sim.sorbed_kg = static_cast<float>(det.water_kg_sorbed);
            sim.energy_kwh = static_cast<float>(det.energy_kj_total / 3.6e6);
            sim.basin_full = det.basin_full;
            sim.cost_brl = sim.energy_kwh * 0.95F / std::max(sim.potable_l, 1e-3F);
            recompute = false;
        }

        // --------------------------- Controle de câmera ---------------------
        if (!io.WantCaptureMouse) {
            if (ImGui::IsMouseDragging(ImGuiMouseButton_Left)) {
                const ImVec2 d = ImGui::GetMouseDragDelta(ImGuiMouseButton_Left);
                cfg.camera.yaw -= d.x * 0.3F;
                cfg.camera.pitch = std::clamp(cfg.camera.pitch + d.y * 0.3F, -5.0F, 85.0F);
                ImGui::ResetMouseDragDelta(ImGuiMouseButton_Left);
            }
            const float wheel = io.MouseWheel;
            if (wheel != 0.0F) cfg.camera.distance = std::clamp(cfg.camera.distance - wheel * 0.6F, 2.0F, 40.0F);
        }

        // ------------------------------- Render 3D --------------------------
        ImGui::Render();
        int fbw = 0, fbh = 0;
        glfwGetFramebufferSize(win, &fbw, &fbh);
        glViewport(0, 0, fbw, fbh);
        scene.draw(cfg, sim, simTime, mode, autoSpin);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        glfwSwapBuffers(win);

        if (wantQuit) break;
    }

    scene.shutdown();
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    glfwDestroyWindow(win);
    glfwTerminate();
    return 0;
}
