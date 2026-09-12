# AGENTS — Guia do projeto Tupan, Máquina de Chuva

Este arquivo orienta agentes/colaboradores automáticos que trabalham no repositório.

## Padrão de código (obrigatório)

1. **Comentários didáticos em PT-BR.** Todo bloco não trivial deve explicar *o
   porquê* e *a intenção* em português, tom de aula — não apenas o *o quê*.
   Use cabeçalhos com `====` e separadores `----`, como no restante do repo.
2. **Nomes de código em inglês**, comentários/documentação em **PT-BR**
   (README e artigo têm versão EN).
3. **Sem `#include`/dependência nova** sem justificar no cabeçalho do arquivo.
4. **C++23** com `-Wall -Wextra -Wpedantic`; prefira `constexpr`, `[[nodiscard]]`,
   `noexcept`, `std::span`, lambdas e `union` para vistas sem cópia.
5. **Python 3.10+** com caminhos resolvidos por `Path(__file__).resolve().parents[2]`
   e saídas sempre em `data/` ou `docs/` (ver `docs/ARCHITECTURE.md`).
6. **Toda mudança de árvore/contrato** exige atualizar: `README.md`,
   `README.pt-BR.md`, `docs/ARCHITECTURE.md`, `docs/manuais/manual_pt-br.md`,
   `docs/manuais/manual_en-us.md`, `docs/relatorios/artigo.txt` e os geradores em `tools/`.

## Estrutura (resumo)

- `src/core` — física C++23 (fonte única de verdade), CLI, testes.
- `src/studio` — UI interativa: DSL **Lua** (estilo JSON) + **sol2** + **Dear
  ImGui** + **OpenGL 3.3** + álgebra linear própria (`math.hpp`, com `union`) +
  carga de malhas 3D **STL/OBJ** (`mesh_loader.*`).
- `src/bindings` — módulo Python (pybind11).
- `src/firmware` — Arduino Mega (C++20, MVC/FSM).
- `tools/{geradores,midia,pipeline,cad,server,tests}` — scripts por propósito
  (`tools/cad/gerar_cad.py` gera DXF/STL/SCAD + prancha).
- `data/{raw,processed,results}` — dados; `docs/` — entregáveis e mídia.
- `scripts/` — build; `deploy/` — k8s e VPS; `ci/` — Jenkins/GitHub Actions.

## Bibliotecas de scripting

- **sol2** — leitura das tabelas declarativas (janelas/painéis/cena) do DSL Lua.
- **luaaa** (`gengyong/luaaa`, single-header) — expõe o núcleo C++ ao Lua,
  para scripts de simulação headless.

## Comandos-chave

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)" && ctest --test-dir build --output-on-failure
./build/tupan_studio          # UI Lua/ImGui/OpenGL
scripts/build-linux.sh        # binários + dist/
python3 tools/geradores/gerar_relatorio.py
```
