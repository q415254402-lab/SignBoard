"""PyInstaller 共享工具 — Server 和 Player 构建脚本共用的 DLL 收集逻辑"""

import os


def get_qt6_paths():
    """获取 PyQt6 安装路径"""
    import PyQt6
    qt6_root = os.path.dirname(PyQt6.__file__)
    qt6_bin = os.path.join(qt6_root, "Qt6", "bin")
    qt6_plugins = os.path.join(qt6_root, "Qt6", "plugins")
    return qt6_root, qt6_bin, qt6_plugins


def collect_binaries(qt6_bin, qt6_plugins, extra_core_dlls=None, extra_plugins=None):
    """收集 Qt6 相关的二进制文件（DLL、插件）

    Args:
        qt6_bin: Qt6 bin 目录
        qt6_plugins: Qt6 plugins 目录
        extra_core_dlls: 额外的核心 DLL 名称列表（如 Qt6Multimedia.dll）
        extra_plugins: 额外的插件目录名列表（如 ["multimedia"]）

    Returns:
        list of (src, dest) 元组
    """
    binaries = []

    # VC++ 运行时 DLL (打包到根目录)
    vc_dlls = [
        "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
        "msvcp140_atomic_wait.dll", "msvcp140_codecvt_ids.dll",
        "vcruntime140.dll", "vcruntime140_1.dll", "vcruntime140_threads.dll",
        "concrt140.dll",
    ]
    for dll_name in vc_dlls:
        dll_path = os.path.join(qt6_bin, dll_name)
        if os.path.exists(dll_path):
            binaries.append((dll_path, "."))

    # Qt6 platforms plugin (关键! 否则 Qt 无法启动)
    platforms_dir = os.path.join(qt6_plugins, "platforms")
    for f in os.listdir(platforms_dir):
        if f.endswith(".dll"):
            binaries.append(
                (os.path.join(platforms_dir, f), "PyQt6/Qt6/plugins/platforms")
            )

    # Qt6 styles
    styles_dir = os.path.join(qt6_plugins, "styles")
    for f in os.listdir(styles_dir):
        if f.endswith(".dll"):
            binaries.append(
                (os.path.join(styles_dir, f), "PyQt6/Qt6/plugins/styles")
            )

    # Qt6 imageformats
    imgf_dir = os.path.join(qt6_plugins, "imageformats")
    for f in os.listdir(imgf_dir):
        if f.endswith(".dll"):
            binaries.append(
                (os.path.join(imgf_dir, f), "PyQt6/Qt6/plugins/imageformats")
            )

    # 额外插件目录（如 multimedia）
    if extra_plugins:
        for plugin_name in extra_plugins:
            plugin_dir = os.path.join(qt6_plugins, plugin_name)
            if os.path.isdir(plugin_dir):
                for f in os.listdir(plugin_dir):
                    if f.endswith(".dll"):
                        binaries.append(
                            (os.path.join(plugin_dir, f), f"PyQt6/Qt6/plugins/{plugin_name}")
                        )

    # Qt6 核心 DLL
    core_dlls = [
        "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll",
        "Qt6Network.dll", "Qt6OpenGL.dll", "Qt6OpenGLWidgets.dll",
        "Qt6Svg.dll", "Qt6DBus.dll",
    ]
    if extra_core_dlls:
        core_dlls.extend(extra_core_dlls)

    for dll_name in core_dlls:
        dll_path = os.path.join(qt6_bin, dll_name)
        if os.path.exists(dll_path):
            binaries.append((dll_path, "PyQt6/Qt6/bin"))

    # 额外: 把 Qt6 bin 下剩余 DLL 全部打包
    already_collected = set()
    for src, _ in binaries:
        already_collected.add(os.path.basename(src))

    for f in os.listdir(qt6_bin):
        if f.endswith(".dll") and f not in already_collected:
            binaries.append((os.path.join(qt6_bin, f), "PyQt6/Qt6/bin"))

    return binaries


def collect_ffmpeg_dlls(qt6_bin):
    """收集 FFmpeg 编解码 DLL（Player 视频播放需要）"""
    binaries = []
    ffmpeg_dlls = [
        "avcodec-61.dll", "avformat-61.dll", "avutil-59.dll",
        "swresample-5.dll", "swscale-8.dll", "avdevice-61.dll", "avfilter-10.dll",
    ]
    for dll_name in ffmpeg_dlls:
        dll_path = os.path.join(qt6_bin, dll_name)
        if os.path.exists(dll_path):
            binaries.append((dll_path, "."))
    return binaries


def verify_build(dist_dir, exe_name, checks):
    """打包后验证

    Args:
        dist_dir: 输出目录
        exe_name: 可执行文件名
        checks: [(rel_path, base, required), ...] 检查项

    Returns:
        bool: 是否全部通过
    """
    print()
    print("=" * 50)
    print("打包验证")
    print("=" * 50)

    all_ok = True
    for rel_path, base, required in checks:
        full = os.path.join(base, rel_path)
        exists = os.path.exists(full)
        status = "[OK]" if exists else ("[FAIL]" if required else "[SKIP]")
        print(f"  {status} {rel_path}")
        if required and not exists:
            all_ok = False

    if all_ok:
        size_mb = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, filenames in os.walk(dist_dir)
            for f in filenames
        ) / 1024 / 1024
        print(f"  Size: {size_mb:.0f} MB")
        print(f"\nBuild OK: {dist_dir}")
    else:
        print(f"\nBuild may be incomplete, check errors above")

    return all_ok
