# NOESIS PyInstaller spec; build on the target OS with Python 3.14.
# Prefer onedir for debug/reproducibility. Do not add --uac-admin or real credentials.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[0]

hiddenimports = collect_submodules("noesis_harness")
datas = [
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (str(ROOT / "docs" / "third_party_provenance.json"), "docs"),
]

a = Analysis(
    [str(ROOT / "scripts" / "noesis_portable_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "models", "secrets"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="noesis-harness", debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="noesis-harness")
