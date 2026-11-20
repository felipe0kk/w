# PyInstaller spec for Windows (build on Windows)
from PyInstaller.utils.hooks import collect_submodules
hidden = collect_submodules("flask")
a = Analysis(
    ["app.py"], pathex=[], binaries=[], datas=[("templates", "templates"), ("static", "static")],
    hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="SteamKeyHunter",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)
