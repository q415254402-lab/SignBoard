"""播放列表布局基类"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import QTimer

from player.renderer import ImageRenderer, VideoRenderer


class BasePlaylistLayout(QWidget):
    """顺序播放布局基类 — FullscreenLayout 和 PlaylistLayout 的共同逻辑"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._zones = []
        self._media_paths = {}
        self._media_list = {}  # 完整的媒体信息（含 ppt_images 等）
        self._current_index = 0
        self._transition_ms = 800
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)

    def configure(self, zones: list, media_paths: dict, transition_ms: int = 800, media_list: dict = None):
        self._zones = zones
        self._media_paths = media_paths
        self._media_list = media_list or {}
        self._transition_ms = transition_ms
        self._current_index = 0
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
        media_id = zone.get("media_id")
        
        # 检查是否是 PPT 固定模式
        ppt_mode = zone.get("ppt_mode")
        if ppt_mode == "fixed":
            # 固定模式：一直显示，不轮播
            return 86400 * 1000  # 24小时（实际不会触发timer）
        
        # 检查是否是 PPT 轮播模式
        if media_id and media_id in self._media_list:
            media_info = self._media_list[media_id]
            ppt_images = media_info.get("ppt_images")
            if ppt_images:
                # PPT 轮播：使用 zone 设置的时长，或素材默认时长
                return zone.get("duration_seconds", media_info.get("ppt_slide_duration", 30)) * 1000
        
        # 普通素材：使用 zone 时长
        return zone.get("duration_seconds", 30) * 1000

    def _show_current(self):
        zone = self._zones[self._current_index]
        media_id = zone.get("media_id")
        if not media_id or media_id not in self._media_paths:
            return

        # 检查是否是 PPT 素材
        ppt_images = None
        ppt_mode = zone.get("ppt_mode")
        if media_id in self._media_list:
            media_info = self._media_list[media_id]
            ppt_images = media_info.get("ppt_images")

        # 确定要显示的图片路径
        if ppt_images and ppt_mode == "fixed":
            # 固定模式：显示指定页
            slide_index = zone.get("ppt_slide_index", 0)
            if slide_index < len(ppt_images):
                path = self._media_paths.get(media_id)
                # 替换为指定页的路径
                ppt_dir = ppt_images[0].rsplit("/", 1)[0] if "/" in ppt_images[0] else ""
                target_img = ppt_images[slide_index]
                local_path = self._media_paths.get(media_id, "").rsplit("/", 1)[0]
                if local_path:
                    path = f"{local_path}/{target_img.split('/')[-1]}"
            else:
                path = self._media_paths.get(media_id)
        elif ppt_images and ppt_mode != "fixed":
            # 轮播模式：根据当前 zone 的页码显示
            slide_index = zone.get("_ppt_slide_index", 0)
            if slide_index < len(ppt_images):
                target_img = ppt_images[slide_index]
                local_path = self._media_paths.get(media_id, "").rsplit("/", 1)[0]
                if local_path:
                    path = f"{local_path}/{target_img.split('/')[-1]}"
                else:
                    path = self._media_paths.get(media_id)
            else:
                path = self._media_paths.get(media_id)
        else:
            path = self._media_paths.get(media_id)

        if not path:
            return

        fill_mode = zone.get("fill_mode", "fill")
        is_video = path.lower().endswith(('.mp4', '.webm', '.mkv'))

        # 清除旧 widget
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            if hasattr(w, 'stop'):
                w.stop()
            w.deleteLater()

        if is_video:
            widget = VideoRenderer(self)
            widget.play_file(path, zone.get("volume", 80))
        else:
            widget = ImageRenderer(self)
            widget.set_image(path, fill_mode)

        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    def _next(self):
        zone = self._zones[self._current_index]
        media_id = zone.get("media_id")
        
        # 检查是否是 PPT 轮播模式
        ppt_images = None
        if media_id in self._media_list:
            media_info = self._media_list[media_id]
            ppt_images = media_info.get("ppt_images")
            ppt_mode = zone.get("ppt_mode")
        
        if ppt_images and ppt_mode != "fixed":
            # PPT 轮播：在同一 zone 内切换页码
            current_slide = zone.get("_ppt_slide_index", 0)
            if current_slide < len(ppt_images) - 1:
                # 还有下一页
                zone["_ppt_slide_index"] = current_slide + 1
            else:
                # 已到最后一页，切换到下一个 zone
                zone["_ppt_slide_index"] = 0
                self._current_index = (self._current_index + 1) % len(self._zones)
        else:
            # 普通素材：切换到下一个 zone
            self._current_index = (self._current_index + 1) % len(self._zones)
        
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
