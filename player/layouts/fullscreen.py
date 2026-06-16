"""全屏轮播布局 — 支持 PPT 多页轮播"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import QTimer

from player.renderer import ImageRenderer, VideoRenderer


class FullscreenLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._zones = []
        self._media_paths = {}     # media_id -> local path
        self._media_list = {}      # media_id -> media info (含 ppt_images)
        self._current_index = 0
        self._ppt_slide_index = 0  # PPT 当前页码
        self._transition_ms = 800
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)

    def configure(self, zones: list, media_paths: dict, transition_ms: int = 800, media_list: dict = None):
        self._zones = zones
        self._media_paths = media_paths
        self._media_list = media_list or {}
        self._transition_ms = transition_ms
        self._current_index = 0
        self._ppt_slide_index = 0
        self._start()

    def _start(self):
        if not self._zones:
            return
        self._show_current()
        duration = self._get_current_duration()
        self._timer.start(duration)

    def _get_current_duration(self):
        """获取当前素材的播放时长"""
        zone = self._zones[self._current_index]

        # 网页组件：使用 zone 时长
        if zone.get("url"):
            return zone.get("duration_seconds", 30) * 1000

        media_id = zone.get("media_id")

        # 检查是否是 PPT 固定模式
        ppt_mode = zone.get("ppt_mode")
        if ppt_mode == "fixed":
            return 86400 * 1000  # 固定模式：24小时（不自动切换）

        # 检查是否是 PPT 轮播模式
        if media_id and media_id in self._media_list:
            media_info = self._media_list[media_id]
            ppt_images = media_info.get("ppt_images")
            if ppt_images:
                return zone.get("duration_seconds", media_info.get("ppt_slide_duration", 30)) * 1000

        # 普通素材：使用 zone 时长
        return zone.get("duration_seconds", 30) * 1000

    def _show_current(self):
        zone = self._zones[self._current_index]
        media_id = zone.get("media_id")
        url = zone.get("url")

        # 清除旧 widget
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            if hasattr(w, 'stop'):
                w.stop()
            w.deleteLater()

        # 网页组件
        if url:
            from player.renderer import WebpageRenderer
            widget = WebpageRenderer(self)
            widget.configure(url)
            self._stack.addWidget(widget)
            return

        if not media_id or media_id not in self._media_paths:
            return

        # 确定要显示的图片路径
        path = self._get_display_path(zone, media_id)
        if not path:
            return

        fill_mode = zone.get("fill_mode", "fill")
        is_video = path.lower().endswith(('.mp4', '.webm', '.mkv'))

        if is_video:
            widget = VideoRenderer(self)
            widget.play_file(path, zone.get("volume", 80))
        else:
            widget = ImageRenderer(self)
            widget.set_image(path, fill_mode)

        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    def _get_display_path(self, zone, media_id):
        """获取当前应显示的文件路径（支持PPT多页）"""
        media_info = self._media_list.get(media_id, {})
        ppt_images = media_info.get("ppt_images")
        ppt_mode = zone.get("ppt_mode")

        if ppt_images and ppt_mode == "fixed":
            # 固定模式：显示指定页
            slide_index = zone.get("ppt_slide_index", 0)
            if slide_index < len(ppt_images):
                return self._get_ppt_slide_path(media_id, ppt_images[slide_index])
            return self._media_paths.get(media_id)

        if ppt_images and ppt_mode != "fixed":
            # 轮播模式：根据当前页码显示
            if self._ppt_slide_index < len(ppt_images):
                return self._get_ppt_slide_path(media_id, ppt_images[self._ppt_slide_index])
            return self._media_paths.get(media_id)

        # 普通素材
        return self._media_paths.get(media_id)

    def _get_ppt_slide_path(self, media_id, slide_path):
        """获取 PPT 幻灯片的本地路径"""
        base_path = self._media_paths.get(media_id, "")
        if not base_path:
            return None
        # slide_path 格式: "ppt_xxx/slide_001.png"
        # base_path 格式: "C:/cache/media/ppt_xxx/slide_001.png"
        # 需要替换文件名为 slide_path 中的文件名
        parent_dir = os.path.dirname(base_path)
        filename = slide_path.split("/")[-1]
        local_path = os.path.join(parent_dir, filename)
        if os.path.exists(local_path):
            return local_path
        return base_path  # fallback

    def _next(self):
        zone = self._zones[self._current_index]

        # 检查是否是 PPT 轮播模式
        media_id = zone.get("media_id")
        media_info = self._media_list.get(media_id, {})
        ppt_images = media_info.get("ppt_images")
        ppt_mode = zone.get("ppt_mode")

        if ppt_images and ppt_mode != "fixed":
            # PPT 轮播：在同一 zone 内切换页码
            if self._ppt_slide_index < len(ppt_images) - 1:
                # 还有下一页
                self._ppt_slide_index += 1
            else:
                # 已到最后一页，切换到下一个 zone
                self._ppt_slide_index = 0
                self._current_index = (self._current_index + 1) % len(self._zones)
        else:
            # 普通素材：切换到下一个 zone
            self._current_index = (self._current_index + 1) % len(self._zones)
            self._ppt_slide_index = 0

        self._show_current()
        duration = self._get_current_duration()
        self._timer.start(duration)

    def stop(self):
        self._timer.stop()
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            if hasattr(w, 'stop'):
                w.stop()
            w.deleteLater()
