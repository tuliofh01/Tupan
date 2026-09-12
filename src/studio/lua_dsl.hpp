// ============================================================================
//  TUPAN STUDIO — DSL Lua com "cara de JSON"
//  ---------------------------------------------------------------------------
//  A UI e a cena 3D são descritas em um único arquivo Lua declarativo
//  (assets/studio.lua) cujo formato lembra JSON: apenas tabelas, strings e
//  números. O host lê essa árvore via C API e monta menus, painéis e objetos.
//  Nada disso exige recompilar: trocar o .lua reconfigura o studio.
// ============================================================================
#pragma once

#include "math.hpp"

#include <string>
#include <vector>

namespace tupan::studio {

using math::Real;
using math::Vec3;

struct Color { Real r = 1, g = 1, b = 1; };

enum class ControlType { Slider, Button, Text, Checkbox };

struct Control {
    ControlType type = ControlType::Text;
    std::string id;
    std::string label;
    Real min = 0, max = 1, value = 0;
    bool checked = false;
};

struct Panel {
    std::string id;
    std::string title;
    std::vector<Control> controls;
};

struct MenuItem { std::string label, action; };
struct Menu { std::string label; std::vector<MenuItem> items; };

enum class Shape { Box, Cylinder, Sphere, Fan, Coil, Model };

struct SceneObject {
    std::string id;
    Shape shape = Shape::Box;
    Vec3 pos{0, 0, 0};
    Vec3 size{1, 1, 1};
    Color color{1, 1, 1};
    std::string file;  // caminho da malha (STL/OBJ) quando shape = "model"
};

struct Camera {
    Vec3 target{0, 0.6F, 0};
    Real distance = 6.5F;
    Real yaw = 35.0F;
    Real pitch = 22.0F;
};

struct Grid { Real size = 10.0F; Real step = 1.0F; Color color{0.15F, 0.2F, 0.28F}; };

struct Theme {
    Color accent{0.25F, 0.72F, 1.0F};
    Color panel{0.09F, 0.14F, 0.22F};
    Color text{0.91F, 0.93F, 0.97F};
};

struct StudioConfig {
    std::string title = "Tupan Studio";
    std::string version = "0.1.0";
    std::string baseDir;  // diretório do .lua, para resolver caminhos relativos
    Theme theme;
    std::vector<Menu> menu;
    std::vector<Panel> panels;
    Camera camera;
    Grid grid;
    std::vector<SceneObject> scene;
};

// Lê o DSL (estilo JSON) de `path`. Lança std::runtime_error em erro de sintaxe.
[[nodiscard]] StudioConfig loadConfig(const std::string& path);

}  // namespace tupan::studio
