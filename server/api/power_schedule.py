"""开关机计划 API"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.models import get_db, PowerScheduleModel
from shared.schemas import PowerScheduleCreate, PowerScheduleOut, PowerSchedulePatch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/power-schedules", tags=["开关机计划"])


def _out(p: PowerScheduleModel) -> PowerScheduleOut:
    return PowerScheduleOut(
        id=p.id,
        name=p.name,
        display_ids=p.get_display_ids(),
        on_time=p.on_time,
        off_time=p.off_time,
        power_days=p.power_days or "1,2,3,4,5",
        is_enabled=p.is_enabled,
        created_at=p.created_at,
    )


@router.get("")
def list_schedules(db: Session = Depends(get_db)):
    items = db.query(PowerScheduleModel).order_by(PowerScheduleModel.created_at.desc()).all()
    return [_out(p) for p in items]


@router.post("")
def create_schedule(data: PowerScheduleCreate, request: Request = None, db: Session = Depends(get_db)):
    p = PowerScheduleModel(
        name=data.name.strip(),
        on_time=data.on_time,
        off_time=data.off_time,
        power_days=data.power_days,
        is_enabled=data.is_enabled,
    )
    p.set_display_ids(data.display_ids)
    db.add(p)
    db.commit()
    db.refresh(p)

    from server.api.audit import log_action
    log_action(db, action="create", resource="power_schedule", resource_id=p.id,
               detail={"name": p.name}, request=request)

    return _out(p)


@router.put("/{schedule_id}")
def update_schedule(schedule_id: int, data: PowerScheduleCreate, request: Request = None, db: Session = Depends(get_db)):
    p = db.query(PowerScheduleModel).filter(PowerScheduleModel.id == schedule_id).first()
    if not p:
        raise HTTPException(404, "计划不存在")

    p.name = data.name.strip()
    p.on_time = data.on_time
    p.off_time = data.off_time
    p.power_days = data.power_days
    p.is_enabled = data.is_enabled
    p.set_display_ids(data.display_ids)
    db.commit()
    db.refresh(p)

    from server.api.audit import log_action
    log_action(db, action="update", resource="power_schedule", resource_id=p.id,
               detail={"name": p.name}, request=request)

    return _out(p)


@router.patch("/{schedule_id}")
def patch_schedule(schedule_id: int, data: PowerSchedulePatch, db: Session = Depends(get_db)):
    p = db.query(PowerScheduleModel).filter(PowerScheduleModel.id == schedule_id).first()
    if not p:
        raise HTTPException(404, "计划不存在")

    if data.is_enabled is not None:
        p.is_enabled = data.is_enabled
    db.commit()
    db.refresh(p)
    return _out(p)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, request: Request = None, db: Session = Depends(get_db)):
    p = db.query(PowerScheduleModel).filter(PowerScheduleModel.id == schedule_id).first()
    if not p:
        raise HTTPException(404, "计划不存在")

    db.delete(p)
    db.commit()

    from server.api.audit import log_action
    log_action(db, action="delete", resource="power_schedule", resource_id=schedule_id,
               detail={"name": p.name}, request=request)

    return {"ok": True}
