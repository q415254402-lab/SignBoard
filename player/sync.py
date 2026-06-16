"""播放器同步/心跳/截图模块"""

import os
import json
import time
import threading
import logging

import httpx
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QMetaObject, Qt, pyqtSlot
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap

from shared.config import get_player_cache_dir, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class PlayerSync(QObject):
    """负责与 CMS 通信：SSE 实时推送 + 轮询排程 + 上报心跳 + 上传截图"""

    schedule_updated = pyqtSignal(dict)   # emit 新的 sync 响应
    connection_changed = pyqtSignal(str, str)  # (state, message)  state: connecting/connected/no_schedule/error/offline
    screenshot_taken = pyqtSignal(str)    # emit 截图本地路径

    _sse_disconnected = pyqtSignal()      # SSE 断开信号 → 恢复轮询

    def __init__(self, server_url: str, display_id: int, parent=None):
        super().__init__(parent)
        self.server_url = server_url.rstrip("/")
        self.display_id = display_id
        self.cache_dir = get_player_cache_dir()
        self.media_cache_dir = os.path.join(self.cache_dir, "media")
        self._http = httpx.Client(timeout=15.0)
        self._player_token = self._load_player_token()

        # 定时轮询排程（SSE 断开时的降级方案）
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._do_sync)
        self._sync_timer.setInterval(DEFAULT_CONFIG["sync_interval_seconds"] * 1000)

        # 定时截图
        self._screenshot_timer = QTimer(self)
        self._screenshot_timer.timeout.connect(self._take_screenshot)
        self._screenshot_timer.start(DEFAULT_CONFIG["screenshot_interval_seconds"] * 1000)

        # SSE 相关
        self._sse_thread: threading.Thread | None = None
        self._sse_running = threading.Event()
        self._sse_connected = threading.Event()
        self._sse_disconnected.connect(self._on_sse_disconnected)

        # 当前缓存状态
        self._last_schedule = None
        self._last_layout = None
        self._cached_media = {}
        self._is_playing = False
        self._display_name = ""
        self._offline_mode = False  # 离线模式标志
        self._remote_control = None  # 延迟初始化
        self._cache_file = os.path.join(self.cache_dir, "last_sync.json")
        self._display_info_file = os.path.join(self.cache_dir, "display_info.json")

    def _load_player_token(self) -> str:
        """从 player_config.json 加载 player token"""
        config_path = os.path.join(os.path.dirname(self.cache_dir), "player_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get("player_token", "")
        except Exception:
            pass
        return ""

    def _get_headers(self) -> dict:
        """获取带认证的请求头"""
        headers = {}
        if self._player_token:
            headers["X-Player-Token"] = self._player_token
        return headers

    # ── SSE 实时监听 ─────────────────────────────────────────────
    def _start_sse(self):
        """启动 SSE 后台监听线程"""
        if self._sse_running.is_set():
            return
        self._sse_running.set()
        self._sse_thread = threading.Thread(target=self._listen_sse, daemon=True)
        self._sse_thread.start()

    def _listen_sse(self):
        """SSE 长连接线程：监听 /player/events/{display_id}"""
        url = f"{self.server_url}/api/v1/player/events/{self.display_id}"
        backoff = 1  # 重连退避秒数

        while self._sse_running.is_set():
            try:
                with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0)) as client:
                    with client.stream("GET", url, headers=self._get_headers()) as resp:
                        if resp.status_code != 200:
                            time.sleep(min(backoff, 60))
                            backoff *= 2
                            continue

                        self._sse_connected.set()
                        backoff = 1  # 重置退避

                        # 解析 SSE 事件（event + data 可能跨多行，空行分隔事件）
                        event_type = None
                        data_str = None
                        for line in resp.iter_lines():
                            if not self._sse_running.is_set():
                                break
                            if not line or line.startswith(":"):
                                # 空行 = 事件结束，处理已收集的数据
                                if event_type and data_str:
                                    self._process_sse_event(event_type, data_str)
                                event_type = None
                                data_str = None
                                continue
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:"):
                                data_str = line[5:].strip()
                        # 处理最后一个事件（如果连接断开时没有空行）
                        if event_type and data_str:
                            self._process_sse_event(event_type, data_str)

                        # iter_lines 结束 = 连接正常断开
                        self._sse_connected.clear()
                        if self._sse_running.is_set():
                            self._resume_polling()
                            time.sleep(min(backoff, 60))
                            backoff *= 2

            except httpx.ConnectError:
                self._sse_connected.clear()
                if self._sse_running.is_set():
                    self._resume_polling()
                    time.sleep(min(backoff, 60))
                    backoff *= 2
            except httpx.TimeoutException:
                self._sse_connected.clear()
                if self._sse_running.is_set():
                    self._resume_polling()
                    time.sleep(min(backoff, 60))
                    backoff *= 2
            except Exception as e:
                logger.debug(f"SSE 连接异常: {e}")
                self._sse_connected.clear()
                if self._sse_running.is_set():
                    self._resume_polling()
                    time.sleep(5)

    def _process_sse_event(self, event_type: str, data_str: str):
        """处理 SSE 事件"""
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return

        if event_type == "command":
            cmd = data.get("command", "")
            if cmd:
                logger.info(f"SSE 收到指令: {cmd}")
                # 立即执行命令（在 SSE 线程中直接调用，RemoteControl 是线程安全的）
                self._handle_command(cmd)
                # 同时触发一次同步刷新状态
                self._trigger_sync_on_main()
        elif event_type == "refresh":
            # 布局/排程变更，触发同步
            self._trigger_sync_on_main()
        elif event_type == "sync":
            # 紧急插播等，触发同步
            self._trigger_sync_on_main()

    def _trigger_sync_on_main(self):
        """从 SSE 线程触发 Qt 主线程执行同步"""
        try:
            QMetaObject.invokeMethod(
                self, "_do_sync",
                Qt.ConnectionType.QueuedConnection
            )
        except Exception:
            pass  # Qt 对象可能已被销毁

    def _pause_polling(self):
        """暂停轮询定时器（SSE 已连接时）"""
        try:
            self._sync_timer.stop()
        except Exception:
            pass

    @pyqtSlot()
    def _resume_polling(self):
        """恢复轮询定时器（SSE 断开后）"""
        try:
            if not self._sync_timer.isActive():
                self._sync_timer.start()
        except Exception:
            pass

    @pyqtSlot()
    def _on_sse_disconnected(self):
        """SSE 断开后的回调（由 _sse_disconnected 信号触发）"""
        self._resume_polling()

    def _stop_sse(self):
        """停止 SSE 监听"""
        self._sse_running.clear()
        # 不需要 join；daemon 线程会自然退出
        self._sse_thread = None

    # ── 同步逻辑 ─────────────────────────────────────────────────
    def _do_sync(self):
        """拉取最新排程"""
        if not self._is_playing:
            self.connection_changed.emit("connecting", "正在连接服务器...")
        try:
            resp = self._http.get(
                f"{self.server_url}/api/v1/player/sync/{self.display_id}",
                headers=self._get_headers(),
            )
            if resp.status_code != 200:
                self.connection_changed.emit("error", f"服务器错误 ({resp.status_code})")
                self._try_offline_fallback()
                return
            data = resp.json()
        except httpx.ConnectError:
            self.connection_changed.emit("error", f"无法连接到服务器\n{self.server_url}")
            self._try_offline_fallback()
            return
        except httpx.TimeoutException:
            self.connection_changed.emit("error", "连接超时")
            self._try_offline_fallback()
            return
        except Exception as e:
            self.connection_changed.emit("error", f"连接失败: {str(e)}")
            self._try_offline_fallback()
            return

        # 连接成功 — 退出离线模式
        was_offline = self._offline_mode
        if self._offline_mode:
            self._offline_mode = False

        self.connection_changed.emit("connected", "已连接")

        # 同步服务器端修改的设备名称
        new_name = data.get("display_name", "")
        if new_name and new_name != self._display_name:
            old_name = self._display_name
            self._display_name = new_name
            # 持久化到本地配置
            try:
                from shared.config import get_config_path
                import json
                cfg_path = get_config_path()
                cfg = {}
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                cfg["display_name"] = new_name
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                logger.info(f"设备名称已同步: {old_name} -> {new_name}")
            except Exception:
                pass

        # 检查并下载素材
        for media in data.get("media_list", []):
            # 文件不在本地时才下载（支持重试失败的下载）
            local_path = os.path.join(self.media_cache_dir, media["file_path"])
            if not os.path.exists(local_path):
                self._download_media(media)
            # 下载 PPT 所有图片
            ppt_images = media.get("ppt_images")
            if ppt_images:
                for img_path in ppt_images:
                    local_img_path = os.path.join(self.media_cache_dir, img_path)
                    if not os.path.exists(local_img_path):
                        self._download_media({"file_path": img_path})
            self._cached_media[media["id"]] = media

        # 检查指令
        for cmd in data.get("commands", []):
            self._handle_command(cmd)

        # 缓存到磁盘（离线恢复用）— 不保存临时标记
        cache_data = {k: v for k, v in data.items() if not k.startswith("_")}
        self._save_sync_cache(cache_data)

        # 通知窗口：离线恢复后需要强制刷新布局
        if was_offline:
            data["_force_refresh"] = True

        # 触发更新
        self.schedule_updated.emit(data)

    def _try_offline_fallback(self):
        """连接失败时尝试加载本地缓存继续播放"""
        if self._offline_mode:
            return  # 已经在离线模式了，不重复 emit

        cached = self.load_cached_sync()
        if not cached or not cached.get("current_layout"):
            return

        # 检查缓存的素材是否存在于本地
        media_list = cached.get("media_list", [])
        has_media = False
        for m in media_list:
            local_path = os.path.join(self.media_cache_dir, m["file_path"])
            if os.path.exists(local_path):
                has_media = True
            # 无论文件是否存在，都填充 _cached_media
            # 让 get_media_path() 能查到元数据
            self._cached_media[m["id"]] = m

        if has_media:
            self._offline_mode = True
            self.schedule_updated.emit(cached)

    def _download_media(self, media: dict):
        """下载素材到本地缓存"""
        file_path = media["file_path"]
        local_path = os.path.join(self.media_cache_dir, file_path)

        if os.path.exists(local_path):
            return local_path

        try:
            resp = self._http.get(
                f"{self.server_url}/api/v1/player/download/{file_path}",
                headers=self._get_headers(),
            )
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(resp.content)
        except Exception as e:
            logger.warning(f"素材下载失败: {file_path} - {e}")

        return local_path

    def get_media_path(self, media_id: int) -> str | None:
        """获取本地缓存的素材路径"""
        media = self._cached_media.get(media_id)
        if not media:
            return None
        local_path = os.path.join(self.media_cache_dir, media["file_path"])
        if os.path.exists(local_path):
            return local_path
        return None

    def _take_screenshot(self):
        """截取当前屏幕"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                pixmap = screen.grabWindow(0)
                filepath = os.path.join(self.cache_dir, "screenshot.jpg")
                pixmap.save(filepath, quality=DEFAULT_CONFIG["screenshot_quality"])
                self._upload_screenshot(filepath)
        except Exception as e:
            logger.warning(f"截图失败: {e}")

    def take_screenshot_now(self):
        """立即截图"""
        self._take_screenshot()

    def _upload_screenshot(self, filepath: str):
        """上传截图到 CMS"""
        try:
            with open(filepath, "rb") as f:
                files = {"file": ("screenshot.jpg", f, "image/jpeg")}
                self._http.post(
                    f"{self.server_url}/api/v1/displays/{self.display_id}/screenshot",
                    files=files,
                    headers=self._get_headers(),
                )
        except Exception as e:
            logger.debug(f"截图上传失败: {e}")

    def _get_remote_control(self):
        """获取 RemoteControl 单例（保持状态）"""
        if self._remote_control is None:
            from player.remote_control import RemoteControl
            self._remote_control = RemoteControl()
        return self._remote_control

    def _handle_command(self, cmd: str):
        """处理 CMS 下发的指令"""
        control = self._get_remote_control()

        if cmd == "restart":
            control.restart()
        elif cmd == "screenshot":
            self._take_screenshot()
        elif cmd == "screen_off":
            control.screen_off()
        elif cmd == "screen_on" or cmd == "wake_up":
            control.screen_on()

    def _get_mac_address(self) -> str:
        """获取本机 MAC 地址"""
        import uuid
        mac = uuid.getnode()
        return ':'.join(f'{(mac >> i) & 0xFF:02x}' for i in range(0, 48, 8))

    def register(self, name: str = None):
        """向 CMS 注册屏幕（首次启动）"""
        import socket
        hostname = name or socket.gethostname()
        try:
            screen = QApplication.primaryScreen()
            if screen:
                # 获取物理分辨率（考虑 DPI 缩放）
                ratio = screen.devicePixelRatio()
                logical = screen.size()
                w = int(logical.width() * ratio)
                h = int(logical.height() * ratio)
            else:
                w, h = 0, 0
            ip = self._get_local_ip()
            mac = self._get_mac_address()
            resp = self._http.post(
                f"{self.server_url}/api/v1/displays/register",
                json={"name": hostname, "group_name": "default",
                       "screen_width": w, "screen_height": h,
                       "platform": "windows", "ip_address": ip,
                       "mac_address": mac},
            )
            if resp.status_code == 200:
                data = resp.json()
                self.display_id = data["id"]
                # 保存 player_token（如果服务端返回了）
                if "player_token" in data:
                    self._player_token = data["player_token"]
                    self._save_player_token(self._player_token)
                self._save_display_info(data)
                return data
        except Exception as e:
            logger.warning(f"屏幕注册失败: {e}")
        return None

    def _save_player_token(self, token: str):
        """保存 player_token 到 player_config.json"""
        config_path = os.path.join(os.path.dirname(self.cache_dir), "player_config.json")
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            config["player_token"] = token
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 player_token 失败: {e}")

    def _save_sync_cache(self, data: dict):
        """将同步数据保存到磁盘"""
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception:
            pass

    def load_cached_sync(self) -> dict | None:
        """从磁盘加载上次同步数据（离线恢复用）"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_display_info(self, data: dict):
        """缓存注册信息到磁盘"""
        try:
            info = {
                "display_id": data.get("id"),
                "name": data.get("name"),
                "server_url": self.server_url,
            }
            with open(self._display_info_file, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_display_info(self) -> dict | None:
        """从磁盘加载注册信息（离线恢复用）"""
        try:
            if os.path.exists(self._display_info_file):
                with open(self._display_info_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def mark_playing(self):
        """标记已进入播放状态（抑制连接状态提示）"""
        self._is_playing = True

    def first_sync(self):
        """立即触发首次同步 + 启动 SSE 监听 + 启动轮询定时器"""
        self._do_sync()
        self._start_sse()
        # 确保轮询定时器启动（SSE 负责即时通知，轮询兜底排程变更）
        if not self._sync_timer.isActive():
            self._sync_timer.start()

    def _get_local_ip(self) -> str:
        """获取本机 IP 地址"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return ""

    def stop(self):
        self._sse_running.clear()
        self._sync_timer.stop()
        self._screenshot_timer.stop()
        self._http.close()
