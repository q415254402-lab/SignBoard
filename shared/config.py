"""共享配置"""

import os
import sys

# 获取程序运行目录
# PyInstaller 打包后: sys.frozen=True, sys.executable 是 exe 路径
#                 资源在 sys._MEIPASS 临时目录
# 开发环境: sys.frozen=False
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)          # exe 所在目录（数据存这）
    RESOURCE_DIR = sys._MEIPASS                          # 打包内嵌资源目录
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESOURCE_DIR = BASE_DIR

# 默认配置
DEFAULT_CONFIG = {
    # 服务器
    "server_host": "0.0.0.0",
    "server_port": 8000,
    "api_prefix": "/api/v1",

    # 素材
    "upload_dir": "uploads",
    "max_upload_size_mb": 500,
    "allowed_image_types": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
    "allowed_video_types": ["mp4", "webm", "mkv"],
    "allowed_doc_types": ["pptx", "ppt"],

    # 播放器
    "sync_interval_seconds": 30,
    "heartbeat_interval_seconds": 30,
    "heartbeat_timeout_minutes": 1,

    # 默认管理员
    "default_admin_password": "china-sand12",
    "screenshot_interval_seconds": 60,
    "screenshot_quality": 75,

    # 过渡动画
    "transition_duration_ms": 800,

    # 走马灯
    "marquee_speed_default": 60,
    "marquee_font_size_default": 28,
    "marquee_font_color_default": "#FFFFFF",
    "marquee_bg_color_default": "#000000",

    # 数据库
    "db_path": "data/signboard.db",

    # Player 本地缓存
    "player_cache_dir": "player_cache",
}


def get_config_path():
    """配置文件路径"""
    return os.path.join(BASE_DIR, "config.json")


def get_db_path():
    """数据库文件路径"""
    db_path = os.environ.get("SIGNBOARD_DB_PATH", DEFAULT_CONFIG["db_path"])
    if not os.path.isabs(db_path):
        db_path = os.path.join(BASE_DIR, db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def get_upload_dir():
    """素材上传目录"""
    upload_dir = os.environ.get("SIGNBOARD_UPLOAD_DIR", DEFAULT_CONFIG["upload_dir"])
    if not os.path.isabs(upload_dir):
        upload_dir = os.path.join(BASE_DIR, upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def get_player_cache_dir():
    """Player 本地缓存目录"""
    cache_dir = os.path.join(BASE_DIR, DEFAULT_CONFIG["player_cache_dir"])
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(os.path.join(cache_dir, "media"), exist_ok=True)
    os.makedirs(os.path.join(cache_dir, "logs"), exist_ok=True)
    return cache_dir


def get_templates_dir():
    """管理后台模板目录（外置优先，内置 fallback）

    打包部署时，exe 同级的 server/templates/ 优先于打包内嵌的模板。
    这样改前端 HTML 不用重新打包 EXE。
    """
    # 1. exe 同级目录的 server/templates（外置，可随时替换）
    external = os.path.join(BASE_DIR, "server", "templates")
    if os.path.isdir(external):
        return external
    # 2. 打包内嵌的（PyInstaller _MEIPASS）
    return os.path.join(RESOURCE_DIR, "server", "templates")