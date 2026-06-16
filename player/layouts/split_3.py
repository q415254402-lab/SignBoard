"""上中下三分屏布局 — 顶部视频/图片 + 中间图片 + 底部走马灯"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt

from player.renderer import ImageRenderer, VideoRenderer, MarqueeWidget


class Split3Layout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._splitter = QSplitter(Qt.Orientation.Vertical)

        # 三块区域
        self._top = QWidget()
        self._top_layout = QVBoxLayout(self._top)
        self._top_layout.setContentsMargins(0, 0, 0, 0)

        self._middle = QWidget()
        self._middle_layout = QVBoxLayout(self._middle)
        self._middle_layout.setContentsMargins(0, 0, 0, 0)

        self._bottom = MarqueeWidget()

        self._splitter.addWidget(self._top)
        self._splitter.addWidget(self._middle)
        self._splitter.addWidget(self._bottom)

        layout.addWidget(self._splitter)

        self._top_renderer = None
        self._middle_renderer = None

        self._zones = []
        self._media_paths = {}
        self._marquee = None
        self._transition_ms = 800

    def configure(self, zones: list, media_paths: dict, marquee: dict = None,
                  transition_ms: int = 800):
        self._zones = zones
        self._media_paths = media_paths
        self._marquee = marquee
        self._transition_ms = transition_ms
        self._current_index = 0

        # 设置区域比例：顶部 45%，中间 45%，底部走马灯 10%
        total_h = self.height() or 1080
        self._splitter.setSizes([int(total_h * 0.45), int(total_h * 0.45), int(total_h * 0.10)])

        # 配置走马灯
        if marquee and marquee.get("text"):
            self._bottom.configure(
                text=marquee["text"],
                speed=marquee.get("speed", 60),
                font_size=marquee.get("font_size", 28),
                font_color=marquee.get("font_color", "#FFFFFF"),
                bg_color=marquee.get("bg_color", "#000000"),
                height_percent=marquee.get("height_percent", 8),
            )

        self._start()

    def _start(self):
        if len(self._zones) < 2:
            return
        self._show_current()

    def _show_current(self):
        # 顶部（视频/图片）
        zone_top = self._zones[0] if len(self._zones) > 0 else None
        if zone_top and zone_top.get("media_id"):
            path = self._media_paths.get(zone_top["media_id"])
            if path:
                fill_mode = zone_top.get("fill_mode", "fill")
                self._set_renderer("top", path, zone_top.get("volume", 80), fill_mode)

        # 中间（图片）
        zone_mid = self._zones[1] if len(self._zones) > 1 else None
        if zone_mid and zone_mid.get("media_id"):
            path = self._media_paths.get(zone_mid["media_id"])
            if path:
                fill_mode = zone_mid.get("fill_mode", "fill")
                self._set_renderer("middle", path, zone_mid.get("volume", 80), fill_mode)

    def _set_renderer(self, position: str, path: str, volume: int = 80, fill_mode: str = "fill"):
        is_video = path.lower().endswith(('.mp4', '.webm', '.mkv'))
        container = self._top if position == "top" else self._middle
        layout = self._top_layout if position == "top" else self._middle_layout
        attr = f"_{position}_renderer"

        old = getattr(self, attr)
        if old:
            layout.removeWidget(old)
            if hasattr(old, 'stop'):
                old.stop()
            old.deleteLater()

        if is_video:
            widget = VideoRenderer(container)
            widget.play_file(path, volume)
        else:
            widget = ImageRenderer(container)
            widget.set_image(path, fill_mode)

        layout.addWidget(widget)
        setattr(self, attr, widget)

    def stop(self):
        for pos in ('top', 'middle'):
            w = getattr(self, f"_{pos}_renderer")
            if w:
                if hasattr(w, 'stop'):
                    w.stop()
                w.deleteLater()