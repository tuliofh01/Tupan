#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tupan — ponto de entrada do serviço web para empacotamento standalone.
=============================================================================
DIDÁTICA: o Flask de desenvolvimento não é indicado para distribuição. Aqui
usamos o Waitress (WSGI de produção, multiplataforma) quando disponível e
caímos no servidor embutido do Flask caso contrário. Este arquivo é o alvo do
PyInstaller (packaging/tupan-web.spec), gerando UM executável que roda o
serviço sem exigir Python instalado no destino.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Garante que `simulador_tupan` (mesmo diretório) seja importável também no bundle.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from simulador_tupan import app  # noqa: E402


def main() -> None:
    host, port = "0.0.0.0", 5000
    try:
        from waitress import serve  # type: ignore[import-not-found]
        print(f"[tupan-web] waitress em http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        print(f"[tupan-web] servidor Flask embutido em http://{host}:{port}")
        app.run(host=host, port=port)


if __name__ == "__main__":
    main()
