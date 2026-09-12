# ============================================================================
#  TUPAN, MÁQUINA DE CHUVA — Imagem de build/execução nativa (Docker)
#  ---------------------------------------------------------------------------
#  DIDÁTICA: multi-stage. O estágio "build" leva toolchain + deps; o estágio
#  final copia APENAS os binários (imagem pequena, sem gcc/Qt-dev).
#  Uso:
#    docker build -t tupan-sim .
#    docker run --rm tupan-sim tupan_sim --ur 70 --hours 2 --runs 100000
#    docker run --rm tupan-sim tupan_tests
# ============================================================================
FROM debian:trixie-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake qtbase5-dev python3 python3-pip python3-pybind11 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j"$(nproc)"

FROM debian:trixie-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libqt5widgets5 libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m tupan
WORKDIR /app
COPY --from=build /src/build/tupan_sim  /app/
COPY --from=build /src/build/tupan_gui  /app/
COPY --from=build /src/build/tupan_tests /app/
COPY --from=build /src/build/tupan_native*.so /app/ 2>/dev/null || true
USER tupan
ENV PATH=/app:$PATH
CMD ["tupan_sim", "--help"]
