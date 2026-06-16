"""播放器音频管理模块"""

from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, pyqtSignal, QObject


class AudioManager(QObject):
    """管理背景音乐和音量"""

    volume_changed = pyqtSignal(int, int)  # (video_volume, bgm_volume)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bgm_player = None
        self._bgm_output = None
        self._bgm_file = None
        self._bgm_volume = 60
        self._video_volume = 80

    @property
    def bgm_volume(self):
        return self._bgm_volume

    @bgm_volume.setter
    def bgm_volume(self, value: int):
        self._bgm_volume = max(0, min(100, value))
        if self._bgm_output:
            self._bgm_output.setVolume(self._bgm_volume / 100.0)

    @property
    def video_volume(self):
        return self._video_volume

    @video_volume.setter
    def video_volume(self, value: int):
        self._video_volume = max(0, min(100, value))
        self.volume_changed.emit(self._video_volume, self._bgm_volume)

    def set_bgm(self, file_path: str, volume: int = 60):
        """设置并循环播放背景音乐"""
        self.stop_bgm()

        if not file_path:
            return

        self._bgm_player = QMediaPlayer(self)
        self._bgm_output = QAudioOutput(self)
        self._bgm_player.setAudioOutput(self._bgm_output)
        self._bgm_player.setSource(QUrl.fromLocalFile(file_path))
        self._bgm_output.setVolume(volume / 100.0)
        self._bgm_volume = volume

        # 循环播放
        self._bgm_player.mediaStatusChanged.connect(self._on_bgm_status)
        self._bgm_player.play()

    def _on_bgm_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._bgm_player.setPosition(0)
            self._bgm_player.play()

    def stop_bgm(self):
        if self._bgm_player:
            try:
                self._bgm_player.mediaStatusChanged.disconnect()
            except TypeError:
                pass
            self._bgm_player.stop()
            self._bgm_player.deleteLater()
            self._bgm_player = None
        if self._bgm_output:
            self._bgm_output.deleteLater()
            self._bgm_output = None

    def pause_bgm(self):
        if self._bgm_player:
            self._bgm_player.pause()

    def resume_bgm(self):
        if self._bgm_player:
            self._bgm_player.play()