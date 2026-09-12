// ============================================================================
//  TUPAN STUDIO — Renderizador OpenGL 3.3
// ============================================================================
#include "scene.hpp"
#include "mesh_loader.hpp"

#include <GL/glew.h>

#include <cmath>
#include <cstddef>
#include <string>
#include <vector>

namespace tupan::studio {
namespace {

using math::Mat4;
using math::Vec3;
using math::radians;

struct Vertex { float px, py, pz, nx, ny, nz; };

void pushVert(std::vector<Vertex>& v, Vec3 p, Vec3 n) {
    v.push_back({p[0], p[1], p[2], n[0], n[1], n[2]});
}

void uploadIndexed(SceneRenderer::Mesh& m,
                   const std::vector<Vertex>& verts,
                   const std::vector<unsigned int>& idx) {
    glGenVertexArrays(1, &m.vao);
    glBindVertexArray(m.vao);
    glGenBuffers(1, &m.vbo);
    glBindBuffer(GL_ARRAY_BUFFER, m.vbo);
    glBufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(verts.size() * sizeof(Vertex)),
                 verts.data(), GL_STATIC_DRAW);
    glGenBuffers(1, &m.ebo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m.ebo);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                 static_cast<GLsizeiptr>(idx.size() * sizeof(unsigned int)),
                 idx.data(), GL_STATIC_DRAW);
    const GLsizei stride = sizeof(Vertex);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride,
                          reinterpret_cast<void*>(offsetof(Vertex, px)));
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride,
                          reinterpret_cast<void*>(offsetof(Vertex, nx)));
    m.count = static_cast<int>(idx.size());
    m.indexed = true;
    glBindVertexArray(0);
}

void uploadLines(SceneRenderer::Mesh& m, const std::vector<float>& pos) {
    glGenVertexArrays(1, &m.vao);
    glBindVertexArray(m.vao);
    glGenBuffers(1, &m.vbo);
    glBindBuffer(GL_ARRAY_BUFFER, m.vbo);
    glBufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(pos.size() * sizeof(float)),
                 pos.data(), GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), nullptr);
    glDisableVertexAttribArray(1);
    glVertexAttrib3f(1, 0.0F, 0.0F, 1.0F);
    m.count = static_cast<int>(pos.size() / 3);
    m.indexed = false;
    glBindVertexArray(0);
}

unsigned int compile(unsigned int type, const char* src, std::string* err) {
    const unsigned int s = glCreateShader(type);
    glShaderSource(s, 1, &src, nullptr);
    glCompileShader(s);
    int ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[1024]{};
        glGetShaderInfoLog(s, sizeof(log), nullptr, log);
        if (err) *err = std::string("shader: ") + log;
        glDeleteShader(s);
        return 0;
    }
    return s;
}

void buildBox(SceneRenderer::Mesh& m) {
    std::vector<Vertex> v;
    std::vector<unsigned int> i;
    const Vec3 n[6] = {{0, 0, 1}, {0, 0, -1}, {1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}};
    const float h = 0.5F;
    for (int f = 0; f < 6; ++f) {
        const Vec3 nn = n[f];
        const Vec3 t = (std::abs(nn[1]) > 0.5F) ? Vec3{1, 0, 0} : Vec3{0, 1, 0};
        const Vec3 b = {nn[1] * t[2] - nn[2] * t[1], nn[2] * t[0] - nn[0] * t[2],
                        nn[0] * t[1] - nn[1] * t[0]};
        const unsigned base = static_cast<unsigned>(v.size());
        for (int c = 0; c < 4; ++c) {
            const float sx = (c == 1 || c == 2) ? 1.0F : -1.0F;
            const float sy = (c == 2 || c == 3) ? 1.0F : -1.0F;
            pushVert(v, {nn[0] * h + t[0] * sx * h + b[0] * sy * h,
                         nn[1] * h + t[1] * sx * h + b[1] * sy * h,
                         nn[2] * h + t[2] * sx * h + b[2] * sy * h}, nn);
        }
        i.insert(i.end(), {base, base + 1, base + 2, base, base + 2, base + 3});
    }
    uploadIndexed(m, v, i);
}

void buildCylinder(SceneRenderer::Mesh& m, int seg = 24) {
    std::vector<Vertex> v;
    std::vector<unsigned int> i;
    const float h = 0.5F;
    for (int s = 0; s <= seg; ++s) {
        const float a = 2.0F * math::kPi * static_cast<float>(s) / static_cast<float>(seg);
        const float cx = std::cos(a), cz = std::sin(a);
        pushVert(v, {cx * 0.5F, h, cz * 0.5F}, {cx, 0, cz});
        pushVert(v, {cx * 0.5F, -h, cz * 0.5F}, {cx, 0, cz});
    }
    for (int s = 0; s < seg; ++s) {
        const unsigned a = static_cast<unsigned>(s * 2);
        i.insert(i.end(), {a, a + 1, a + 3, a, a + 3, a + 2});
    }
    const unsigned topC = static_cast<unsigned>(v.size());
    pushVert(v, {0, h, 0}, {0, 1, 0});
    const unsigned botC = static_cast<unsigned>(v.size());
    pushVert(v, {0, -h, 0}, {0, -1, 0});
    for (int s = 0; s < seg; ++s) {
        const float a0 = 2.0F * math::kPi * static_cast<float>(s) / static_cast<float>(seg);
        const float a1 = 2.0F * math::kPi * static_cast<float>(s + 1) / static_cast<float>(seg);
        const unsigned t0 = static_cast<unsigned>(v.size());
        pushVert(v, {std::cos(a0) * 0.5F, h, std::sin(a0) * 0.5F}, {0, 1, 0});
        pushVert(v, {std::cos(a1) * 0.5F, h, std::sin(a1) * 0.5F}, {0, 1, 0});
        i.insert(i.end(), {topC, t0, t0 + 1});
        const unsigned b0 = static_cast<unsigned>(v.size());
        pushVert(v, {std::cos(a1) * 0.5F, -h, std::sin(a1) * 0.5F}, {0, -1, 0});
        pushVert(v, {std::cos(a0) * 0.5F, -h, std::sin(a0) * 0.5F}, {0, -1, 0});
        i.insert(i.end(), {botC, b0, b0 + 1});
    }
    uploadIndexed(m, v, i);
}

void buildSphere(SceneRenderer::Mesh& m, int rings = 16, int sectors = 24) {
    std::vector<Vertex> v;
    std::vector<unsigned int> i;
    for (int r = 0; r <= rings; ++r) {
        const float phi = math::kPi * static_cast<float>(r) / static_cast<float>(rings);
        for (int s = 0; s <= sectors; ++s) {
            const float th = 2.0F * math::kPi * static_cast<float>(s) / static_cast<float>(sectors);
            const float x = std::sin(phi) * std::cos(th);
            const float y = std::cos(phi);
            const float z = std::sin(phi) * std::sin(th);
            pushVert(v, {x * 0.5F, y * 0.5F, z * 0.5F}, {x, y, z});
        }
    }
    for (int r = 0; r < rings; ++r) {
        for (int s = 0; s < sectors; ++s) {
            const unsigned a = static_cast<unsigned>(r * (sectors + 1) + s);
            const unsigned b = a + static_cast<unsigned>(sectors + 1);
            i.insert(i.end(), {a, b, a + 1, a + 1, b, b + 1});
        }
    }
    uploadIndexed(m, v, i);
}

void buildGrid(SceneRenderer::Mesh& m, int half = 10) {
    std::vector<float> p;
    for (int i = -half; i <= half; ++i) {
        const float t = static_cast<float>(i) / static_cast<float>(half) * 0.5F;
        p.insert(p.end(), {-0.5F, 0.0F, t, 0.5F, 0.0F, t});
        p.insert(p.end(), {t, 0.0F, -0.5F, t, 0.0F, 0.5F});
    }
    uploadLines(m, p);
}

void buildCoil(SceneRenderer::Mesh& m, int turns = 8, int steps = 96) {
    std::vector<float> p;
    for (int s = 0; s <= steps; ++s) {
        const float t = static_cast<float>(s) / static_cast<float>(steps);
        const float a = 2.0F * math::kPi * static_cast<float>(turns) * t;
        p.insert(p.end(), {t - 0.5F, 0.35F * std::sin(a), 0.35F * std::cos(a)});
    }
    uploadLines(m, p);
}

}  // namespace

bool SceneRenderer::init(std::string* err) {
    static const char* vs = R"(
        #version 330 core
        layout(location=0) in vec3 aPos;
        layout(location=1) in vec3 aNormal;
        uniform mat4 uMVP; uniform mat4 uModel;
        out vec3 vNormal;
        void main(){ vNormal = mat3(uModel)*aNormal; gl_Position = uMVP*vec4(aPos,1.0); }
    )";
    static const char* fs = R"(
        #version 330 core
        in vec3 vNormal; out vec4 FragColor;
        uniform vec3 uColor; uniform float uLight;
        void main(){
            vec3 c = uColor;
            if(uLight > 0.5){
                vec3 n = normalize(vNormal);
                vec3 l = normalize(vec3(0.4,0.9,0.6));
                float d = max(dot(n,l), 0.0);
                c *= 0.35 + 0.75*d;
            }
            FragColor = vec4(c, 1.0);
        }
    )";
    const unsigned int v = compile(GL_VERTEX_SHADER, vs, err);
    if (!v) return false;
    const unsigned int f = compile(GL_FRAGMENT_SHADER, fs, err);
    if (!f) return false;
    program_ = glCreateProgram();
    glAttachShader(program_, v);
    glAttachShader(program_, f);
    glLinkProgram(program_);
    glDeleteShader(v);
    glDeleteShader(f);
    int ok = 0;
    glGetProgramiv(program_, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[1024]{};
        glGetProgramInfoLog(program_, sizeof(log), nullptr, log);
        if (err) *err = std::string("link: ") + log;
        return false;
    }
    uMvp_ = glGetUniformLocation(program_, "uMVP");
    uModel_ = glGetUniformLocation(program_, "uModel");
    uColor_ = glGetUniformLocation(program_, "uColor");
    uLight_ = glGetUniformLocation(program_, "uLight");

    buildBox(box_);
    buildCylinder(cylinder_);
    buildSphere(sphere_);
    buildGrid(grid_);
    buildCoil(coil_);
    return true;
}

void SceneRenderer::shutdown() {
    for (Mesh* m : {&box_, &cylinder_, &sphere_, &grid_, &coil_, &unit_}) {
        if (m->vao) glDeleteVertexArrays(1, &m->vao);
        if (m->vbo) glDeleteBuffers(1, &m->vbo);
        if (m->ebo) glDeleteBuffers(1, &m->ebo);
    }
    for (auto& [key, m] : models_) {
        (void)key;
        if (m.vao) glDeleteVertexArrays(1, &m.vao);
        if (m.vbo) glDeleteBuffers(1, &m.vbo);
        if (m.ebo) glDeleteBuffers(1, &m.ebo);
    }
    models_.clear();
    if (program_) glDeleteProgram(program_);
}

void SceneRenderer::clear() {
    glClearColor(0.06F, 0.09F, 0.14F, 1.0F);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
}

void SceneRenderer::drawMesh(const Mesh& m) const {
    if (!m.vao) return;
    glBindVertexArray(m.vao);
    if (m.indexed) glDrawElements(GL_TRIANGLES, m.count, GL_UNSIGNED_INT, nullptr);
    else glDrawArrays(GL_LINES, 0, m.count);
    glBindVertexArray(0);
}

void SceneRenderer::drawGpuMesh(const GpuMesh& m) const {
    if (!m.vao) return;
    glBindVertexArray(m.vao);
    glDrawElements(GL_TRIANGLES, m.count, GL_UNSIGNED_INT, nullptr);
    glBindVertexArray(0);
}

// Carrega (uma vez) e devolve a malha de arquivo pedida pelo DSL. Tenta o
// caminho como veio, relativo ao diretório do .lua e, por fim, à raiz do repo.
const SceneRenderer::GpuMesh* SceneRenderer::modelFor(const StudioConfig& cfg,
                                                      const std::string& file) {
    if (file.empty()) return nullptr;
    const auto cached = models_.find(file);
    if (cached != models_.end()) return cached->second.count > 0 ? &cached->second : nullptr;

    std::vector<std::string> candidates{file, cfg.baseDir + "/" + file};
#ifdef TUPAN_ASSET_DIR
    candidates.push_back(std::string(TUPAN_ASSET_DIR) + "/" + file);
#endif
    MeshData data;
    for (const std::string& candidate : candidates) {
        try {
            data = loadMeshFile(candidate);
            if (!data.empty()) break;
        } catch (const std::exception&) {
            // tenta o próximo candidato
        }
    }

    GpuMesh gm;
    if (!data.empty()) {
        glGenVertexArrays(1, &gm.vao);
        glBindVertexArray(gm.vao);
        glGenBuffers(1, &gm.vbo);
        glBindBuffer(GL_ARRAY_BUFFER, gm.vbo);
        glBufferData(GL_ARRAY_BUFFER,
                     static_cast<GLsizeiptr>(data.vertices.size() * sizeof(float)),
                     data.vertices.data(), GL_STATIC_DRAW);
        glGenBuffers(1, &gm.ebo);
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, gm.ebo);
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     static_cast<GLsizeiptr>(data.indices.size() * sizeof(unsigned int)),
                     data.indices.data(), GL_STATIC_DRAW);
        const GLsizei stride = 6 * sizeof(float);
        glEnableVertexAttribArray(0);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, nullptr);
        glEnableVertexAttribArray(1);
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride,
                              reinterpret_cast<void*>(3 * sizeof(float)));
        gm.count = static_cast<int>(data.indices.size());
        glBindVertexArray(0);
    }
    const auto inserted = models_.emplace(file, gm);
    return inserted.first->second.count > 0 ? &inserted.first->second : nullptr;
}

void SceneRenderer::drawObject(const SceneObject& o, const StudioConfig& cfg,
                               const SimState& sim, float time_s, Mode mode, bool spin) {
    (void)cfg;
    const bool day = (mode == Mode::Day);
    const bool blueprint = (mode == Mode::Blueprint);

    if (o.shape == Shape::Fan) {
        const float rpm = (mode == Mode::Night ? 1.0F : 0.15F);
        const float ang = (spin ? time_s * 2.5F : 0.0F) + time_s * 6.0F * rpm;
        const Vec3 color{o.color.r, o.color.g, o.color.b};
        glUniform1f(uLight_, 1.0F);
        for (int b = 0; b < 3; ++b) {
            const Mat4 blade = math::translate(o.pos) *
                               math::rotateX(ang + static_cast<float>(b) * 2.0943951F) *
                               math::scale({0.06F, o.size[1], o.size[2] * 0.4F});
            const Mat4 mvp = proj_ * view_ * blade;
            glUniformMatrix4fv(uModel_, 1, GL_FALSE, blade.data());
            glUniformMatrix4fv(uMvp_, 1, GL_FALSE, mvp.data());
            glUniform3f(uColor_, color[0], color[1], color[2]);
            drawMesh(box_);
        }
        const Mat4 hub = math::translate(o.pos) * math::scale({0.18F, 0.18F, 0.18F});
        const Mat4 hmvp = proj_ * view_ * hub;
        glUniformMatrix4fv(uModel_, 1, GL_FALSE, hub.data());
        glUniformMatrix4fv(uMvp_, 1, GL_FALSE, hmvp.data());
        drawMesh(sphere_);
        return;
    }

    Mat4 model = math::translate(o.pos) * math::scale(o.size);
    Vec3 color{o.color.r, o.color.g, o.color.b};
    bool light = true;
    const Mesh* mesh = &box_;
    if (o.shape == Shape::Cylinder) mesh = &cylinder_;
    else if (o.shape == Shape::Sphere) mesh = &sphere_;
    else if (o.shape == Shape::Coil) {
        mesh = &coil_;
        light = false;
        const float glow = day ? 1.6F : 0.7F;
        color = {o.color.r * glow, o.color.g * glow, o.color.b * glow};
    }
    if (blueprint) { color = {0.45F, 0.72F, 1.0F}; light = false; }

    // Modelo 3D carregado de arquivo (STL/OBJ): desenha a malha normalizada.
    if (o.shape == Shape::Model) {
        const GpuMesh* gm = modelFor(cfg, o.file);
        if (gm) {
            const Mat4 mvp = proj_ * view_ * model;
            glUniformMatrix4fv(uModel_, 1, GL_FALSE, model.data());
            glUniformMatrix4fv(uMvp_, 1, GL_FALSE, mvp.data());
            glUniform3f(uColor_, color[0], color[1], color[2]);
            glUniform1f(uLight_, light ? 1.0F : 0.0F);
            drawGpuMesh(*gm);
            return;
        }
        // Se falhar o carregamento, cai no cubo para não sumir da cena.
    }

    // Nível de água na bacia: um volume interno que cresce com os litros.
    if (o.id.find("bacia") != std::string::npos) {
        const float fill = std::min(1.0F, sim.potable_l / 2.0F);
        if (fill > 0.001F) {
            const Vec3 wp{o.pos[0], o.pos[1] - o.size[1] * 0.5F + o.size[1] * fill * 0.5F, o.pos[2]};
            const Mat4 water = math::translate(wp) *
                               math::scale({o.size[0] * 0.9F, o.size[1] * fill, o.size[2] * 0.9F});
            const Mat4 wmvp = proj_ * view_ * water;
            glUniformMatrix4fv(uModel_, 1, GL_FALSE, water.data());
            glUniformMatrix4fv(uMvp_, 1, GL_FALSE, wmvp.data());
            glUniform3f(uColor_, 0.18F, 0.55F, 0.95F);
            glUniform1f(uLight_, 1.0F);
            drawMesh(box_);
        }
    }

    const Mat4 mvp = proj_ * view_ * model;
    glUniformMatrix4fv(uModel_, 1, GL_FALSE, model.data());
    glUniformMatrix4fv(uMvp_, 1, GL_FALSE, mvp.data());
    glUniform3f(uColor_, color[0], color[1], color[2]);
    glUniform1f(uLight_, light ? 1.0F : 0.0F);
    drawMesh(*mesh);
}

void SceneRenderer::draw(const StudioConfig& cfg, const SimState& sim, float time_s,
                         Mode mode, bool auto_spin) {
    int vp[4]{};
    glGetIntegerv(GL_VIEWPORT, vp);
    fb_width_ = std::max(1, vp[2]);
    fb_height_ = std::max(1, vp[3]);
    const float aspect = static_cast<float>(fb_width_) / static_cast<float>(fb_height_);

    proj_ = math::perspective(radians(45.0F), aspect, 0.1F, 200.0F);
    const Vec3 eye = math::orbitEye(cfg.camera.target, cfg.camera.yaw, cfg.camera.pitch,
                                    cfg.camera.distance);
    view_ = math::lookAt(eye, cfg.camera.target, {0, 1, 0});

    if (mode == Mode::Night) glClearColor(0.04F, 0.06F, 0.13F, 1.0F);
    else if (mode == Mode::Day) glClearColor(0.62F, 0.74F, 0.86F, 1.0F);
    else glClearColor(0.05F, 0.08F, 0.12F, 1.0F);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    glEnable(GL_DEPTH_TEST);
    glUseProgram(program_);

    // Piso (grade) sem iluminação.
    {
        const Mat4 g = math::translate({0, 0, 0}) * math::scale({cfg.grid.size, 1.0F, cfg.grid.size});
        const Mat4 mvp = proj_ * view_ * g;
        glUniformMatrix4fv(uModel_, 1, GL_FALSE, g.data());
        glUniformMatrix4fv(uMvp_, 1, GL_FALSE, mvp.data());
        const Vec3 c{cfg.grid.color.r, cfg.grid.color.g, cfg.grid.color.b};
        glUniform3f(uColor_, c[0], c[1], c[2]);
        glUniform1f(uLight_, 0.0F);
        drawMesh(grid_);
    }

    for (const SceneObject& o : cfg.scene) {
        drawObject(o, cfg, sim, time_s, mode, auto_spin);
    }
    glUseProgram(0);
}

}  // namespace tupan::studio
