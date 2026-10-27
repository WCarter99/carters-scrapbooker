"""Build a standalone executable for the OS this runs on.

    python build.py

Creates .venv-build, installs requirements, runs PyInstaller and writes dist/CartersScrapbooker
(dist/CartersScrapbooker.exe on Windows). PyInstaller cannot cross-compile: build on Windows for
a Windows .exe, on macOS for a Mac app, on Linux for a Linux binary.
"""
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv-build"


def run(*cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT)


def main():
    if not VENV.exists():
        venv.create(VENV, with_pip=True)
    bindir = VENV / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / ("python.exe" if sys.platform == "win32" else "python")
    run(python, "-m", "pip", "install", "--quiet", "-r", "requirements-dev.txt")
    run(python, "-m", "PyInstaller", "--noconfirm", "--clean", "packaging/scrapbooker.spec")
    exe = ROOT / "dist" / ("CartersScrapbooker.exe" if sys.platform == "win32" else "CartersScrapbooker")
    print(f"\nBuilt: {exe}")


if __name__ == "__main__":
    main()
