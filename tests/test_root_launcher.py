from __future__ import annotations

import os
import sqlite3
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The supported launcher is a Windows PowerShell entry point.")
def test_root_start_script_reaches_launcher_in_isolated_project_root(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parent.parent
    isolated_root = tmp_path / "project"
    scripts_dir = isolated_root / "scripts"
    python_scripts_dir = isolated_root / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    python_scripts_dir.mkdir(parents=True)

    for relative_path in (
        Path("start.ps1"),
        Path("scripts/start_ecobi.ps1"),
        Path("scripts/ecobi_launcher.py"),
        Path("scripts/ollama_bootstrap.ps1"),
    ):
        destination = isolated_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / relative_path, destination)

    python_executable = Path(sys.executable)
    shutil.copy2(python_executable, python_scripts_dir / "python.exe")
    venv_config = python_executable.parents[1] / "pyvenv.cfg"
    shutil.copy2(venv_config, isolated_root / ".venv" / "pyvenv.cfg")

    environment = os.environ.copy()
    site_packages = python_executable.parents[1] / "Lib" / "site-packages"
    environment["PYTHONPATH"] = os.pathsep.join((str(site_packages), str(project_root)))

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(isolated_root / "start.ps1"),
            "-CheckOnly",
            "-Port",
            "18086",
        ],
        cwd=isolated_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Runtime Python detectado" in result.stdout
    assert "Modo --check-only concluído com êxito." in result.stdout
    assert (isolated_root / "data" / "logs" / "ecobi.log").is_file()
    assert not (isolated_root / "data" / "runtime" / "ecobi.db").exists()
    canary_db = isolated_root / "data" / "runtime" / "ecobi.db"
    canary_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(canary_db) as connection:
        connection.execute("CREATE TABLE canary (value TEXT NOT NULL)")
        connection.execute("INSERT INTO canary VALUES (?)", ("preserve-me",))
    original_db_bytes = canary_db.read_bytes()

    preserve_result = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(isolated_root / "start.ps1"),
            "-CheckOnly",
            "-Port",
            "18086",
        ],
        cwd=isolated_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert preserve_result.returncode == 0, preserve_result.stdout + preserve_result.stderr
    assert "Modo --check-only concluído com êxito." in preserve_result.stdout
    assert canary_db.read_bytes() == original_db_bytes


@pytest.mark.skipif(sys.platform != "win32", reason="The supported launcher is a Windows PowerShell entry point.")
def test_start_ecobi_accepts_python_3_11_plus_and_checks_declared_imports(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parent.parent
    start_script = project_root / "scripts" / "start_ecobi.ps1"
    content = start_script.read_text(encoding="utf-8")

    assert "Resolve-EcoBIPythonLauncher" in content
    assert "'-3', '--version'" not in content
    assert "-3 --version" in content
    assert "[version]'3.11'" in content
    assert "httpx" in content

    ast_check = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "$errors = $null; "
                f"[void][System.Management.Automation.Language.Parser]::ParseFile('{project_root / 'start.ps1'}', [ref]$null, [ref]$errors); "
                "if ($errors) { throw ($errors | Out-String) }; "
                f"[void][System.Management.Automation.Language.Parser]::ParseFile('{start_script}', [ref]$null, [ref]$errors); "
                "if ($errors) { throw ($errors | Out-String) }; "
                "Write-Output 'AST_OK'"
            ),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert ast_check.returncode == 0, ast_check.stdout + ast_check.stderr
    assert "AST_OK" in ast_check.stdout
