"""布局管理 API"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.models import get_db, LayoutModel
from shared.schemas import LayoutCreate, LayoutOut, LayoutType, SplitRatio

router = APIRouter(prefix="/layouts", tags=["布局管理"])


@router.post("")
def create_layout(data: LayoutCreate, request: Request = None, db: Session = Depends(get_db)):
    # 校验 zone 中的 media_id 是否存在
    _validate_zone_media_ids(data.zones, db)

    layout = LayoutModel(
        name=data.name,
        type=data.type.value,
        split_ratio=data.split_ratio.value,
        bgm_media_id=data.bgm_media_id,
        bgm_volume=data.bgm_volume,
        transition_duration_ms=data.transition_duration_ms,
        resolution_width=data.resolution_width,
        resolution_height=data.resolution_height,
        orientation="landscape" if data.resolution_width >= data.resolution_height else "portrait",
    )
    layout.set_zones([z.model_dump() for z in data.zones])
    if data.marquee:
        layout.set_marquee(data.marquee.model_dump())

    db.add(layout)
    db.commit()
    db.refresh(layout)

    from server.api.audit import log_action
    log_action(db, action="create", resource="layout", resource_id=layout.id,
               detail={"name": layout.name, "type": layout.type}, request=request)

    return _layout_out(layout)


@router.put("/{layout_id}")
def update_layout(layout_id: int, data: LayoutCreate, request: Request = None, db: Session = Depends(get_db)):
    layout = db.query(LayoutModel).filter(LayoutModel.id == layout_id).first()
    if not layout:
        raise HTTPException(404, "布局不存在")

    # 校验 zone 中的 media_id 是否存在
    _validate_zone_media_ids(data.zones, db)

    layout.name = data.name
    layout.type = data.type.value
    layout.split_ratio = data.split_ratio.value
    layout.bgm_media_id = data.bgm_media_id
    layout.bgm_volume = data.bgm_volume
    layout.transition_duration_ms = data.transition_duration_ms
    layout.resolution_width = data.resolution_width
    layout.resolution_height = data.resolution_height
    layout.orientation = "landscape" if data.resolution_width >= data.resolution_height else "portrait"
    layout.set_zones([z.model_dump() for z in data.zones])
    if data.marquee:
        layout.set_marquee(data.marquee.model_dump())
    else:
        layout.set_marquee(None)
    layout.created_at = datetime.now()

    db.commit()
    db.refresh(layout)

    from server.api.audit import log_action
    log_action(db, action="update", resource="layout", resource_id=layout.id,
               detail={"name": layout.name}, request=request)

    return _layout_out(layout)


@router.get("/list")
def list_layouts(db: Session = Depends(get_db)):
    layouts = db.query(LayoutModel).order_by(LayoutModel.created_at.desc()).all()
    return [_layout_out(l) for l in layouts]


@router.get("/{layout_id}")
def get_layout(layout_id: int, db: Session = Depends(get_db)):
    layout = db.query(LayoutModel).filter(LayoutModel.id == layout_id).first()
    if not layout:
        raise HTTPException(404, "布局不存在")
    return _layout_out(layout)


@router.delete("/{layout_id}")
def delete_layout(layout_id: int, force: bool = False, request: Request = None, db: Session = Depends(get_db)):
    layout = db.query(LayoutModel).filter(LayoutModel.id == layout_id).first()
    if not layout:
        raise HTTPException(404, "布局不存在")

    from server.models import ScheduleModel
    ref_count = db.query(ScheduleModel).filter(ScheduleModel.layout_id == layout_id).count()
    if ref_count > 0 and not force:
        raise HTTPException(409, f"该布局被 {ref_count} 个排程引用，请先删除相关排程，或使用 force=true 强制删除")

    name = layout.name
    db.delete(layout)
    db.commit()

    # 记录删除日志
    from server.api.audit import log_action
    log_action(db, action="delete", resource="layout", resource_id=layout_id,
               detail={"name": name}, request=request)

    return {"ok": True}


def _layout_out(layout: LayoutModel) -> LayoutOut:
    from shared.schemas import ZoneConfig, MarqueeConfig
    zones = [ZoneConfig(**z) for z in layout.get_zones()]
    marquee_data = layout.get_marquee()
    marquee = MarqueeConfig(**marquee_data) if marquee_data else None
    return LayoutOut(
        id=layout.id,
        name=layout.name,
        type=LayoutType(layout.type),
        zones=zones,
        marquee=marquee,
        split_ratio=SplitRatio(layout.split_ratio),
        bgm_media_id=layout.bgm_media_id,
        bgm_volume=layout.bgm_volume,
        transition_duration_ms=layout.transition_duration_ms,
        resolution_width=layout.resolution_width or 1920,
        resolution_height=layout.resolution_height or 1080,
        created_at=layout.created_at,
    )


def _validate_zone_media_ids(zones: list, db: Session):
    """校验 zone 中引用的 media_id 是否存在"""
    from server.models import MediaModel
    for z in zones:
        media_id = getattr(z, 'media_id', None) if hasattr(z, 'media_id') else z.get('media_id') if isinstance(z, dict) else None
        if media_id is not None:
            exists = db.query(MediaModel).filter(MediaModel.id == media_id).first()
            if not exists:
                raise HTTPException(400, f"素材 ID {media_id} 不存在")