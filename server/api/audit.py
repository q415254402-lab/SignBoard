"""操作日志 API"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.models import get_db, AuditLogModel, TokenModel, UserModel

router = APIRouter(prefix="/audit", tags=["操作日志"])


def _get_user_from_request(request: Request, db: Session):
    """从请求中获取当前用户信息"""
    token = request.cookies.get("signboard_token")
    if not token:
        return None, None
    token_obj = db.query(TokenModel).filter(
        TokenModel.token == token,
        TokenModel.expires_at > datetime.now(),
    ).first()
    if not token_obj:
        return None, None
    user = db.query(UserModel).filter(UserModel.id == token_obj.user_id).first()
    if user:
        return user.id, user.username
    return None, None


def log_action(db: Session, action: str = "", resource: str = None, resource_id: int = None,
               detail: dict = None, request: Request = None):
    """记录操作日志（供其他模块调用）"""
    user_id, username = None, None
    ip_address = None

    if request:
        user_id, username = _get_user_from_request(request, db)
        if request.client:
            ip_address = request.client.host

    log = AuditLogModel(
        user_id=user_id,
        username=username,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()


@router.get("/list")
def list_logs(
    request: Request,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """查询操作日志"""
    query = db.query(AuditLogModel)

    if resource:
        query = query.filter(AuditLogModel.resource == resource)
    if action:
        query = query.filter(AuditLogModel.action == action)
    if username:
        query = query.filter(AuditLogModel.username == username)

    logs = query.order_by(AuditLogModel.id.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "username": l.username,
            "action": l.action,
            "resource": l.resource,
            "resource_id": l.resource_id,
            "detail": json.loads(l.detail) if l.detail else None,
            "ip_address": l.ip_address,
            "created_at": l.created_at,
        }
        for l in logs
    ]
