"""SignBoard 播放器主入口

启动方式:
    signboard-player.exe --server 192.168.1.100:8000
    signboard-player.exe --server 192.168.1.100:8000 --name "一楼大厅"
    
    直接双击 exe → 弹出配置窗口输入服务器地址
"""

import sys
import os
import argparse
import json

# ============================================================
# PyInstaller 打包时，runtime_hook.py 在 bootloader 阶段设置好了
# Qt6 的 DLL 搜索路径和插件路径。这里不需要重复设置。
# ============================================================

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from shared.config import BASE_DIR


# ---- 配置对话框 ----

class SetupDialog(QDialog):
    """首次启动/配置服务器地址的对话框"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SignBoard Player — 连接配置")
        self.setFixedSize(480, 320)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )
        self._server_url = ""
        self._display_name = ""
        self._load_saved_config()

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        # 标题
        title = QLabel("📺 SignBoard 播放器")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("请配置 CMS 服务器连接信息")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # 服务器地址
        server_label = QLabel("服务器地址:")
        server_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(server_label)

        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("例如: 192.168.3.254 或 192.168.3.254:8000")
        self.server_input.setText(self._server_url)
        self.server_input.setMinimumHeight(36)
        layout.addWidget(self.server_input)

        # 屏幕名称
        name_label = QLabel("屏幕名称 (可选):")
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: 一楼大厅（留空则使用计算机名）")
        self.name_input.setText(self._display_name)
        self.name_input.setMinimumHeight(36)
        layout.addWidget(self.name_input)

        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.connect_btn = QPushButton("连接")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        self.connect_btn.clicked.connect(self._on_connect)
        btn_layout.addWidget(self.connect_btn)

        layout.addLayout(btn_layout)

        # 状态提示
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #ef4444;")
        layout.addWidget(self.status_label)

    def _load_saved_config(self):
        """加载上次保存的配置"""
        config_path = os.path.join(BASE_DIR, "player_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._server_url = cfg.get("server_url", "")
                self._display_name = cfg.get("display_name", "")
        except Exception:
            pass

    def _save_config(self):
        """保存配置"""
        config_path = os.path.join(BASE_DIR, "player_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "server_url": self.server_input.text().strip(),
                    "display_name": self.name_input.text().strip(),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_connect(self):
        """点击连接按钮"""
        server = self.server_input.text().strip()
        if not server:
            self.status_label.setText("请输入服务器地址")
            return

        # 格式化 URL
        if not server.startswith("http"):
            server = "http://" + server
        # 补默认端口
        host_part = server.replace("http://", "").replace("https://", "").split("/")[0]
        if ":" not in host_part:
            server = server + ":8000"

        self._server_url = server
        self._display_name = self.name_input.text().strip()
        self._save_config()
        self.accept()

    def get_server_url(self) -> str:
        return self._server_url

    def get_display_name(self) -> str:
        return self._display_name


# ---- 主入口 ----

def main():
    # 先解析命令行参数（允许 --server 缺失）
    parser = argparse.ArgumentParser(description="SignBoard 播放器")
    parser.add_argument("--server", type=str, default=None, help="CMS 服务器地址 (ip:port)")
    parser.add_argument("--name", type=str, default=None, help="屏幕名称（可选）")
    parser.add_argument("--id", type=int, default=0, help="已注册的屏幕 ID")
    parser.add_argument("--config", action="store_true", help="强制显示配置窗口")
    args = parser.parse_args()

    try:
        # 在创建 QApplication 前，手动添加 Qt 插件路径
        # 解决打包后目标机器找不到 Qt 插件的问题
        if getattr(sys, 'frozen', False):
            from PyQt6.QtCore import QCoreApplication
            internal_dir = os.path.join(os.path.dirname(sys.executable), '_internal')
            if not os.path.isdir(internal_dir):
                internal_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            qt_plugins = os.path.join(internal_dir, 'PyQt6', 'Qt6', 'plugins')
            if os.path.isdir(qt_plugins):
                QCoreApplication.addLibraryPath(qt_plugins)

        app = QApplication(sys.argv)
    except ImportError as e:
        print(f"[ERROR] 无法加载 Qt 图形界面组件: {e}")
        print("[ERROR] 播放器需要 Windows 桌面环境（Player 不支持纯命令行模式）")
        print("[ERROR] 请确保运行在 Windows 10/11 桌面版，而非 Windows Server Core")
        sys.exit(1)

    app.setApplicationName("SignBoard Player")
    server_url = args.server
    display_name = args.name

    # 加载已保存的配置
    saved_config_path = os.path.join(BASE_DIR, "player_config.json")
    saved_cfg = {}
    if os.path.exists(saved_config_path):
        try:
            with open(saved_config_path, "r", encoding="utf-8") as f:
                saved_cfg = json.load(f)
        except Exception:
            pass

    # 决定 server_url 来源：命令行 > 保存的配置 > 弹窗
    if server_url is None and not args.config:
        # 命令行没指定，尝试用已保存的配置
        if saved_cfg.get("server_url"):
            server_url = saved_cfg["server_url"]
            display_name = display_name or saved_cfg.get("display_name", "")

    if server_url is None or args.config:
        # 没有已保存配置 或 强制 --config，弹出配置窗口
        dialog = SetupDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            server_url = dialog.get_server_url()
            display_name = dialog.get_display_name() or display_name
        else:
            return

    # 格式化 server_url
    if not server_url.startswith("http"):
        server_url = "http://" + server_url
    host_part = server_url.replace("http://", "").replace("https://", "").split("/")[0]
    if ":" not in host_part:
        server_url = server_url + ":8000"

    # 注册/获取 display_id
    display_id = args.id
    if display_id == 0:
        from player.sync import PlayerSync
        sync = PlayerSync(server_url, 0)
        result = sync.register(display_name)
        if result:
            display_id = result["id"]
            print(f"已注册为屏幕 ID: {display_id} ({result['name']})")
        else:
            # 注册失败，尝试从缓存恢复 display_id
            cached_info = sync.load_display_info()
            if cached_info and cached_info.get("display_id"):
                display_id = cached_info["display_id"]
                print(f"服务器不可达，使用缓存的屏幕 ID: {display_id}")
            else:
                # 无缓存，首次启动必须连服务器
                QMessageBox.warning(
                    None, "连接失败",
                    f"无法连接到服务器:\n{server_url}\n\n首次启动需要连接服务器注册屏幕。\n请检查网络后重试。"
                )
                sync.stop()
                return
        sync.stop()

    # 启动主窗口（无论服务器是否在线都启动）
    from player.player_window import PlayerWindow
    window = PlayerWindow(server_url, display_id)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()