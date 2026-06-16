"""排程管理 API"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from server.models import get_db, ScheduleModel
from shared.schemas import ScheduleCreate, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["排程管理"])


@router.post("")
def create_schedule(data: ScheduleCreate, request: Request = None, db: Session = Depends(get_db)):
    sched = ScheduleModel(
        name=data.name,
        layout_id=data.layout_id,
        start_time=data.start_time,
        end_time=data.end_time,
        priority=data.priority,
        is_active=data.is_active,
        repeat_type=data.repeat_type,
        repeat_start_time=data.repeat_start_time,
        repeat_end_time=data.repeat_end_time,
        repeat_until=data.repeat_until,
    )
    sched.set_display_ids(data.display_ids)
    if data.repeat_days:
        sched.set_repeat_days(data.repeat_days)
    db.add(sched)
    db.commit()
    db.refresh(sched)

    # 记录创建日志
    from server.api.audit import log_action
    log_action(db, action="create", resource="schedule", resource_id=sched.id,
               detail={"name": sched.name, "layout_id": sched.layout_id}, request=request)

    # 紧急插播（priority >= 999）通过 SSE 立即通知屏幕刷新
    if data.priority >= 999 and data.is_active:
        from server.api.player_sync import notify_display, notify_all_displays
        target_ids = data.display_ids if data.display_ids else []
        if target_ids:
            for did in target_ids:
                notify_display(did, "sync", {"reason": "urgent_schedule", "schedule_id": sched.id})
        else:
            notify_all_displays("sync", {"reason": "urgent_schedule", "schedule_id": sched.id})

    return _schedule_out(sched)


@router.get("/count")
def count_schedules(db: Session = Depends(get_db)):
    """获取排程统计"""
    total = db.query(ScheduleModel).count()
    active = db.query(ScheduleModel).filter(ScheduleModel.is_active == True).count()
    return {"total": total, "active": active}


@router.put("/{schedule_id}")
def update_schedule(schedule_id: int, data: ScheduleCreate, db: Session = Depends(get_db)):
    sched = db.query(ScheduleModel).filter(ScheduleModel.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, "排程不存在")

    sched.name = data.name
    sched.layout_id = data.layout_id
    sched.start_time = data.start_time
    sched.end_time = data.end_time
    sched.priority = data.priority
    sched.is_active = data.is_active
    sched.repeat_type = data.repeat_type
    sched.repeat_start_time = data.repeat_start_time
    sched.repeat_end_time = data.repeat_end_time
    sched.repeat_until = data.repeat_until
    sched.set_display_ids(data.display_ids)
    if data.repeat_days is not None:
        sched.set_repeat_days(data.repeat_days)

    db.commit()
    db.refresh(sched)

    from server.api.audit import log_action
    log_action(db, action="update", resource="schedule", resource_id=schedule_id,
               detail={"name": sched.name}, request=request)

    return _schedule_out(sched)


class SchedulePatch(BaseModel):
    """排程部分更新"""
    name: Optional[str] = None
    layout_id: Optional[int] = None
    display_ids: Optional[list[int]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    repeat_type: Optional[str] = None
    repeat_days: Optional[list[int]] = None
    repeat_start_time: Optional[str] = None
    repeat_end_time: Optional[str] = None
    repeat_until: Optional[datetime] = None


@router.patch("/{schedule_id}")
def patch_schedule(schedule_id: int, data: SchedulePatch, db: Session = Depends(get_db)):
    """部分更新排程（如暂停/启用）"""
    sched = db.query(ScheduleModel).filter(ScheduleModel.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, "排程不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "display_ids":
            sched.set_display_ids(value)
        elif key == "repeat_days":
            sched.set_repeat_days(value)
        else:
            setattr(sched, key, value)

    db.commit()
    db.refresh(sched)
    return _schedule_out(sched)


@router.get("/list")
def list_schedules(db: Session = Depends(get_db)):
    items = db.query(ScheduleModel).order_by(ScheduleModel.created_at.desc()).all()
    return [_schedule_out(s) for s in items]


@router.get("/{schedule_id}")
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = db.query(ScheduleModel).filter(ScheduleModel.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, "排程不存在")
    return _schedule_out(sched)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, request: Request = None, db: Session = Depends(get_db)):
    sched = db.query(ScheduleModel).filter(ScheduleModel.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, "排程不存在")
    name = sched.name
    db.delete(sched)
    db.commit()

    # 记录删除日志
    from server.api.audit import log_action
    log_action(db, action="delete", resource="schedule", resource_id=schedule_id,
               detail={"name": name}, request=request)

    return {"ok": True}


def _schedule_out(sched: ScheduleModel) -> ScheduleOut:
    return ScheduleOut(
        id=sched.id,
        name=sched.name,
        layout_id=sched.layout_id,
        display_ids=sched.get_display_ids(),
        start_time=sched.start_time,
        end_time=sched.end_time,
        priority=sched.priority,
        is_active=sched.is_active,
        repeat_type=sched.repeat_type or "none",
        repeat_days=sched.get_repeat_days() if sched.repeat_type != "none" else None,
        repeat_start_time=sched.repeat_start_time,
        repeat_end_time=sched.repeat_end_time,
        repeat_until=sched.repeat_until,
        created_at=sched.created_at,
    )


def get_active_schedule_for_display(db: Session, display_id: int):
    """给 Player 查询当前有效排程（含重复排程）"""
    now = datetime.now()
    today_date = now.date()
    now_time = now.strftime("%H:%M")

    schedules = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.is_active == True)
        .order_by(ScheduleModel.priority.desc())
        .all()
    )

    for s in schedules:
        # 先检查屏幕是否匹配
        display_ids = s.get_display_ids()
        if display_ids and display_id not in display_ids:
            continue

        # 不重复排程：按 start_time / end_time 判断
        if s.repeat_type == "none" or not s.repeat_type:
            # start_time 为 None 视为立即生效（永久排程）
            if (s.start_time is None or s.start_time <= now) and (s.end_time is None or s.end_time >= now):
                return s
            continue

        # 重复排程
        # 检查 repeat_until（截止日期）
        if s.repeat_until:
            repeat_until_date = s.repeat_until.date() if isinstance(s.repeat_until, datetime) else s.repeat_until
            if today_date > repeat_until_date:
                continue

        # 检查时间段（支持跨天：如 22:00-06:00）
        if s.repeat_start_time and s.repeat_end_time:
            if s.repeat_start_time <= s.repeat_end_time:
                # 正常时间段
                if now_time < s.repeat_start_time or now_time > s.repeat_end_time:
                    continue
            else:
                # 跨天时间段（如 22:00-06:00）：now 在 start 之后 OR end 之前
                if now_time < s.repeat_start_time and now_time > s.repeat_end_time:
                    continue

        # 按重复类型判断今天是否命中
        repeat_days = s.get_repeat_days()
        if s.repeat_type == "daily":
            return s
        elif s.repeat_type == "weekly":
            dow = now.isoweekday()  # Mon=1..Sun=7
            if repeat_days and dow in repeat_days:
                return s
        elif s.repeat_type == "monthly":
            day_of_month = now.day
            if repeat_days and day_of_month in repeat_days:
                return s

    return None