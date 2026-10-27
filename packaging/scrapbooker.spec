# PyInstaller spec: run via `python build.py`
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent

datas = [(str(root / "templates"), "templates")]
if (root / "assets").exists():
    datas.append((str(root / "assets"), "assets"))
datas += collect_data_files("pygame_gui")  # default themes, fonts, translations

a = Analysis([str(root / "src" / "main.py")], pathex=[str(root / "src")], datas=datas,
             excludes=["tkinter", "pytest"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="CartersScrapbooker",
          console=False, upx=False)
