# Arquitetura — Tupan, Máquina de Chuva

> Documento vivo. Sempre que a árvore, os contratos ou o pipeline mudarem,
> atualize **este arquivo primeiro** e replique nos READMEs, manual e artigo.
> Última revisão: reorganização para o layout EN (`src/`, `tools/`, `data/`,
> `docs/`, `scripts/`, `deploy/`).

## 1. Princípio central

Existe **uma única fonte de verdade física**: `src/core/tupan_core.hpp`
(header-only, C++23). Todo consumidor — CLI, GUI Qt5, studio Lua/ImGui/OpenGL,
módulo pybind11, serviço Flask e firmware — usa as mesmas equações e o mesmo
`tupan_constants.json`. Isso garante **paridade física** verificável entre
linguagens e é o requisito de manutenibilidade (ISO/IEC 25010).

```
                     ┌───────────────────────────────┐
                     │  src/core/tupan_core.hpp      │
                     │  (física C++23, header-only)  │
                     └───────────────┬───────────────┘
        ┌───────────────┬────────────┼───────────────┬───────────────┐
   tupan_sim       tupan_studio  tupan_native    tupan_script     firmware
   (CLI)        (Lua+sol2+ImGui   (pybind11)     (luaaa headless)  (Arduino)
                 +OpenGL 3.3)
                                                     │
                              ┌──────────────────────┼───────────────────────┐
                        tools/pipeline          tools/server            tools/geradores
                        (clima + ML + custo)    (Flask REST/UI)         (relatórios/pitch)
                              │                        │
                          data/raw, processed,      data/results
                          results
```

## 2. Árvore por propósito

| Diretório | Propósito | Contém |
|-----------|-----------|--------|
| `src/core/` | Núcleo físico e derivados nativos | `tupan_core.hpp`, `tupan_sim.cpp`, `tupan_tests.cpp`, `tupan_constants.json`, `CMakeLists.txt` |
| `src/studio/` | Studio interativo (UI gráfica) | `math.hpp` (álgebra com `union`), `main.cpp`, `scene.*`, `lua_dsl.*`, `mesh_loader.*` (STL/OBJ), `assets/studio.lua` |
| `src/scripting/` | Runner Lua headless (luaaa) | `main.cpp`, `scripts/ciclo.lua` |
| `src/bindings/` | Ponte Python | `tupan_pybind.cpp` |
| `src/firmware/` | Firmware embarcado | `main.cpp`, `tupan_firmware.hpp`, `platformio.ini` |
| `tools/geradores/` | Entregáveis textuais | relatório, pitch, diagramas UML |
| `tools/midia/` | Mídia visual | imagens/renders, mapas, mockups |
| `tools/pipeline/` | Dados e ML | `analise_dados.py`, `custo_energia.py` |
| `tools/cad/` | Desenho técnico e 3D | `esquema_eletrico.py` (PNG/SVG), `gerar_cad.py` (DXF/STL/SCAD + prancha) |
| `tools/server/` | Microsserviço | `simulador_tupan.py` + `templates/` |
| `tools/tests/` | Testes Python | `test_simulador.py` |
| `data/raw/` | Entradas climáticas | CSVs de origem |
| `data/processed/` | Séries tratadas | clima, custo por bandeira |
| `data/results/` | Métricas/contratos | JSONs e projeções |
| `docs/relatorios/` | Artigo/relatório | docx, `artigo.txt` (LinkedIn) |
| `docs/pitch/` | Apresentação | pptx |
| `docs/manuais/` | Manuais | `manual_pt-br.md`, `manual_en-us.md` |
| `docs/midia/` | Mídia gerada | `renders/ graficos/ mapas/ mockups/ diagramas/ cad/` |
| `scripts/` | Build e operação | `build-linux.sh`, `build-windows.bat`, `build-docker.sh`, `deploy-k8s.sh`, `build-standalone.sh` |
| `packaging/` | Empacotamento standalone | `tupan-web.spec` (PyInstaller) |
| `deploy/k8s/` | Kubernetes | namespace, deployment, service, ingress, hpa |
| `deploy/vps/` | VPS | unit systemd + nginx |
| `ci/` | CI/CD | `Jenkinsfile` (+ `.github/workflows/ci.yml`) |

## 3. Contratos de dados

- **`src/core/tupan_constants.json`** — constantes físico-químicas
  (`sorção`, `destilação`, `pós-tratamento`, `energia`).
- **`data/raw/clima_semiarido_petrolina.csv`** — série horária de origem (ERA5/Open-Meteo).
- **`data/processed/clima_capitais_2024.csv`** — UR noturna média das 27 capitais (mapas).
- **`data/processed/custo_energia.csv`** — série por bandeira/tarifa social.
- **`data/results/metricas_ml.json`** — R², RMSE e envelope do modelo.
- **`data/results/projetoes_tupan.csv`** — projeção de produção.
- **`data/results/custo_energia.json`** — cenários anuais e comparação R$/L.

Regra: **entrada → `data/raw`; transformação → `data/processed`; saída analítica
→ `data/results`**. Nenhum script grava dados fora dessas pastas.

## 4. Convenções de caminho

Cada script resolve a raiz assim (arquivo em `tools/<sub>/x.py`):

```python
RAIZ = Path(__file__).resolve().parents[2]   # repo root
DADOS = RAIZ / "data"
DOCS  = RAIZ / "docs"
```

Mídia gerada **nunca** vai para `data/`; gráficos vão para
`docs/midia/graficos/`, renders para `docs/midia/renders/`, mapas para
`docs/midia/mapas/`. O módulo nativo é compilado em `build/tupan_native*.so`.

## 5. Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release      # núcleo + studio + scripting
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure          # testes C++
```

Opções: `TUPAN_WITH_STUDIO` (Lua+sol2+ImGui+OpenGL), `TUPAN_WITH_SCRIPTING`
(runner headless via luaaa), `TUPAN_WITH_PYBIND`. A GUI Qt5 foi **removida**.
Scripts: `scripts/build-linux.sh`, `scripts/build-windows.bat`.

## 5.1 UI interativa e scripting (Lua)

A interface gráfica é o **Tupan Studio** (`src/studio`): janela GLFW + OpenGL 3.3,
widgets em **Dear ImGui** e a cena 3D desenhada com a álgebra linear própria
(`math.hpp`, `Real = float`, `Mat4` com `union` column-major, `constexpr`).

- **sol2** lê o DSL declarativo `assets/studio.lua` (menus, painéis e objetos da
  cena) — formato de tabelas aninhadas que **lembra JSON**. Trocar o `.lua`
  reconfigura a UI sem recompilar; o menu "Arquivo → Recarregar DSL" recarrega.
- **luaaa** (single-header) faz o caminho inverso em `src/scripting`: expõe o
  núcleo C++ como módulo `tupan.*` para scripts headless (`tupan_script`).
- Ações de menu viram **lambdas** numa tabela de despacho; a física vem de
  `full_cycle(...)` do núcleo (paridade com CLI/pybind/web).
- O studio carrega **malhas 3D reais** (STL/OBJ) via `mesh_loader.*`: no DSL,
  `shape = "model"` + `file = "docs/midia/cad/tupan_pecas.stl"`. A malha é
  normalizada para uma caixa unitária, então `pos`/`size` valem para qualquer arquivo.

```bash
./build/tupan_studio                 # UI interativa
./build/tupan_script                 # roda src/scripting/scripts/ciclo.lua
./build/tupan_script meu_script.lua  # script próprio usando tupan.*
```

## 6. Entrega (Docker + CI/CD)

- `docker/Dockerfile` — estágios `build` → `core` (CLI) e `web` (gunicorn + `/health`).
- `docker-compose.yml` — sobe o serviço web local.
- `ci/Jenkinsfile` — build+teste → mídia → docker → push → deploy.
- `deploy/k8s/` — Deploy/Service/Ingress/HPA (probes em `/health`, `runAsNonRoot`).
- `deploy/vps/` — systemd + nginx para VPS simples.

## 7. Como estender

1. **Nova física/constante** → `src/core` + `tupan_constants.json`; rode os testes C++.
2. **Novo consumidor nativo** → adicione alvo em `src/core/CMakeLists.txt`.
3. **Novo script Python** → coloque em `tools/<propósito>/`, use `parents[2]` e grave em `data/`.
4. **Novo entregável** → gere em `docs/<pasta>/`; registre aqui e no README.
5. **Nova mídia** → `tools/midia/` → `docs/midia/<categoria>/`.
6. **Mudou a árvore?** Atualize `README.md`, `README.pt-BR.md`,
   `docs/manuais/manual_pt-br.md`, `docs/relatorios/artigo.txt` e este arquivo.
