// ============================================================================
//  TUPAN STUDIO — Carregador de malhas 3D (STL/OBJ)
//  ---------------------------------------------------------------------------
//  DIDÁTICA: o studio nasceu desenhando primitivas (caixa, cilindro, esfera).
//  Para exibir CAD de verdade, este módulo lê arquivos STL (ASCII/binário) e
//  OBJ, normaliza a malha para uma caixa unitária centrada na origem (-0.5..0.5)
//  e devolve vértices intercalados (posição + normal) prontos para a GPU.
//  A normalização permite reaproveitar o mesmo `pos`/`size` do DSL para
//  posicionar e escalar qualquer modelo carregado.
// ============================================================================
#pragma once

#include <string>
#include <vector>

namespace tupan::studio {

struct MeshData {
    std::vector<float> vertices;              // intercalado: px,py,pz, nx,ny,nz
    std::vector<unsigned int> indices;        // triângulos
    bool empty() const noexcept { return indices.empty(); }
};

// Carrega STL (ascii ou binário) ou OBJ. Lança std::runtime_error em falha.
[[nodiscard]] MeshData loadMeshFile(const std::string& path);

}  // namespace tupan::studio
