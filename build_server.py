"""PyInstaller 打包脚本 — Server

生成:
    dist/signboard-server/  (--onedir, 推荐用于 Windows Server)
    dist/signboard-server.exe  (--onefile)

用法:
    python build_server.py           # 默认 onedir
    python build_server.py onefile   # 单文件模式
"""

import PyInstaller.__main__
import os
import sys
import shutil

root = os.path.dirname(os.path.abspath(__file__))

from build_common import get_qt6_paths, collect_binaries, verify_build

qt6_root, qt6_bin, qt6_plugins = get_qt6_paths()

# 收集 Qt6 二进制文件
binaries = collect_binaries(qt6_bin, qt6_plugins)

spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

binaries = {repr(binaries)}

a = Analysis(
    [r'{root}\\server\\main.py'],
    pathex=[r'{root}'],
    binaries=binaries,
    datas=[
        (r'{root}\\server\\templates', 'server/templates'),
        (r'{root}\\shared', 'shared'),
    ],
    hiddenimports=[
        "server.models",
        "server.api.media", "server.api.layout", "server.api.schedule",
        "server.api.display", "server.api.player_sync", "server.api.auth",
        "server.ppt_converter", "server.status_window",
        "sqlalchemy", "sqlalchemy.pool", "sqlalchemy.engine",
        "aiosqlite",
        "uvicorn", "uvicorn.loops.auto", "uvicorn.logging",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "fastapi", "starlette", "python_multipart",
        "PIL", "PIL.Image",
        "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "PyQt6.QtNetwork", "PyQt6.sip",
        "click", "pptx", "anyio", "h11", "websockets",
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
        name='signboard-server',
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
        name='signboard-server',
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
        name='signboard-server',
    )
'''

spec_path = os.path.join(root, "signboard-server.spec")
with open(spec_path, "w", encoding="utf-8") as f:
    f.write(spec_content)

# 用 spec 文件打包
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
dist_dir = os.path.join(root, "dist", "signboard-server")
internal_dir = os.path.join(dist_dir, "_internal")
checks = [
    ("signboard-server.exe", dist_dir, True),
    (os.path.join("server", "templates", "admin", "index.html"), internal_dir, True),
    (os.path.join("shared", "config.py"), internal_dir, True),
]

all_ok = verify_build(dist_dir, "signboard-server", checks)

if all_ok:
    # 检查 index.html 引用了 Vite 构建的 JS（SPA 模式下 auth 逻辑在 JS 里）
    index_path = os.path.join(internal_dir, "server", "templates", "admin", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "modulepreload" in content and "index-" in content:
        print(f"  [OK] index.html is Vite SPA build")

    # ---- 外置模板：复制到 exe 同级目录，支持免打包替换 ----
    ext_templates = os.path.join(dist_dir, "server", "templates", "admin")
    os.makedirs(ext_templates, exist_ok=True)
    src_admin = os.path.join(internal_dir, "server", "templates", "admin")
    src_index = os.path.join(src_admin, "index.html")
    src_assets = os.path.join(src_admin, "assets")
    dst_index = os.path.join(ext_templates, "index.html")
    dst_assets = os.path.join(ext_templates, "assets")

    shutil.copy2(src_index, dst_index)
    print(f"  [OK] External template: {dst_index}")

    # 同时复制 Vite 构建产物 assets/ 目录（JS/CSS）
    if os.path.isdir(src_assets):
        if os.path.isdir(dst_assets):
            # 先删除旧的，确保和 index.html 配套
            shutil.rmtree(dst_assets)
        shutil.copytree(src_assets, dst_assets)
        asset_count = sum(len(files) for _, _, files in os.walk(dst_assets))
        print(f"  [OK] External assets: {dst_assets} ({asset_count} files)")

    print(f"\nTo update frontend: edit {dst_index}")
    print(f"Then refresh browser, no repack needed.")