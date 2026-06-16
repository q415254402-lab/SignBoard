"""下发记录 API"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from server.models import get_db, CommandLogModel
from shared.schemas import CommandLogOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/command-logs", tags=["下发记录"])


def _out(c: CommandLogModel) -> CommandLogOut:
    return CommandLogOut(
        id=c.id,
        display_id=c.display_id,
        display_name=c.display_name,
        command=c.command,
        detail=c.detail,
        status=c.status,
        error_msg=c.error_msg,
        triggered_by=c.triggered_by or "manual",
        created_at=c.created_at,
    )


@router.get("")
def list_logs(
    display_id: Optional[int] = Query(None),
    command: Optional[str] = Query(None),
    triggered_by: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(CommandLogModel)

    if display_id is not None:
        q = q.filter(CommandLogModel.display_id == display_id)
    if command:
        q = q.filter(CommandLogModel.command == command)
    if triggered_by:
        q = q.filter(CommandLogModel.triggered_by == triggered_by)
    if start_time:
        try:
            q = q.filter(CommandLogModel.created_at >= datetime.fromisoformat(start_time))
        except ValueError:
            pass
    if end_time:
        try:
            q = q.filter(CommandLogModel.created_at <= datetime.fromisoformat(end_time))
        except ValueError:
            pass

    total = q.count()
    items = q.order_by(CommandLogModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_out(c) for c in items],
    }


def log_command(db: Session, display_id: int, display_name: str, command: str,
                status: str = "success", error_msg: str = None, detail: str = None,
                triggered_by: str = "manual"):
    """记录下发日志"""
    log = CommandLogModel(
        display_id=display_id,
        display_name=display_name,
        command=command,
        detail=detail,
        status=status,
        error_msg=error_msg,
        triggered_by=triggered_by,
    )
    db.add(log)
    db.commit()
