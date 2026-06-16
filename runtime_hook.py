"""PyInstaller runtime hook — 在导入任何模块之前设置 DLL 搜索路径

关键：使用 os.add_dll_directory() 而不是 PATH 环境变量。
Windows 下 Python 3.8+ 的 DLL 加载机制优先使用 add_dll_directory()。
"""

import os
import sys


def _setup_dll_paths():
    meipass = sys._MEIPASS

    # 把 _MEIPASS 和 Qt bin 加到 DLL 搜索路径
    # os.add_dll_directory() 是最可靠的方式（Python 3.8+）
    dirs_to_add = [meipass]

    qt_bin = os.path.join(meipass, "PyQt6", "Qt6", "bin")
    if os.path.isdir(qt_bin):
        dirs_to_add.append(qt_bin)

    for d in dirs_to_add:
        try:
            os.add_dll_directory(os.path.abspath(d))
        except Exception:
            # 如果已添加或不被支持
            pass

    # 设置 Qt 插件路径（PyQt6 初始化时读取）
    qt_plugins = os.path.join(meipass, "PyQt6", "Qt6", "plugins")
    if os.path.isdir(qt_plugins):
        os.environ["QT_PLUGIN_PATH"] = qt_plugins
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(qt_plugins, "platforms")

    # 也设 PATH 作为双保险
    os.environ["PATH"] = meipass + os.pathsep + os.environ.get("PATH", "")
    if os.path.isdir(qt_bin):
        os.environ["PATH"] = qt_bin + os.pathsep + os.environ.get("PATH", "")


_setup_dll_paths()
del _setup_dll_paths