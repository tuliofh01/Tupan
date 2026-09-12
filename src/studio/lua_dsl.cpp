// ============================================================================
//  TUPAN STUDIO — Parser do DSL Lua via sol2 (formato declarativo tipo JSON)
//  ---------------------------------------------------------------------------
//  sol2 dá acesso seguro a tabelas/hashes do Lua; usamos lambdas para eliminar
//  a repetição de iterar listas e ler campos compostos (vec3/color). O estado
//  Lua também expõe uma API `tupan.*` com lambdas C++ para o script chamar.
// ============================================================================
#include "lua_dsl.hpp"

#include <sol/sol.hpp>

#include <cstdio>
#include <stdexcept>
#include <string>

namespace tupan::studio {
namespace {

using math::Vec3;

// Lê {x,y,z} (índices 1..3) ou {x=,y=,z=}. Lambda reutilizável.
const auto readVec3 = [](const sol::object& o, Vec3 def) -> Vec3 {
    if (!o.is<sol::table>()) return def;
    sol::table t = o.as<sol::table>();
    if (t.size() >= 3) {
        return {t.get_or(1, def[0]), t.get_or(2, def[1]), t.get_or(3, def[2])};
    }
    return {t.get_or("x", def[0]), t.get_or("y", def[1]), t.get_or("z", def[2])};
};

const auto readColor = [](const sol::object& o, Color def) -> Color {
    if (!o.is<sol::table>()) return def;
    sol::table t = o.as<sol::table>();
    if (t.size() >= 3) {
        return {t.get_or(1, def.r), t.get_or(2, def.g), t.get_or(3, def.b)};
    }
    return {t.get_or("r", def.r), t.get_or("g", def.g), t.get_or("b", def.b)};
};

// Percorre uma lista Lua 1..n aplicando `fn(entry)` — evita repetir o laço.
template <class Fn>
void forEach(const sol::object& arr, Fn&& fn) {
    if (!arr.is<sol::table>()) return;
    sol::table t = arr.as<sol::table>();
    const std::size_t n = t.size();
    for (std::size_t i = 1; i <= n; ++i) {
        sol::object entry = t[i];
        if (entry.valid()) fn(entry, static_cast<int>(i));
    }
}

Shape shapeFrom(const std::string& s) {
    if (s == "cylinder") return Shape::Cylinder;
    if (s == "sphere") return Shape::Sphere;
    if (s == "fan") return Shape::Fan;
    if (s == "coil") return Shape::Coil;
    if (s == "model") return Shape::Model;
    return Shape::Box;
}

ControlType controlTypeFrom(const std::string& s) {
    if (s == "slider") return ControlType::Slider;
    if (s == "button") return ControlType::Button;
    if (s == "checkbox") return ControlType::Checkbox;
    return ControlType::Text;
}

}  // namespace

StudioConfig loadConfig(const std::string& path) {
    sol::state lua;
    lua.open_libraries(sol::lib::base, sol::lib::math, sol::lib::string, sol::lib::table);

    // API exposta ao DSL: lambdas C++ ficam disponíveis como tupan.log(...).
    lua["tupan"] = lua.create_table_with(
        "version", std::string("0.1.0"),
        "pi", 3.14159265358979323846,
        "log", [](const std::string& msg) { std::printf("[dsl] %s\n", msg.c_str()); });

    sol::protected_function_result result = lua.safe_script_file(path, sol::script_pass_on_error);
    if (!result.valid()) {
        const sol::error err = result;
        throw std::runtime_error("DSL Lua (" + path + "): " + err.what());
    }
    if (result.get_type() != sol::type::table) {
        throw std::runtime_error("DSL Lua deve retornar uma tabela na raiz.");
    }
    const sol::table root = result;

    StudioConfig cfg;
    cfg.title = root.get_or("title", cfg.title);
    cfg.version = root.get_or("version", cfg.version);
    // Guarda o diretório do DSL para resolver `file` relativos dos modelos.
    const std::size_t slash = path.find_last_of("/\\");
    cfg.baseDir = (slash == std::string::npos) ? "." : path.substr(0, slash);

    // --- tema -------------------------------------------------------------
    if (sol::optional<sol::table> th = root["theme"]) {
        cfg.theme.accent = readColor((*th)["accent"], cfg.theme.accent);
        cfg.theme.panel = readColor((*th)["panel"], cfg.theme.panel);
        cfg.theme.text = readColor((*th)["text"], cfg.theme.text);
    }

    // --- menus ------------------------------------------------------------
    forEach(root["menu"], [&](const sol::object& m, int) {
        const sol::table t = m.as<sol::table>();
        Menu menu;
        menu.label = t.get_or("label", std::string("Menu"));
        forEach(t["items"], [&](const sol::object& it, int) {
            const sol::table j = it.as<sol::table>();
            menu.items.push_back({j.get_or("label", std::string("-")),
                                  j.get_or("action", std::string("none"))});
        });
        cfg.menu.push_back(std::move(menu));
    });

    // --- painéis ----------------------------------------------------------
    forEach(root["panels"], [&](const sol::object& p, int) {
        const sol::table t = p.as<sol::table>();
        Panel panel;
        panel.id = t.get_or("id", std::string("panel"));
        panel.title = t.get_or("title", panel.id);
        forEach(t["controls"], [&](const sol::object& c, int) {
            const sol::table j = c.as<sol::table>();
            Control ctl;
            ctl.type = controlTypeFrom(j.get_or("type", std::string("text")));
            ctl.id = j.get_or("id", std::string("ctl"));
            ctl.label = j.get_or("label", ctl.id);
            ctl.min = j.get_or("min", 0.0F);
            ctl.max = j.get_or("max", 1.0F);
            ctl.value = j.get_or("value", ctl.min);
            ctl.checked = j.get_or("checked", false);
            panel.controls.push_back(std::move(ctl));
        });
        cfg.panels.push_back(std::move(panel));
    });

    // --- câmera -----------------------------------------------------------
    if (sol::optional<sol::table> cam = root["camera"]) {
        cfg.camera.target = readVec3((*cam)["target"], cfg.camera.target);
        cfg.camera.distance = cam->get_or("distance", cfg.camera.distance);
        cfg.camera.yaw = cam->get_or("yaw", cfg.camera.yaw);
        cfg.camera.pitch = cam->get_or("pitch", cfg.camera.pitch);
    }

    // --- cena -------------------------------------------------------------
    if (sol::optional<sol::table> sc = root["scene"]) {
        if (sol::optional<sol::table> g = (*sc)["grid"]) {
            cfg.grid.size = g->get_or("size", cfg.grid.size);
            cfg.grid.step = g->get_or("step", cfg.grid.step);
            cfg.grid.color = readColor((*g)["color"], cfg.grid.color);
        }
        forEach((*sc)["objects"], [&](const sol::object& o, int) {
            const sol::table t = o.as<sol::table>();
            SceneObject obj;
            obj.id = t.get_or("id", std::string("obj"));
            obj.shape = shapeFrom(t.get_or("shape", std::string("box")));
            obj.pos = readVec3(t["pos"], obj.pos);
            obj.size = readVec3(t["size"], obj.size);
            obj.color = readColor(t["color"], obj.color);
            obj.file = t.get_or("file", std::string(""));
            cfg.scene.push_back(std::move(obj));
        });
    }

    return cfg;
}

}  // namespace tupan::studio
