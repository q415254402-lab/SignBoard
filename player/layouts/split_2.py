"""左右二分屏布局 — 支持 1:1 和 16:9 比例，百分比定位"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from player.renderer import ImageRenderer, VideoRenderer


class Split2Layout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._left = QWidget(self)
        self._left_layout = QVBoxLayout(self._left)
        self._left_layout.setContentsMargins(0, 0, 0, 0)

        self._right = QWidget(self)
        self._right_layout = QVBoxLayout(self._right)
        self._right_layout.setContentsMargins(0, 0, 0, 0)

        self._left_renderer = None
        self._right_renderer = None

        self._zones = []
        self._media_paths = {}
        self._transition_ms = 800
        self._ratio = "1:1"
        self._left_pct = 0.5

    def configure(self, zones: list, media_paths: dict, ratio: str = "1:1",
                  transition_ms: int = 800):
        self._zones = zones
        self._media_paths = media_paths
        self._ratio = ratio
        self._transition_ms = transition_ms

        # 设置比例
        if ratio == "16:9":
            self._left_pct = 0.64
        else:
            self._left_pct = 0.5

        self._show_current()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_zones()

    def _layout_zones(self):
        """根据百分比计算并设置两个区域的几何位置"""
        w, h = self.width(), self.height()
        left_w = int(w * self._left_pct)
        self._left.setGeometry(0, 0, left_w, h)
        self._right.setGeometry(left_w, 0, w - left_w, h)

    def _show_current(self):
        # 左区域
        zone_l = self._zones[0] if len(self._zones) > 0 else None
        if zone_l and zone_l.get("media_id"):
            path = self._media_paths.get(zone_l["media_id"])
            if path:
                fill_mode = zone_l.get("fill_mode", "fill")
                self._set_renderer("left", path, zone_l.get("volume", 80), fill_mode)

        # 右区域
        zone_r = self._zones[1] if len(self._zones) > 1 else None
        if zone_r and zone_r.get("media_id"):
            path = self._media_paths.get(zone_r["media_id"])
            if path:
                fill_mode = zone_r.get("fill_mode", "fill")
                self._set_renderer("right", path, zone_r.get("volume", 80), fill_mode)

        self._layout_zones()

    def _set_renderer(self, side: str, path: str, volume: int = 80, fill_mode: str = "fill"):
        is_video = path.lower().endswith(('.mp4', '.webm', '.mkv'))
        container = self._left if side == "left" else self._right
        layout = self._left_layout if side == "left" else self._right_layout

        # 清除旧的
        attr = f"_{side}_renderer"
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
        for side in ('left', 'right'):
            attr = f"_{side}_renderer"
            w = getattr(self, attr)
            if w:
                if hasattr(w, 'stop'):
                    w.stop()
                w.deleteLater()
