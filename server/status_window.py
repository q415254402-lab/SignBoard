"""Server 本地状态窗口（PyQt6）"""

import sys
import socket
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QPushButton, QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction, QFont


def get_local_ip():
    """获取本机内网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class StatusWindow(QMainWindow):
    def __init__(self, port: int, get_online_count_func):
        super().__init__()
        self.port = port
        self.get_online_count = get_online_count_func
        self.local_ip = get_local_ip()
        self.start_time = datetime.now()

        self.setWindowTitle("SignBoard 服务端")
        self.setFixedSize(420, 320)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        self._setup_ui()
        self._setup_tray()

        # 定时刷新
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(3000)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 标题
        title = QLabel("🖥️ SignBoard 数字标牌服务端")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 服务状态
        status_group = QGroupBox("服务状态")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("✅ 运行中")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.port_label = QLabel(f"端口: {self.port}")
        status_layout.addWidget(self.port_label)

        self.ip_label = QLabel(f"本机地址: {self.local_ip}")
        status_layout.addWidget(self.ip_label)

        self.url_label = QLabel(f"管理后台: http://{self.local_ip}:{self.port}")
        self.url_label.setStyleSheet("color: #0066cc;")
        self.url_label.setOpenExternalLinks(True)
        status_layout.addWidget(self.url_label)

        self.uptime_label = QLabel("运行时间: 0 分钟")
        status_layout.addWidget(self.uptime_label)

        layout.addWidget(status_group)

        # 屏幕状态
        screen_group = QGroupBox("屏幕状态")
        screen_layout = QVBoxLayout(screen_group)

        self.online_label = QLabel("在线屏幕: 0 台")
        self.online_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
        screen_layout.addWidget(self.online_label)

        self.last_refresh_label = QLabel("上次刷新: --")
        screen_layout.addWidget(self.last_refresh_label)

        layout.addWidget(screen_group)

        # 按钮
        btn_layout = QHBoxLayout()

        self.open_btn = QPushButton("🌐 打开管理后台")
        self.open_btn.clicked.connect(self._open_browser)
        btn_layout.addWidget(self.open_btn)

        self.minimize_btn = QPushButton("➖ 最小化到托盘")
        self.minimize_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.minimize_btn)

        layout.addLayout(btn_layout)

    def _setup_tray(self):
        """系统托盘图标"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("SignBoard 服务端")

        # 托盘菜单
        menu = QMenu()
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)

        open_action = QAction("打开管理后台", self)
        open_action.triggered.connect(self._open_browser)
        menu.addAction(open_action)

        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _open_browser(self):
        import webbrowser
        webbrowser.open(f"http://{self.local_ip}:{self.port}")

    def _refresh(self):
        count = self.get_online_count()
        self.online_label.setText(f"在线屏幕: {count} 台")

        uptime = datetime.now() - self.start_time
        minutes = int(uptime.total_seconds() / 60)
        if minutes < 60:
            self.uptime_label.setText(f"运行时间: {minutes} 分钟")
        else:
            hours = minutes // 60
            mins = minutes % 60
            self.uptime_label.setText(f"运行时间: {hours} 小时 {mins} 分钟")

        self.last_refresh_label.setText(f"上次刷新: {datetime.now().strftime('%H:%M:%S')}")

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘"""
        event.ignore()
        self.hide()

    def _quit(self):
        self.tray.hide()
        QApplication.quit()
