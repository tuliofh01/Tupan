# ============================================================================
#  TUPAN, MÁQUINA DE CHUVA — Imagem Docker (multi-stage / multi-target)
#  ---------------------------------------------------------------------------
#  Estágios:
#    build → toolchain + CMake + pybind11; compila núcleo C++23 e roda CTest.
#    core  → imagem mínima só com o CLI (tupan_sim) e testes.
#    web   → microsserviço Flask (gunicorn) com o módulo nativo pybind.
#
#  Build:
#    docker build -f docker/Dockerfile --target core -t tupan-core:0.1.0 .
#    docker build -f docker/Dockerfile --target web  -t tupan-web:0.1.0  .
#    # ou: scripts/build-docker.sh --target web --tag 0.1.0 --push
# ============================================================================

# ---------------------------------------------------------------- build ----
FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pybind11
WORKDIR /src
COPY . .
# Studio desligado: a imagem é headless (sem GL/GLFW/Lua).
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
        -DTUPAN_WITH_STUDIO=OFF -DTUPAN_WITH_PYBIND=ON \
    && cmake --build build -j"$(nproc)" \
    && ctest --test-dir build --output-on-failure

# ----------------------------------------------------------------- core ----
FROM python:3.12-slim AS core
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 tupan
COPY --from=build /src/build/tupan_sim   /usr/local/bin/tupan_sim
COPY --from=build /src/build/tupan_tests /usr/local/bin/tupan_tests
COPY --from=build /src/src/core/tupan_constants.json /usr/local/share/tupan/tupan_constants.json
USER tupan
ENTRYPOINT ["tupan_sim"]
CMD ["--help"]

# ------------------------------------------------------------------ web ----
FROM python:3.12-slim AS web
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir flask gunicorn \
    && useradd -m -u 10001 tupan
WORKDIR /app/server
COPY --from=build /src/tools/server/ ./ 
COPY --from=build /src/build/tupan_native*.so ./
COPY --from=build /src/src/core/tupan_constants.json ./
ENV PYTHONPATH=/app/server PYTHONUNBUFFERED=1
EXPOSE 5000
USER tupan
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health').status==200 else 1)"
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "simulador_tupan:app"]
