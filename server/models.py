"""SQLAlchemy 数据库模型"""

import json
import os
import secrets
import string
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

from shared.config import get_db_path

Base = declarative_base()

# 延迟初始化：engine 和 _SessionLocal_factory 在 init_db() 中创建
_engine = None
_SessionLocal_factory = None


def get_engine():
    """获取 SQLAlchemy engine（延迟初始化）"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{get_db_path()}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def SessionLocal():
    """获取数据库会话"""
    global _SessionLocal_factory
    if _SessionLocal_factory is None:
        _SessionLocal_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal_factory()


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表 + 迁移新增字段"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_db()


def _migrate_db():
    """为现有数据库添加新字段（幂等，事务保护）"""
    from sqlalchemy import text
    engine = get_engine()

    migrations = [
        ("layouts", "resolution_width", "INTEGER DEFAULT 1920"),
        ("layouts", "resolution_height", "INTEGER DEFAULT 1080"),
        ("layouts", "orientation", "VARCHAR(20) DEFAULT 'landscape'"),
        ("layouts", "updated_at", "DATETIME"),
        ("displays", "screen_width", "INTEGER"),
        ("displays", "screen_height", "INTEGER"),
        ("displays", "screen_orientation", "VARCHAR(20)"),
        ("tokens", "expires_at", "DATETIME"),
        ("schedules", "repeat_type", "VARCHAR(20) DEFAULT 'none'"),
        ("schedules", "repeat_days", "TEXT DEFAULT '[]'"),
        ("schedules", "repeat_start_time", "VARCHAR(10)"),
        ("schedules", "repeat_end_time", "VARCHAR(10)"),
        ("schedules", "repeat_until", "DATETIME"),
        ("media", "ppt_images", "TEXT"),
        ("media", "ppt_slide_duration", "INTEGER DEFAULT 30"),
        ("displays", "platform", "VARCHAR(20) DEFAULT 'windows'"),
        ("displays", "ip_address", "VARCHAR(50)"),
        ("displays", "group_id", "INTEGER"),
        ("users", "role", "VARCHAR(20) DEFAULT 'admin'"),
        ("media", "expires_at", "DATETIME"),
        ("media", "width", "INTEGER"),
        ("media", "height", "INTEGER"),
    ]

    with engine.begin() as conn:
        # 创建 device_groups 表
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS device_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description VARCHAR(255) DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
        except Exception:
            pass

        # 迁移现有 group_name 到 device_groups 表
        try:
            conn.execute(text("""
                INSERT OR IGNORE INTO device_groups (name)
                SELECT DISTINCT group_name FROM displays
                WHERE group_name IS NOT NULL AND group_name != 'default'
            """))
            conn.execute(text("""
                UPDATE displays SET group_id = (
                    SELECT id FROM device_groups WHERE device_groups.name = displays.group_name
                ) WHERE group_id IS NULL AND group_name IS NOT NULL AND group_name != 'default'
            """))
        except Exception:
            pass
        for table, column, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            except Exception:
                pass  # 字段已存在（SQLite 报 OperationalError）

        # 为现有无过期时间的 token 补上 +7 天
        try:
            conn.execute(text(
                "UPDATE tokens SET expires_at = datetime(created_at, '+7 days') WHERE expires_at IS NULL"
            ))
        except Exception:
            pass

        # 创建开关机计划表
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS power_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255),
                    display_ids TEXT DEFAULT '[]',
                    on_time VARCHAR(5),
                    off_time VARCHAR(5),
                    power_days VARCHAR(50) DEFAULT '1,2,3,4,5',
                    is_enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
        except Exception:
            pass

        # 创建下发记录表
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS command_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_id INTEGER,
                    display_name VARCHAR(255),
                    command VARCHAR(50),
                    detail TEXT,
                    status VARCHAR(20),
                    error_msg TEXT,
                    triggered_by VARCHAR(20),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
        except Exception:
            pass

    # 创建默认管理员账号
    _ensure_default_admin()


# ============ 模型定义 ============

class MediaModel(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)      # image / video / ppt
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # 视频时长
    file_size = Column(Integer, default=0)
    width = Column(Integer, nullable=True)         # 图片/视频宽度
    height = Column(Integer, nullable=True)        # 图片/视频高度
    ppt_images = Column(Text, nullable=True)       # JSON: PPT 所有图片路径列表
    ppt_slide_duration = Column(Integer, default=30)  # PPT 每页默认播放时长（秒）
    expires_at = Column(DateTime, nullable=True)    # 素材过期时间（NULL=不过期）
    created_at = Column(DateTime, default=datetime.now)

    def get_ppt_images(self) -> list:
        """获取 PPT 图片列表"""
        if not self.ppt_images:
            return []
        try:
            return json.loads(self.ppt_images)
        except Exception:
            return []

    def set_ppt_images(self, images: list):
        """设置 PPT 图片列表"""
        self.ppt_images = json.dumps(images) if images else None


class DeviceGroupModel(Base):
    __tablename__ = "device_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class DisplayModel(Base):
    __tablename__ = "displays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    mac_address = Column(String(50), nullable=True)
    group_name = Column(String(100), default="default")
    group_id = Column(Integer, ForeignKey("device_groups.id"), nullable=True)
    license_key = Column(String(100), nullable=True)
    status = Column(String(20), default="offline")
    last_heartbeat = Column(DateTime, nullable=True)
    current_layout_id = Column(Integer, nullable=True)
    screenshot_updated_at = Column(DateTime, nullable=True)
    commands = Column(Text, default="[]")  # JSON: 待执行指令列表
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    screen_orientation = Column(String(20), nullable=True)
    platform = Column(String(20), nullable=True)  # windows / android
    ip_address = Column(String(50), nullable=True)  # 设备 IP 地址
    created_at = Column(DateTime, default=datetime.now)

    def get_commands(self):
        return json.loads(self.commands or "[]")

    def set_commands(self, cmds: list):
        self.commands = json.dumps(cmds)

    def add_command(self, cmd: str):
        cmds = self.get_commands()
        cmds.append(cmd)
        self.set_commands(cmds)

    def clear_commands(self):
        self.set_commands([])


class LayoutModel(Base):
    __tablename__ = "layouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)       # fullscreen / playlist / split_2 / split_3
    zones = Column(Text, default="[]")               # JSON: list of ZoneConfig
    marquee = Column(Text, nullable=True)            # JSON: MarqueeConfig or None
    split_ratio = Column(String(10), default="1:1")
    bgm_media_id = Column(Integer, nullable=True)
    bgm_volume = Column(Integer, default=60)
    transition_duration_ms = Column(Integer, default=800)
    resolution_width = Column(Integer, default=1920)
    resolution_height = Column(Integer, default=1080)
    orientation = Column(String(20), default="landscape")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def get_zones(self):
        return json.loads(self.zones or "[]")

    def set_zones(self, data: list):
        self.zones = json.dumps(data)

    def get_marquee(self):
        return json.loads(self.marquee) if self.marquee else None

    def set_marquee(self, data):
        self.marquee = json.dumps(data) if data else None


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    layout_id = Column(Integer, nullable=False)
    display_ids = Column(Text, default="[]")         # JSON: list of display IDs
    start_time = Column(DateTime, nullable=True, default=datetime.now)  # None 表示立即生效（永久排程）
    end_time = Column(DateTime, nullable=True)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    # 重复排程字段
    repeat_type = Column(String(20), default="none")  # none / daily / weekly / monthly
    repeat_days = Column(Text, default="[]")           # JSON: [1,3,5] (周一三五) 或 [1,15] (每月1号15号)
    repeat_start_time = Column(String(10), nullable=True)  # "08:00" 每天时间段开始
    repeat_end_time = Column(String(10), nullable=True)    # "18:00" 每天时间段结束
    repeat_until = Column(DateTime, nullable=True)         # 重复截止日期
    created_at = Column(DateTime, default=datetime.now)

    def get_display_ids(self):
        return json.loads(self.display_ids or "[]")

    def set_display_ids(self, data: list):
        self.display_ids = json.dumps(data)

    def get_repeat_days(self):
        return json.loads(self.repeat_days or "[]")

    def set_repeat_days(self, data: list):
        self.repeat_days = json.dumps(data)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="admin")  # admin / operator / readonly
    created_at = Column(DateTime, default=datetime.now)


class TokenModel(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False)       # login / create / update / delete
    resource = Column(String(50), nullable=True)       # media / layout / schedule / display / user
    resource_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)               # JSON: 变更内容
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class TagModel(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    color = Column(String(10), default="#3B82F6")
    created_at = Column(DateTime, default=datetime.now)


# 素材-标签多对多关联表
from sqlalchemy import Table
media_tags = Table(
    'media_tags', Base.metadata,
    Column('media_id', Integer, ForeignKey('media.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)


def hash_password(password: str) -> str:
    """密码哈希（pbkdf2_sha256）"""
    import hashlib
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    import hashlib
    import hmac
    try:
        salt_hex, key_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return hmac.compare_digest(new_key, key)
    except Exception:
        return False


def _ensure_default_admin():
    """确保默认管理员账号存在，首次运行时生成随机密码"""
    db = SessionLocal()
    try:
        if db.query(UserModel).count() == 0:
            # 生成随机 16 位密码（增强安全性）
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            random_pw = ''.join(secrets.choice(alphabet) for _ in range(16))
            user = UserModel(
                username="admin",
                password_hash=hash_password(random_pw),
            )
            db.add(user)
            db.commit()
            print(f"\n  首次启动，管理员初始密码已生成")
            print(f"     用户名: admin")
            print(f"     密码:   {random_pw}")
            print(f"     请登录后立即修改密码\n")
    except Exception:
        db.rollback()
    finally:
        db.close()


def _save_initial_password(password: str):
    """将首次生成的随机密码保存到 config.json"""
    import json
    from shared.config import get_config_path
    config_path = get_config_path()
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    config['_initial_admin_password'] = password
    config['_password_generated_at'] = datetime.now().isoformat()
    config['_note'] = '⚠ 请登录后立即修改密码并删除 _initial_admin_password 字段'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    # 设置文件权限（仅 owner 可读写）
    try:
        os.chmod(config_path, 0o600)
    except OSError:
        pass  # Windows 不支持


def get_or_create_player_secret() -> str:
    """获取 Player 端认证密钥，不存在则自动生成"""
    import json
    from shared.config import get_config_path
    config_path = get_config_path()
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    secret = config.get("player_secret", "")
    if not secret:
        secret = secrets.token_urlsafe(32)
        config["player_secret"] = secret
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return secret


class PowerScheduleModel(Base):
    """开关机计划"""
    __tablename__ = "power_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    display_ids = Column(Text, default="[]")             # JSON: 绑定的屏幕 ID 列表，空=全部
    on_time = Column(String(5), nullable=True)            # 开机时间 "08:00"，null=不控制
    off_time = Column(String(5), nullable=True)           # 关机时间 "22:00"，null=不控制
    power_days = Column(String(50), default="1,2,3,4,5") # 执行日，周日=0
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    def get_display_ids(self) -> list:
        if not self.display_ids:
            return []
        try:
            return json.loads(self.display_ids)
        except Exception:
            return []

    def set_display_ids(self, ids: list):
        self.display_ids = json.dumps(ids) if ids else "[]"


class CommandLogModel(Base):
    """下发记录"""
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_id = Column(Integer, nullable=True)
    display_name = Column(String(255), nullable=True)
    command = Column(String(50), nullable=False)
    detail = Column(Text, nullable=True)
    status = Column(String(20), default="success")
    error_msg = Column(Text, nullable=True)
    triggered_by = Column(String(20), default="manual")  # schedule / manual
    created_at = Column(DateTime, default=datetime.now)
