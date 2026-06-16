"""Pydantic 数据模型（API 请求/响应）"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ============ 枚举 ============

class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    PPT = "ppt"


class LayoutType(str, Enum):
    FULLSCREEN = "fullscreen"       # 全屏轮播
    PLAYLIST = "playlist"           # 播放列表
    WEBPAGE = "webpage"             # 网页组件
    SPLIT_2 = "split_2"             # 左右二分屏
    SPLIT_3 = "split_3"             # 上中下三分屏


class SplitRatio(str, Enum):
    RATIO_1_1 = "1:1"
    RATIO_16_9 = "16:9"


class FillMode(str, Enum):
    FIT = "fit"          # 保持比例，可能有黑边
    FILL = "fill"        # 保持比例，裁切超出，无黑边
    STRETCH = "stretch"  # 拉伸填满


class DisplayStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


# ============ 素材 ============

class MediaOut(BaseModel):
    id: int
    name: str
    type: MediaType
    file_path: str
    thumbnail_path: Optional[str] = None
    duration_seconds: Optional[int] = None  # 视频时长（秒）
    file_size: int
    width: Optional[int] = None   # 图片/视频宽度
    height: Optional[int] = None  # 图片/视频高度
    ppt_images: Optional[list[str]] = None  # PPT 所有图片路径
    ppt_slide_duration: int = 30  # PPT 每页默认播放时长（秒）
    expires_at: Optional[datetime] = None  # 素材过期时间
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 布局 ============

class ZoneConfig(BaseModel):
    """布局中一个区域的配置"""
    media_id: Optional[int] = None
    x: float = Field(default=0.0, ge=0.0, le=1.0)    # 区域左边界 (0.0-1.0)
    y: float = Field(default=0.0, ge=0.0, le=1.0)    # 区域上边界 (0.0-1.0)
    w: float = Field(default=1.0, ge=0.0, le=1.0)    # 区域宽度 (0.0-1.0)
    h: float = Field(default=1.0, ge=0.0, le=1.0)    # 区域高度 (0.0-1.0)
    duration_seconds: int = Field(default=30, ge=1, le=86400)  # 素材播放时长
    volume: int = Field(default=80, ge=0, le=100)     # 音量 0-100
    fill_mode: FillMode = FillMode.FILL  # 素材填充模式
    # PPT 播放配置
    ppt_mode: Optional[str] = None  # loop=轮播, fixed=固定
    ppt_slide_index: Optional[int] = None  # fixed模式下指定页码（0开始）
    # 网页组件配置
    url: Optional[str] = None  # 网页地址


class MarqueeConfig(BaseModel):
    """走马灯配置"""
    text: str = ""
    speed: int = Field(default=60, ge=1, le=1000)  # px/s
    font_size: int = Field(default=28, ge=8, le=200)
    font_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    bg_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    height_percent: int = Field(default=8, ge=1, le=50)  # 占屏幕高度的百分比


class LayoutCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: LayoutType
    zones: list[ZoneConfig] = []          # 区域配置
    marquee: Optional[MarqueeConfig] = None  # 走马灯（仅 split_3）
    split_ratio: SplitRatio = SplitRatio.RATIO_1_1  # 二分屏比例
    bgm_media_id: Optional[int] = None    # 背景音乐素材ID
    bgm_volume: int = Field(default=60, ge=0, le=100)  # 背景音乐音量
    transition_duration_ms: int = Field(default=800, ge=0, le=10000)  # 过渡动画时长
    resolution_width: int = Field(default=1920, ge=320, le=7680)  # 布局分辨率-宽
    resolution_height: int = Field(default=1080, ge=240, le=4320)  # 布局分辨率-高


class LayoutOut(BaseModel):
    id: int
    name: str
    type: LayoutType
    zones: list[ZoneConfig]
    marquee: Optional[MarqueeConfig]
    split_ratio: SplitRatio
    bgm_media_id: Optional[int]
    bgm_volume: int
    transition_duration_ms: int
    resolution_width: int
    resolution_height: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 排程 ============

class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    layout_id: int
    display_ids: list[int] = []     # 目标屏幕 ID 列表，空 = 全部
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None  # None = 无限
    priority: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True
    # 重复排程
    repeat_type: str = Field(default="none", pattern=r"^(none|daily|weekly|monthly)$")  # none / daily / weekly / monthly
    repeat_days: Optional[list[int]] = None  # [1,3,5] 周一三五
    repeat_start_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")  # "08:00"
    repeat_end_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")    # "18:00"
    repeat_until: Optional[datetime] = None  # 重复截止日期


class ScheduleOut(BaseModel):
    id: int
    name: str
    layout_id: int
    display_ids: list[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    priority: int
    is_active: bool
    repeat_type: str = "none"
    repeat_days: Optional[list[int]] = None
    repeat_start_time: Optional[str] = None
    repeat_end_time: Optional[str] = None
    repeat_until: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 屏幕 ============

class DisplayRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mac_address: Optional[str] = Field(default=None, max_length=50)
    group_name: str = Field(default="default", max_length=100)
    license_key: Optional[str] = Field(default=None, max_length=100)
    screen_width: Optional[int] = Field(default=None, ge=0, le=15360)
    screen_height: Optional[int] = Field(default=None, ge=0, le=8640)
    platform: Optional[str] = Field(default=None, max_length=20)  # windows / android
    ip_address: Optional[str] = Field(default=None, max_length=50)  # 设备 IP


class DisplayOut(BaseModel):
    id: int
    name: str
    mac_address: Optional[str]
    group_name: str
    status: DisplayStatus
    last_heartbeat: Optional[datetime]
    current_layout_id: Optional[int]
    screenshot_updated_at: Optional[datetime]
    last_screenshot: Optional[str] = None  # 最新截图文件名
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    screen_orientation: Optional[str] = None
    platform: Optional[str] = None  # windows / android
    ip_address: Optional[str] = None  # 设备 IP
    created_at: datetime

    class Config:
        from_attributes = True


class HeartbeatData(BaseModel):
    display_id: int
    current_layout_id: Optional[int] = None
    current_media_id: Optional[int] = None
    player_version: str = Field(default="1.0.0", max_length=20)
    platform: Optional[str] = None
    ip_address: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None


# ============ Player 拉取响应 ============

class SyncResponse(BaseModel):
    """Player 轮询时返回的数据"""
    display_id: int
    display_name: str = ""          # 设备名称（前端可修改）
    current_schedule: Optional[ScheduleOut] = None
    current_layout: Optional[LayoutOut] = None
    media_list: list[MediaOut] = []
    commands: list[str] = []       # ["restart", "screenshot"]
    server_time: datetime


class PlayerCommand(str, Enum):
    """Player 支持的命令白名单"""
    RESTART = "restart"
    SCREENSHOT = "screenshot"
    SCREEN_OFF = "screen_off"      # 熄屏
    SCREEN_ON = "screen_on"        # 唤醒
    WAKE_UP = "wake_up"            # 唤醒（同 screen_on）


class CommandRequest(BaseModel):
    """CMS 发送给 Player 的指令"""
    command: PlayerCommand
    display_ids: list[int]


# ============ 开关机计划 ============

class PowerScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_ids: list[int] = []
    on_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    off_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    power_days: str = Field(default="1,2,3,4,5", max_length=50)
    is_enabled: bool = True


class PowerScheduleOut(BaseModel):
    id: int
    name: str
    display_ids: list[int]
    on_time: Optional[str]
    off_time: Optional[str]
    power_days: str
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PowerSchedulePatch(BaseModel):
    is_enabled: Optional[bool] = None


# ============ 下发记录 ============

class CommandLogOut(BaseModel):
    id: int
    display_id: Optional[int]
    display_name: Optional[str]
    command: str
    detail: Optional[str]
    status: str
    error_msg: Optional[str]
    triggered_by: str
    created_at: datetime

    class Config:
        from_attributes = True
