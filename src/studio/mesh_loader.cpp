// ============================================================================
//  TUPAN STUDIO — Implementação do carregador STL/OBJ
// ============================================================================
#include "mesh_loader.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace tupan::studio {
namespace {

struct Vec3f { float x = 0, y = 0, z = 0; };

Vec3f sub(Vec3f a, Vec3f b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
Vec3f cross(Vec3f a, Vec3f b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
Vec3f normalize(Vec3f v) {
    const float n = std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    return n > 1e-12F ? Vec3f{v.x / n, v.y / n, v.z / n} : Vec3f{0, 1, 0};
}

// Acrescenta um triângulo (3 vértices) com a normal informada.
void pushTri(MeshData& m, Vec3f a, Vec3f b, Vec3f c) {
    const Vec3f n = normalize(cross(sub(b, a), sub(c, a)));
    const unsigned int base = static_cast<unsigned int>(m.vertices.size() / 6);
    for (const Vec3f v : {a, b, c}) {
        m.vertices.insert(m.vertices.end(), {v.x, v.y, v.z, n.x, n.y, n.z});
    }
    m.indices.insert(m.indices.end(), {base, base + 1, base + 2});
}

std::string readAll(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("malha nao encontrada: " + path);
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

MeshData parseStlAscii(const std::string& text) {
    MeshData m;
    std::istringstream in(text);
    std::string tok;
    std::vector<Vec3f> tri;
    while (in >> tok) {
        if (tok == "vertex") {
            Vec3f v;
            in >> v.x >> v.y >> v.z;
            tri.push_back(v);
            if (tri.size() == 3) {
                pushTri(m, tri[0], tri[1], tri[2]);
                tri.clear();
            }
        }
    }
    return m;
}

MeshData parseStlBinary(const std::string& blob) {
    MeshData m;
    if (blob.size() < 84) return m;
    std::uint32_t count = 0;
    std::memcpy(&count, blob.data() + 80, 4);
    const std::size_t need = 84 + static_cast<std::size_t>(count) * 50;
    if (blob.size() < need) return m;
    const char* p = blob.data() + 84;
    for (std::uint32_t i = 0; i < count; ++i) {
        Vec3f v[3];
        std::memcpy(&v[0], p + 12, 12);
        std::memcpy(&v[1], p + 24, 12);
        std::memcpy(&v[2], p + 36, 12);
        pushTri(m, v[0], v[1], v[2]);
        p += 50;
    }
    return m;
}

MeshData parseObj(const std::string& text) {
    MeshData m;
    std::vector<Vec3f> pos;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        std::istringstream ls(line);
        std::string tag;
        ls >> tag;
        if (tag == "v") {
            Vec3f v;
            ls >> v.x >> v.y >> v.z;
            pos.push_back(v);
        } else if (tag == "f") {
            std::vector<Vec3f> poly;
            std::string item;
            while (ls >> item) {
                const int idx = std::stoi(item) - 1;  // OBJ é 1-based
                if (idx >= 0 && idx < static_cast<int>(pos.size())) poly.push_back(pos[idx]);
            }
            for (std::size_t i = 1; i + 1 < poly.size(); ++i) {
                pushTri(m, poly[0], poly[i], poly[i + 1]);  // triangula em leque
            }
        }
    }
    return m;
}

// Normaliza: centraliza e escala a maior dimensão para 1 (caixa unitária).
void normalizeMesh(MeshData& m) {
    if (m.vertices.empty()) return;
    float lo[3] = {1e30F, 1e30F, 1e30F};
    float hi[3] = {-1e30F, -1e30F, -1e30F};
    for (std::size_t i = 0; i < m.vertices.size(); i += 6) {
        for (int k = 0; k < 3; ++k) {
            lo[k] = std::min(lo[k], m.vertices[i + k]);
            hi[k] = std::max(hi[k], m.vertices[i + k]);
        }
    }
    const float center[3] = {(lo[0] + hi[0]) * 0.5F, (lo[1] + hi[1]) * 0.5F, (lo[2] + hi[2]) * 0.5F};
    const float size = std::max({hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], 1e-6F});
    const float s = 1.0F / size;
    for (std::size_t i = 0; i < m.vertices.size(); i += 6) {
        for (int k = 0; k < 3; ++k) m.vertices[i + k] = (m.vertices[i + k] - center[k]) * s;
    }
}

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
    return s;
}

std::string extensionOf(const std::string& path) {
    const std::size_t dot = path.find_last_of('.');
    return dot == std::string::npos ? "" : lower(path.substr(dot));
}

}  // namespace

MeshData loadMeshFile(const std::string& path) {
    const std::string blob = readAll(path);
    const std::string ext = extensionOf(path);
    MeshData m;
    if (ext == ".obj") {
        m = parseObj(blob);
    } else if (ext == ".stl") {
        // Heurística: ASCII começa com "solid" e contém "facet"; senão binário.
        const std::string head = lower(blob.substr(0, 5));
        if (head == "solid" && lower(blob).find("facet") != std::string::npos) {
            m = parseStlAscii(blob);
        } else {
            m = parseStlBinary(blob);
        }
    } else {
        throw std::runtime_error("formato de malha nao suportado: " + ext);
    }
    normalizeMesh(m);
    return m;
}

}  // namespace tupan::studio
