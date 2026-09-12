// ============================================================================
//  TUPAN STUDIO — Renderizador OpenGL 3.3 da cena do dispositivo
//  ---------------------------------------------------------------------------
//  Desenha a "sala" em 3D a partir dos objetos declarados no DSL Lua e anima a
//  física do núcleo: ventoinhas giram no INTAKE, a bobina brilha no REGEN e o
//  nível da bacia acompanha os litros potáveis. Um único shader Lambert serve
//  a todas as malhas; a álgebra linear fica em math.hpp (sem dependências).
// ============================================================================
#pragma once

#include "lua_dsl.hpp"

#include <string>
#include <unordered_map>

namespace tupan::studio {

// Estado físico injetado pelo núcleo a cada ciclo.
struct SimState {
    float potable_l = 0.0F;
    float distilled_l = 0.0F;
    float energy_kwh = 0.0F;
    float cost_brl = 0.0F;
    bool basin_full = false;
    float sorbed_kg = 0.0F;
};

enum class Mode { Day, Night, Blueprint };

class SceneRenderer {
public:
    // Malha GPU (VAO/VBO/EBO). Pública porque funções de construção de malha
    // no .cpp (namespace anônimo) precisam preenchê-la.
    struct Mesh {
        unsigned int vao = 0, vbo = 0, ebo = 0;
        int count = 0;
        bool indexed = false;
    };

    bool init(std::string* err);
    void shutdown();
    void clear();
    void draw(const StudioConfig& cfg, const SimState& sim, float time_s,
              Mode mode, bool auto_spin);

private:
    Mesh box_{}, cylinder_{}, sphere_{}, grid_{}, coil_{}, unit_{};
    unsigned int program_ = 0;
    int uMvp_ = -1, uModel_ = -1, uColor_ = -1, uLight_ = -1;
    math::Mat4 proj_{}, view_{};
    int fb_width_ = 1, fb_height_ = 1;

    // Malhas 3D carregadas de arquivo (STL/OBJ), cacheadas por caminho.
    struct GpuMesh { unsigned int vao = 0, vbo = 0, ebo = 0; int count = 0; };
    std::unordered_map<std::string, GpuMesh> models_;
    const GpuMesh* modelFor(const StudioConfig& cfg, const std::string& file);

    void drawMesh(const Mesh& m) const;
    void drawGpuMesh(const GpuMesh& m) const;
    void drawObject(const SceneObject& o, const StudioConfig& cfg,
                    const SimState& sim, float time_s, Mode mode, bool spin);
};

}  // namespace tupan::studio
