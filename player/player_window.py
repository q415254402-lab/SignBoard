"""播放器主窗口 — 全屏播放"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

from player.layouts.fullscreen import FullscreenLayout
from player.layouts.playlist import PlaylistLayout
from player.layouts.split_2 import Split2Layout
from player.layouts.split_3 import Split3Layout
from player.sync import PlayerSync
from player.audio import AudioManager


class PlayerWindow(QWidget):
    def __init__(self, server_url: str, display_id: int = 0):
        super().__init__()
        self.server_url = server_url
        self.display_id = display_id
        self._current_layout_key = None
        self._current_layout_widget = None
        self._sync = None
        self._audio = AudioManager(self)

        self.setWindowTitle("SignBoard Player")
        self.setStyleSheet("background: black;")

        # 全屏 + 隐藏鼠标
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.showFullScreen()

        # 提示加载中
        self._layout_container = QVBoxLayout(self)
        self._layout_container.setContentsMargins(0, 0, 0, 0)
        self._loading_label = QLabel("正在连接服务器...")
        self._loading_label.setStyleSheet("color: white; font-size: 24px;")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout_container.addWidget(self._loading_label)

        # 启动同步
        self._setup_sync()

    def _setup_sync(self):
        self._sync = PlayerSync(self.server_url, self.display_id, self)
        self._sync_failed = False
        self._offline_label = None

        # 1. 先连信号
        self._sync.connection_changed.connect(self._on_connection_changed)
        self._sync.schedule_updated.connect(self._on_schedule_updated)

        # 2. 再注册
        if self.display_id == 0:
            result = self._sync.register()
            if result:
                self.display_id = result["id"]
                self._sync.display_id = self.display_id
            else:
                self._sync_failed = True
                self._on_connection_changed("error", f"无法注册到服务器\n{self.server_url}")

        # 3. 立即触发首次同步（不等 30 秒定时器）
        # _do_sync 内部会自动尝试离线 fallback
        self._sync.first_sync()

    def _on_connection_changed(self, state: str, message: str):
        """连接状态变化"""
        if state == "error":
            self._sync_failed = True
            # 如果已经在播放，不显示全屏 loading，用角落提示
            if self._loading_label is None:
                self._show_offline_indicator(message)
                return

        if state == "connected":
            self._sync_failed = False
            self._hide_offline_indicator()

        if not self._loading_label:
            return  # 已经在播放了，不需要更新 loading

        if state == "connecting":
            self._loading_label.setText(f"⏳ {message}")
            self._loading_label.setStyleSheet("color: white; font-size: 20px;")
        elif state == "connected":
            self._loading_label.setText(f"🟢 {message}\n等待排程下发...")
            self._loading_label.setStyleSheet("color: #4ade80; font-size: 20px;")
        elif state == "error":
            self._loading_label.setText(f"🔴 {message}\n30秒后自动重试...")
            self._loading_label.setStyleSheet("color: #f87171; font-size: 20px;")

    def _show_offline_indicator(self, message: str):
        """角落显示离线模式提示（不影响播放）"""
        if not self._offline_label:
            self._offline_label = QLabel("⚠ 离线模式", self)
            self._offline_label.setStyleSheet(
                "background: rgba(239,68,68,0.85); color: white; "
                "padding: 4px 12px; border-radius: 4px; font-size: 14px;"
            )
            self._offline_label.adjustSize()
            self._offline_label.move(10, 10)
        self._offline_label.show()

    def _hide_offline_indicator(self):
        """隐藏离线提示"""
        if self._offline_label:
            self._offline_label.deleteLater()
            self._offline_label = None

    def _on_schedule_updated(self, data: dict):
        """收到新的排程数据"""
        layout = data.get("current_layout")
        force_refresh = data.get("_force_refresh", False)

        if not layout:
            # 无排程
            if force_refresh and self._current_layout_widget:
                # 从离线恢复但服务器已无排程 → 清除旧布局，显示提示
                if hasattr(self._current_layout_widget, 'stop'):
                    self._current_layout_widget.stop()
                self._layout_container.removeWidget(self._current_layout_widget)
                self._current_layout_widget.deleteLater()
                self._current_layout_widget = None
                self._current_layout_key = None
                # 重建 loading 提示
                self._loading_label = QLabel("🟢 已连接\n暂无排程，请在管理后台创建")
                self._loading_label.setStyleSheet("color: #4ade80; font-size: 20px;")
                self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout_container.addWidget(self._loading_label)
            elif self._loading_label:
                self._loading_label.setText("🟢 已连接\n暂无排程，请在管理后台创建")
                self._loading_label.setStyleSheet("color: #4ade80; font-size: 20px;")
            return

        # 构建 media_id -> 本地路径映射
        media_paths = {}
        media_list_map = {}  # media_id -> 完整媒体信息
        for m in data.get("media_list", []):
            local = self._sync.get_media_path(m["id"])
            if local:
                media_paths[m["id"]] = local
            media_list_map[m["id"]] = m

        # 用排程 ID + 布局 ID + 更新时间做变更检测（排程变更也触发刷新）
        schedule = data.get("current_schedule")
        schedule_id = schedule.get("id", "") if schedule else ""
        layout_key = f"{schedule_id}_{layout['id']}_{layout.get('updated_at', layout.get('created_at', ''))}"
        if layout_key == self._current_layout_key and not force_refresh:
            return

        # 素材全部下载失败时，保留旧布局，不清屏
        if force_refresh and not media_paths and self._current_layout_widget:
            return

        self._current_layout_key = layout_key
        self._switch_layout(layout, media_paths, media_list_map)

    def _switch_layout(self, layout: dict, media_paths: dict, media_list: dict = None):
        """切换布局"""
        # 标记进入播放状态
        if self._sync:
            self._sync.mark_playing()

        # 隐藏加载提示
        if self._loading_label:
            self._loading_label.hide()
            self._layout_container.removeWidget(self._loading_label)
            self._loading_label = None

        # 清除旧布局
        if self._current_layout_widget:
            if hasattr(self._current_layout_widget, 'stop'):
                self._current_layout_widget.stop()
            self._layout_container.removeWidget(self._current_layout_widget)
            self._current_layout_widget.deleteLater()

        layout_type = layout["type"]
        zones = layout.get("zones", [])
        marquee = layout.get("marquee")
        split_ratio = layout.get("split_ratio", "1:1")
        transition_ms = layout.get("transition_duration_ms", 800)
        bgm_media_id = layout.get("bgm_media_id")
        bgm_volume = layout.get("bgm_volume", 60)

        # 根据类型创建布局
        if layout_type == "fullscreen" or layout_type == "webpage":
            widget = FullscreenLayout(self)
            widget.configure(zones, media_paths, transition_ms, media_list)
        elif layout_type == "playlist":
            widget = PlaylistLayout(self)
            widget.configure(zones, media_paths, transition_ms, media_list)
        elif layout_type == "split_2":
            widget = Split2Layout(self)
            widget.configure(zones, media_paths, split_ratio, transition_ms)
        elif layout_type == "split_3":
            widget = Split3Layout(self)
            widget.configure(zones, media_paths, marquee, transition_ms)
        else:
            return

        self._layout_container.addWidget(widget)
        self._current_layout_widget = widget

        # 背景音乐
        if bgm_media_id and bgm_media_id in media_paths:
            self._audio.set_bgm(media_paths[bgm_media_id], bgm_volume)
        else:
            self._audio.stop_bgm()

    def keyPressEvent(self, event):
        """按 Esc 退出全屏（调试用）"""
        if event.key() == Qt.Key.Key_Escape:
            self._cleanup()
            self.close()

    def closeEvent(self, event):
        self._cleanup()
        event.accept()

    def _cleanup(self):
        if self._sync:
            self._sync.stop()
        if self._current_layout_widget and hasattr(self._current_layout_widget, 'stop'):
            self._current_layout_widget.stop()
        self._audio.stop_bgm()