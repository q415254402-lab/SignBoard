"""账号认证 API（含用户管理和权限控制）"""

import os
import uuid
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from server.models import get_db, UserModel, TokenModel, AuditLogModel, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["账号认证"])

TOKEN_EXPIRE_DAYS = 7

# 权限矩阵
ROLE_PERMISSIONS = {
    "admin": {
        "media": ["read", "write", "delete"],
        "layout": ["read", "write", "delete"],
        "schedule": ["read", "write", "delete"],
        "display": ["read", "write", "delete"],
        "user": ["read", "write", "delete"],
        "audit": ["read"],
    },
    "operator": {
        "media": ["read", "write"],
        "layout": ["read", "write"],
        "schedule": ["read", "write"],
        "display": ["read"],
        "user": ["read"],
        "audit": [],
    },
    "readonly": {
        "media": ["read"],
        "layout": ["read"],
        "schedule": ["read"],
        "display": ["read"],
        "user": [],
        "audit": [],
    },
}


# ---- 登录限流 ----
class LoginRateLimiter:
    """基于 IP 的滑动窗口限流器"""
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._max_attempts = max_attempts
        self._window = window_seconds

    def is_blocked(self, key: str) -> bool:
        now = time.time()
        self._attempts[key] = [
            t for t in self._attempts[key] if now - t < self._window
        ]
        return len(self._attempts[key]) >= self._max_attempts

    def record(self, key: str):
        self._attempts[key].append(time.time())

    def get_remaining_seconds(self, key: str) -> int:
        if not self._attempts[key]:
            return 0
        oldest = self._attempts[key][0]
        remaining = self._window - (time.time() - oldest)
        return max(0, int(remaining))

    def clear(self, key: str):
        self._attempts.pop(key, None)


_login_limiter = LoginRateLimiter(max_attempts=5, window_seconds=300)


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """登录（带频率限制）"""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}"

    if _login_limiter.is_blocked(rate_key):
        remaining = _login_limiter.get_remaining_seconds(rate_key)
        raise HTTPException(
            429,
            f"登录尝试过于频繁，请 {remaining} 秒后再试",
            headers={"Retry-After": str(remaining)},
        )

    user = db.query(UserModel).filter(UserModel.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        _login_limiter.record(rate_key)
        logger.warning(f"登录失败: username={data.username}, ip={client_ip}")
        raise HTTPException(401, "账号或密码错误")

    _login_limiter.clear(rate_key)

    token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(days=TOKEN_EXPIRE_DAYS)
    token_obj = TokenModel(user_id=user.id, token=token, expires_at=expires_at)
    db.add(token_obj)
    db.commit()

    from server.api.audit import log_action
    log = AuditLogModel(
        user_id=user.id, username=user.username, action="login",
        ip_address=client_ip,
    )
    db.add(log)
    db.commit()

    is_https = request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        key="signboard_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=is_https,
        max_age=86400 * TOKEN_EXPIRE_DAYS,
    )
    return {"ok": True, "username": user.username, "role": user.role}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """登出"""
    token = request.cookies.get("signboard_token")
    if token:
        db.query(TokenModel).filter(TokenModel.token == token).delete()
        db.commit()
    response.delete_cookie("signboard_token")
    return {"ok": True}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    """检查登录状态"""
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(401, "未登录")
    return {"username": user.username, "role": user.role}


@router.post("/change-password")
def change_password(data: PasswordChange, request: Request, response: Response, db: Session = Depends(get_db)):
    """修改密码（会踢掉该用户所有其他设备的登录）"""
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(401, "未登录")
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")

    user.password_hash = hash_password(data.new_password)
    db.query(TokenModel).filter(TokenModel.user_id == user.id).delete()

    token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(days=TOKEN_EXPIRE_DAYS)
    db.add(TokenModel(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()

    response.set_cookie(
        key="signboard_token",
        value=token,
        httponly=True,
        samesite="strict",
        max_age=86400 * TOKEN_EXPIRE_DAYS,
    )

    try:
        from shared.config import get_config_path
        import json
        config_path = get_config_path()
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if '_initial_admin_password' in config:
                del config['_initial_admin_password']
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {"ok": True}


# ---- 用户管理（仅 admin） ----

@router.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    """获取用户列表"""
    user = _get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(403, "无权限")

    users = db.query(UserModel).all()
    return [
        {"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at}
        for u in users
    ]


@router.post("/users")
def create_user(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """创建用户"""
    user = _get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(403, "无权限")

    if data.role not in ROLE_PERMISSIONS:
        raise HTTPException(400, f"无效角色: {data.role}")

    existing = db.query(UserModel).filter(UserModel.username == data.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")

    new_user = UserModel(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}


@router.put("/users/{user_id}")
def update_user(user_id: int, data: UserUpdate, request: Request, db: Session = Depends(get_db)):
    """更新用户"""
    user = _get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(403, "无权限")

    target = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target:
        raise HTTPException(404, "用户不存在")

    if data.username is not None:
        existing = db.query(UserModel).filter(
            UserModel.username == data.username,
            UserModel.id != user_id
        ).first()
        if existing:
            raise HTTPException(400, "用户名已存在")
        target.username = data.username

    if data.password is not None:
        target.password_hash = hash_password(data.password)
        # 清除该用户所有 token
        db.query(TokenModel).filter(TokenModel.user_id == user_id).delete()

    if data.role is not None:
        if data.role not in ROLE_PERMISSIONS:
            raise HTTPException(400, f"无效角色: {data.role}")
        target.role = data.role

    db.commit()
    return {"id": target.id, "username": target.username, "role": target.role}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    """删除用户"""
    user = _get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(403, "无权限")

    target = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target:
        raise HTTPException(404, "用户不存在")

    if target.id == user.id:
        raise HTTPException(400, "不能删除自己")

    db.query(TokenModel).filter(TokenModel.user_id == user_id).delete()
    db.delete(target)
    db.commit()
    return {"ok": True}


@router.get("/roles")
def get_roles(request: Request):
    """获取角色列表和权限矩阵"""
    return {
        "roles": [
            {"name": "admin", "label": "管理员", "description": "全部权限"},
            {"name": "operator", "label": "操作员", "description": "管理素材/布局/排程，不能管理设备和用户"},
            {"name": "readonly", "label": "只读", "description": "仅查看，不能修改任何内容"},
        ],
        "permissions": ROLE_PERMISSIONS,
    }


# ---- 工具函数 ----

def _get_current_user(request: Request, db: Session) -> UserModel | None:
    """从 cookie 获取当前用户（检查过期时间）"""
    token = request.cookies.get("signboard_token")
    if not token:
        return None
    token_obj = db.query(TokenModel).filter(
        TokenModel.token == token,
        TokenModel.expires_at > datetime.now(),
    ).first()
    if not token_obj:
        return None
    user = db.query(UserModel).filter(UserModel.id == token_obj.user_id).first()
    return user


def get_current_user(request: Request, db: Session) -> UserModel:
    """获取当前用户（未登录抛异常）"""
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(401, "未登录")
    return user


def check_permission(request: Request, db: Session, resource: str, action: str) -> UserModel:
    """检查权限，返回当前用户"""
    user = get_current_user(request, db)
    perms = ROLE_PERMISSIONS.get(user.role, {})
    if action not in perms.get(resource, []):
        raise HTTPException(403, f"无权限: {resource}.{action}")
    return user


def check_auth(request: Request, db: Session) -> bool:
    """检查是否已登录（供中间件调用）"""
    return _get_current_user(request, db) is not None
