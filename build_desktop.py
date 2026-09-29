#!/usr/bin/env python3
"""
Script automatizado de compilação e empacotamento com PyInstaller.
Gera um executável standalone (zero-setup) para distribuição aos usuários finais.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


def main():
    root_dir = Path(__file__).resolve().parent
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    print("=" * 70)
    print("Iniciando Empacotamento Desktop do CorujaSync")
    print("=" * 70)

    # Limpa compilações anteriores
    if dist_dir.exists():
        shutil.rmtree(dist_dir, ignore_errors=True)
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "CorujaSync",
        "--collect-all",
        "customtkinter",
        "--collect-all",
        "rich",
        "--hidden-import",
        "core",
        "--hidden-import",
        "browser",
        "--hidden-import",
        "legal",
        "--hidden-import",
        "ui",
        "--hidden-import",
        "ui.gui",
        "--hidden-import",
        "ui.gui.dialogs",
        "--hidden-import",
        "ui.gui.views",
        "--hidden-import",
        "ui.cli",
        "--add-data",
        f"{root_dir / 'core' / 'selectors.json'}{os.pathsep}core",
        str(root_dir / "main.py"),
    ]

    # No Windows podemos adicionar --windowed se desejado
    if sys.platform == "win32":
        cmd.append("--windowed")

    print(f"Executando comando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(root_dir))

    if result.returncode == 0:
        print("\n" + "=" * 70)
        print("[✓] Compilação concluída com sucesso!")
        print(f"O executável gerado encontra-se em: {dist_dir / 'CorujaSync'}")
        print("=" * 70)
    else:
        print("\n[✗] Falha durante a compilação do executável.", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
