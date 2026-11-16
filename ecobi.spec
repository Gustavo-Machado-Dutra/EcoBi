# -*- mode: python ; coding: utf-8 -*-
"""Especificação PyInstaller para empacotamento executável do EcoBI Intelligence no Windows.

Gera um diretório ou executável autocontido com o backend FastAPI, Uvicorn, interface
web Sustainable Tech (frontend/) e bibliotecas analíticas locais.
"""

import sys
from pathlib import Path

block_cipher = None

root_dir = Path.cwd().resolve()

added_files = [
    (str(root_dir / "frontend"), "frontend"),
    (str(root_dir / "samples"), "samples"),
]

hidden_imports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "fastapi.staticfiles",
    "fastapi.responses",
    "starlette",
    "starlette.staticfiles",
    "starlette.responses",
    "pydantic",
    "sqlite3",
    "pandas",
    "numpy",
    "sklearn",
    "sklearn.ensemble",
    "sklearn.linear_model",
    "openpyxl",
    "multipart",
    "httpx",
    "psutil",
    "backend",
    "backend.config",
    "backend.database",
    "backend.security",
    "backend.memory_guard",
    "backend.main",
    "backend.services",
    "backend.services.data_quality",
    "backend.services.connectors",
    "backend.services.analytics",
    "backend.services.predictive",
    "backend.services.drift_monitor",
    "backend.services.recalibration",
    "backend.services.simulation",
    "backend.services.validation_engine",
    "backend.services.llm_agent",
    "backend.services.lora_evaluator",
    "backend.services.powerbi_generator",
    "backend.services.scheduler",
    "backend.services.multiproject",
]

a = Analysis(
    [str(root_dir / "scripts" / "ecobi_launcher.py")],
    pathex=[str(root_dir)],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "torch", "tensorflow"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EcoBI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EcoBI",
)
