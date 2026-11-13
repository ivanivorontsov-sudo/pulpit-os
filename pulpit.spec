# -*- mode: python ; coding: utf-8 -*-
"""Сборка Pulpit.exe для Windows 11. CustomTkinter тащит свои данные сам."""

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ["pulpit", "pulpit.shell", "pulpit.engines", "pulpit.builder_app", "webview", "webview.platforms.edgechromium", "webview.platforms.winforms", "pythonnet", "clr_loader"]

for package in ("customtkinter", "PIL", "docx", "openpyxl", "pptx", "tkinterweb", "webview", "pythonnet", "clr_loader"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

datas += [("pulpit/web", "pulpit/web")]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pulpit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Pulpit",
)
