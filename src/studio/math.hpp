// ============================================================================
//  TUPAN STUDIO — Álgebra linear para tempo real (C++23)
//  ---------------------------------------------------------------------------
//  Escalar fixo `Real = float`: metade da banda de memória de `double` e
//  suficiente para visualização; structs `alignas(16)` casam com registradores
//  SSE/AVX e com o layout column-major exigido pelo OpenGL. As operações são
//  `constexpr`/`noexcept` e evitam alocação dinâmica — overhead mínimo por frame.
// ============================================================================
#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <numbers>

namespace tupan::math {

using Real = float;
using Vec3 = std::array<Real, 3>;

// Vec4 alinhada a 16 B. A `union` dá duas vistas do MESMO armazenamento, sem
// cópia: `v` para laços/vetorização e `c` para leitura por nome (x,y,z,w).
struct alignas(16) Vec4 {
    struct Names { Real x, y, z, w; };
    union {
        std::array<Real, 4> v;
        Names c;
    };
    [[nodiscard]] constexpr Real& operator[](std::size_t i) noexcept { return v[i]; }
    [[nodiscard]] constexpr const Real& operator[](std::size_t i) const noexcept { return v[i]; }
};

inline constexpr Real kPi = std::numbers::pi_v<Real>;

[[nodiscard]] constexpr Real radians(Real deg) noexcept { return deg * kPi / 180.0F; }

[[nodiscard]] constexpr Vec3 operator+(Vec3 a, Vec3 b) noexcept {
    return {a[0] + b[0], a[1] + b[1], a[2] + b[2]};
}
[[nodiscard]] constexpr Vec3 operator-(Vec3 a, Vec3 b) noexcept {
    return {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
}
[[nodiscard]] constexpr Vec3 operator*(Vec3 a, Real s) noexcept {
    return {a[0] * s, a[1] * s, a[2] * s};
}
[[nodiscard]] constexpr Real dot(Vec3 a, Vec3 b) noexcept {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
[[nodiscard]] constexpr Vec3 cross(Vec3 a, Vec3 b) noexcept {
    return {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]};
}
[[nodiscard]] inline Vec3 normalize(Vec3 v) noexcept {
    const Real n = std::sqrt(dot(v, v));
    return n > 1e-6F ? v * (1.0F / n) : Vec3{0, 0, 0};
}

// ---------------------------------------------------------------------------
// Mat4 — 4×4 column-major (m[col*4 + row]), como o OpenGL espera. A `union`
// expõe a mesma memória como 16 floats (`m`), 4 colunas Vec4 (`col`) ou um
// bloco cru (`data`): zero cópias para upload GL e acesso por coluna (SIMD).
// ---------------------------------------------------------------------------
struct alignas(16) Mat4 {
    union {
        std::array<Real, 16> m;
        std::array<Vec4, 4> col;
        Real raw[16];
    };

    constexpr Mat4() noexcept : m{} {}

    [[nodiscard]] static constexpr Mat4 identity() noexcept {
        Mat4 r;
        r.m[0] = r.m[5] = r.m[10] = r.m[15] = 1.0F;
        return r;
    }
    [[nodiscard]] constexpr const Real* data() const noexcept { return m.data(); }
};

[[nodiscard]] constexpr Mat4 operator*(const Mat4& a, const Mat4& b) noexcept {
    Mat4 r{};
    for (int c = 0; c < 4; ++c) {
        for (int row = 0; row < 4; ++row) {
            Real s = 0.0F;
            for (int k = 0; k < 4; ++k) s += a.m[k * 4 + row] * b.m[c * 4 + k];
            r.m[c * 4 + row] = s;
        }
    }
    return r;
}

[[nodiscard]] inline Mat4 translate(Vec3 t) noexcept {
    Mat4 r = Mat4::identity();
    r.m[12] = t[0]; r.m[13] = t[1]; r.m[14] = t[2];
    return r;
}

[[nodiscard]] inline Mat4 scale(Vec3 s) noexcept {
    Mat4 r = Mat4::identity();
    r.m[0] = s[0]; r.m[5] = s[1]; r.m[10] = s[2];
    return r;
}

[[nodiscard]] inline Mat4 rotateY(Real a) noexcept {
    Mat4 r = Mat4::identity();
    const Real c = std::cos(a), s = std::sin(a);
    r.m[0] = c; r.m[2] = -s; r.m[8] = s; r.m[10] = c;
    return r;
}

[[nodiscard]] inline Mat4 rotateX(Real a) noexcept {
    Mat4 r = Mat4::identity();
    const Real c = std::cos(a), s = std::sin(a);
    r.m[5] = c; r.m[6] = s; r.m[9] = -s; r.m[10] = c;
    return r;
}

[[nodiscard]] inline Mat4 rotateZ(Real a) noexcept {
    Mat4 r = Mat4::identity();
    const Real c = std::cos(a), s = std::sin(a);
    r.m[0] = c; r.m[1] = s; r.m[4] = -s; r.m[5] = c;
    return r;
}

[[nodiscard]] inline Mat4 perspective(Real fovy, Real aspect, Real znear, Real zfar) noexcept {
    Mat4 r{};
    const Real f = 1.0F / std::tan(fovy * 0.5F);
    r.m[0] = f / aspect;
    r.m[5] = f;
    r.m[10] = (zfar + znear) / (znear - zfar);
    r.m[11] = -1.0F;
    r.m[14] = (2.0F * zfar * znear) / (znear - zfar);
    return r;
}

[[nodiscard]] inline Mat4 lookAt(Vec3 eye, Vec3 center, Vec3 up) noexcept {
    const Vec3 f = normalize(center - eye);
    const Vec3 s = normalize(cross(f, up));
    const Vec3 u = cross(s, f);
    Mat4 r = Mat4::identity();
    r.m[0] = s[0]; r.m[4] = s[1]; r.m[8] = s[2];
    r.m[1] = u[0]; r.m[5] = u[1]; r.m[9] = u[2];
    r.m[2] = -f[0]; r.m[6] = -f[1]; r.m[10] = -f[2];
    r.m[12] = -dot(s, eye); r.m[13] = -dot(u, eye); r.m[14] = dot(f, eye);
    return r;
}

// Órbita: converte (yaw, pitch, distância) em posição de câmera.
[[nodiscard]] inline Vec3 orbitEye(Vec3 target, Real yawDeg, Real pitchDeg, Real dist) noexcept {
    const Real yaw = radians(yawDeg), pitch = radians(pitchDeg);
    return {target[0] + dist * std::cos(pitch) * std::sin(yaw),
            target[1] + dist * std::sin(pitch),
            target[2] + dist * std::cos(pitch) * std::cos(yaw)};
}

}  // namespace tupan::math
