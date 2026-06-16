"""播放列表布局 — 多个素材按各自设定的时长顺序全屏播放"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import QTimer

from player.renderer import ImageRenderer, VideoRenderer


class PlaylistLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._zones = []
        self._media_paths = {}
        self._current_index = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)

    def configure(self, zones: list, media_paths: dict, transition_ms: int = 800, media_list: dict = None):
        self._zones = zones
        self._media_paths = media_paths
        self._transition_ms = transition_ms
        self._current_index = 0
        self._start()

    def _start(self):
        if not self._zones:
            return
        self._show_current()
        duration = self._zones[self._current_index].get("duration_seconds", 30) * 1000
        self._timer.start(duration)

    def _show_current(self):
        zone = self._zones[self._current_index]
        media_id = zone.get("media_id")
        if not media_id or media_id not in self._media_paths:
            return

        path = self._media_paths[media_id]
        fill_mode = zone.get("fill_mode", "fill")
        is_video = path.lower().endswith(('.mp4', '.webm', '.mkv'))

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
        self._current_index = (self._current_index + 1) % len(self._zones)
        self._show_current()
        duration = self._zones[self._current_index].get("duration_seconds", 30) * 1000
        self._timer.start(duration)

    def stop(self):
        self._timer.stop()
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            if hasattr(w, 'stop'):
                w.stop()
            w.deleteLater()