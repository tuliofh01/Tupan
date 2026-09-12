# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
#  TUPAN — PyInstaller spec do serviço web (executável único, onefile)
#  ---------------------------------------------------------------------------
#  Empacota tools/server (Flask + templates) e, se já compilado, o módulo
#  nativo `tupan_native*.so` (senão o servidor usa o fallback Python puro).
#  Uso: scripts/build-standalone.sh   (ou: python3 -m PyInstaller packaging/tupan-web.spec)
# ============================================================================
from pathlib import Path
import glob

PACKAGING = Path(SPECPATH).resolve()          # .../packaging
BASE = PACKAGING.parent                        # raiz do repositório
SERVER = BASE / "tools" / "server"

datas = [(str(SERVER / "templates"), "templates")]
for so in glob.glob(str(BASE / "build" / "tupan_native*")):
    datas.append((so, "."))                    # módulo nativo, se existir

a = Analysis(
    [str(SERVER / "run_server.py")],
    pathex=[str(SERVER)],
    binaries=[],
    datas=datas,
    hiddenimports=["simulador_tupan"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "PIL", "pptx", "docx", "pandas", "sklearn"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="tupan-web",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
