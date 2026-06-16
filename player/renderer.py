"""播放器渲染引擎 — 负责在 QWidget 上渲染图片/视频/走马灯"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class MarqueeWidget(QWidget):
    """走马灯文字滚动组件"""

    # 字体回退链：优先系统字体，最后 fallback
    FONT_FALLBACKS = [
        "Microsoft YaHei",   # Windows 中文
        "PingFang SC",       # macOS 中文
        "Noto Sans CJK SC", # Linux 中文
        "WenQuanYi Micro Hei",
        "SimHei",
        "Arial",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._speed = 60  # px/s
        self._font_size = 28
        self._font_color = QColor("#FFFFFF")
        self._bg_color = QColor("#000000")
        self._offset = 0
        self._text_width = 0
        self._font_family = self._detect_font()
        self.setFixedHeight(60)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scroll)
        self._timer.start(30)  # ~33fps

    @classmethod
    def _detect_font(cls) -> str:
        """检测系统可用的中文字体"""
        from PyQt6.QtGui import QFontDatabase
        available = QFontDatabase.families()
        for font_name in cls.FONT_FALLBACKS:
            if font_name in available:
                return font_name
        return ""  # 使用 Qt 默认字体

    def configure(self, text: str, speed: int = 60, font_size: int = 28,
                  font_color: str = "#FFFFFF", bg_color: str = "#000000",
                  height_percent: int = 8):
        self._text = text
        self._speed = speed
        self._font_size = font_size
        self._font_color = QColor(font_color)
        self._bg_color = QColor(bg_color)

        # 计算文本宽度
        font = QFont(self._font_family, font_size) if self._font_family else QFont(font_size)
        fm = QFontMetrics(font)
        self._text_width = fm.horizontalAdvance(text) if text else 0

        if not text:
            self._timer.stop()
        elif not self._timer.isActive():
            self._timer.start(30)

        self.update()

    def _scroll(self):
        if not self._text:
            return
        self._offset -= self._speed / 33.0  # 30ms per frame
        if self._offset < -self._text_width:
            self._offset = self.width()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), self._bg_color)

        if not self._text:
            return

        # 文字
        font = QFont(self._font_family, self._font_size) if self._font_family else QFont(self._font_size)
        painter.setFont(font)
        painter.setPen(self._font_color)

        y = (self.height() + self._font_size) // 2 - 4
        painter.drawText(int(self._offset), y, self._text)


class ImageRenderer(QWidget):
    """图片渲染器（支持淡入淡出）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = None
        self._current_pixmap = None
        self._next_pixmap = None
        self._fill_mode = "fill"
        self._opacity = 1.0
        self._fading = False
        self._transition_duration = 800

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

    def set_image(self, filepath: str, fill_mode: str = "fill"):
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            return
        self._original_pixmap = pixmap
        self._fill_mode = fill_mode
        self._rescale()

    def _rescale(self):
        """根据当前 widget 尺寸重新缩放图片"""
        if not self._original_pixmap or self.width() <= 0 or self.height() <= 0:
            return
        if self._fill_mode == "fill":
            scaled = self._original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            self._current_pixmap = scaled.copy(x, y, self.width(), self.height())
        elif self._fill_mode == "stretch":
            self._current_pixmap = self._original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:  # fit
            self._current_pixmap = self._original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def transition_to(self, filepath: str, duration_ms: int = 800):
        """淡入淡出切换图片"""
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            return

        self._next_pixmap = pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._transition_duration = duration_ms

        # 淡出
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(duration_ms // 2)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_fade_out_done)
        self._anim.start()

    def _on_fade_out_done(self):
        self._current_pixmap = self._next_pixmap
        self._next_pixmap = None
        self.update()

        # 淡入
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(self._transition_duration // 2)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._current_pixmap:
            x = (self.width() - self._current_pixmap.width()) // 2
            y = (self.height() - self._current_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._current_pixmap)


class VideoRenderer(QWidget):
    """视频渲染器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)

        self._video_widget = QVideoWidget(self)
        self._player.setVideoOutput(self._video_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._video_widget)

        self._player.mediaStatusChanged.connect(self._on_status)

    def set_volume(self, vol: int):
        self._audio.setVolume(vol / 100.0)

    def play_file(self, filepath: str, volume: int = 80):
        self._audio.setVolume(volume / 100.0)
        self._player.setSource(QUrl.fromLocalFile(filepath))
        self._player.play()

    def stop(self):
        self._player.stop()

    def _on_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.setPosition(0)
            self._player.play()  # 循环播放

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._video_widget.setGeometry(self.rect())


class WebpageRenderer(QWidget):
    """网页渲染组件 — 使用 QWebEngineView 显示网页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self._web_view = None
        self._fallback_label = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            self._web_view = QWebEngineView(self)
            self._web_view.setZoomFactor(1.0)
            layout.addWidget(self._web_view)
        except ImportError:
            # QWebEngineView 不可用，降级为显示 URL
            self._fallback_label = QLabel(self)
            self._fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._fallback_label.setStyleSheet("color: #888; font-size: 14px;")
            layout.addWidget(self._fallback_label)

    def configure(self, url: str):
        """加载网页"""
        self._url = url
        if not url:
            if self._fallback_label:
                self._fallback_label.setText("未配置网页地址")
            return

        if self._web_view:
            self._web_view.setUrl(QUrl(url))
        elif self._fallback_label:
            self._fallback_label.setText(f"网页: {url}\n(QWebEngineView 不可用)")

    def reload(self):
        """刷新网页"""
        if self._web_view and self._url:
            self._web_view.reload()