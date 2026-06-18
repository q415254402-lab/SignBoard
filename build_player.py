"""PyInstaller 打包脚本 — Player

生成:
    dist/signboard-player/  (--onedir, 推荐)
    dist/signboard-player.exe  (--onefile)

用法:
    python build_player.py           # 默认 onedir
    python build_player.py onefile   # 单文件模式
"""

import PyInstaller.__main__
import os
import sys

root = os.path.dirname(os.path.abspath(__file__))

from build_common import get_qt6_paths, collect_binaries, collect_ffmpeg_dlls, verify_build

qt6_root, qt6_bin, qt6_plugins = get_qt6_paths()

# 收集 Qt6 二进制文件（含 FFmpeg 和 multimedia 插件）
binaries = collect_binaries(
    qt6_bin, qt6_plugins,
    extra_core_dlls=["Qt6Multimedia.dll", "Qt6MultimediaWidgets.dll"],
    extra_plugins=["multimedia"]
)
binaries.extend(collect_ffmpeg_dlls(qt6_bin))

spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

binaries = {repr(binaries)}

a = Analysis(
    [r'{root}\\player\\main.py'],
    pathex=[r'{root}'],
    binaries=binaries,
    datas=[
        (r'{root}\\shared', 'shared'),
    ],
    hiddenimports=[
        "player.player_window", "player.renderer", "player.sync", "player.audio",
        "player.layouts.fullscreen", "player.layouts.playlist",
        "player.layouts.split_2", "player.layouts.split_3",
        "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtNetwork", "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
        "PyQt6.sip",
        "PIL", "PIL.Image",
        "httpx", "anyio", "httpcore", "certifi", "h11",
        "requests", "urllib3",
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[r'{root}\\runtime_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

mode = "{"onedir" if len(sys.argv) <= 1 or sys.argv[1] != "onefile" else "onefile"}"

if mode == "onefile":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='signboard-player',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='signboard-player',
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
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='signboard-player',
    )
'''

spec_path = os.path.join(root, "signboard-player.spec")
with open(spec_path, "w", encoding="utf-8") as f:
    f.write(spec_content)

mode = sys.argv[1] if len(sys.argv) > 1 else "onedir"
print(f"Mode: {mode}")
print(f"Spec: {spec_path}")
print()

PyInstaller.__main__.run([
    spec_path,
    f"--distpath={os.path.join(root, 'dist')}",
    "--clean",
    "--noconfirm",
])

# ---- 打包后验证 ----
dist_dir = os.path.join(root, "dist", "signboard-player")
internal_dir = os.path.join(dist_dir, "_internal")
checks = [
    ("signboard-player.exe", dist_dir, True),
    (os.path.join("shared", "config.py"), internal_dir, True),
]

verify_build(dist_dir, "signboard-player", checks)