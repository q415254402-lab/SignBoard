"""屏幕管理 + 心跳 + 截图 API"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from server.models import get_db, DisplayModel
from shared.schemas import DisplayRegister, DisplayOut, DisplayStatus, HeartbeatData, CommandRequest
from shared.config import get_upload_dir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/displays", tags=["屏幕管理"])

SCREENSHOT_DIR_NAME = "screenshots"


def _get_screenshot_dir():
    upload_dir = get_upload_dir()
    ss_dir = os.path.join(upload_dir, SCREENSHOT_DIR_NAME)
    os.makedirs(ss_dir, exist_ok=True)
    return ss_dir


@router.post("/register")
def register_display(data: DisplayRegister, db: Session = Depends(get_db)):
    """注册新屏幕"""
    existing = db.query(DisplayModel).filter(DisplayModel.name == data.name).first()
    if existing:
        # 已存在同名屏幕则更新
        existing.mac_address = data.mac_address
        existing.group_name = data.group_name
        existing.status = DisplayStatus.ONLINE.value
        existing.last_heartbeat = datetime.now()
        if data.screen_width:
            existing.screen_width = data.screen_width
        if data.screen_height:
            existing.screen_height = data.screen_height
        if data.screen_width and data.screen_height:
            existing.screen_orientation = (
                "landscape" if data.screen_width >= data.screen_height else "portrait"
            )
        if data.platform:
            existing.platform = data.platform
        if data.ip_address:
            existing.ip_address = data.ip_address
        db.commit()
        db.refresh(existing)
        result = _display_out(existing)
        return _attach_player_token(result)

    # MAC 地址去重：防止同一台机器创建多个屏幕记录
    if data.mac_address:
        mac_exist = db.query(DisplayModel).filter(DisplayModel.mac_address == data.mac_address).first()
        if mac_exist:
            mac_exist.name = data.name
            mac_exist.group_name = data.group_name
            mac_exist.status = DisplayStatus.ONLINE.value
            mac_exist.last_heartbeat = datetime.now()
            if data.screen_width:
                mac_exist.screen_width = data.screen_width
            if data.screen_height:
                mac_exist.screen_height = data.screen_height
            if data.screen_width and data.screen_height:
                mac_exist.screen_orientation = (
                    "landscape" if data.screen_width >= data.screen_height else "portrait"
                )
            if data.platform:
                mac_exist.platform = data.platform
            if data.ip_address:
                mac_exist.ip_address = data.ip_address
            db.commit()
            db.refresh(mac_exist)
            result = _display_out(mac_exist)
            return _attach_player_token(result)

    display = DisplayModel(
        name=data.name,
        mac_address=data.mac_address,
        group_name=data.group_name,
        license_key=data.license_key,
        status=DisplayStatus.ONLINE.value,
        last_heartbeat=datetime.now(),
        screen_width=data.screen_width,
        screen_height=data.screen_height,
        screen_orientation=(
            "landscape" if (data.screen_width or 0) >= (data.screen_height or 0) else "portrait"
        ) if data.screen_width and data.screen_height else None,
        platform=data.platform,
        ip_address=data.ip_address,
    )
    db.add(display)
    db.commit()
    db.refresh(display)
    result = _display_out(display)
    return _attach_player_token(result)


def _attach_player_token(result):
    """在返回结果中附带 player_token"""
    from server.models import get_or_create_player_secret
    result_dict = result if isinstance(result, dict) else result.model_dump()
    result_dict["player_token"] = get_or_create_player_secret()
    return result_dict


@router.get("/list")
def list_displays(
    group_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(DisplayModel)

    if group_id is not None:
        query = query.filter(DisplayModel.group_id == group_id)
    elif group_id == -1:
        # 特殊值：未分组
        query = query.filter(DisplayModel.group_id == None)

    if status:
        query = query.filter(DisplayModel.status == status)

    if search:
        query = query.filter(
            DisplayModel.name.contains(search) |
            DisplayModel.ip_address.contains(search)
        )

    items = query.order_by(DisplayModel.name).all()
    return [_display_out(d) for d in items]


@router.get("/count")
def count_displays(db: Session = Depends(get_db)):
    """获取屏幕统计"""
    total = db.query(DisplayModel).count()
    online = db.query(DisplayModel).filter(DisplayModel.status == "online").count()
    return {"total": total, "online": online}


@router.post("/{display_id}/heartbeat")
def heartbeat(display_id: int, data: Optional[HeartbeatData] = None, db: Session = Depends(get_db)):
    """Player 心跳上报"""
    d = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not d:
        raise HTTPException(404, "屏幕不存在")
    
    d.status = "online"
    d.last_heartbeat = datetime.now()
    
    if data:
        if data.platform:
            d.platform = data.platform
        if data.ip_address:
            d.ip_address = data.ip_address
        if data.screen_width:
            d.screen_width = data.screen_width
        if data.screen_height:
            d.screen_height = data.screen_height
        if data.screen_width and data.screen_height:
            d.screen_orientation = (
                "landscape" if data.screen_width >= data.screen_height else "portrait"
            )
    
    db.commit()
    return {"ok": True}


@router.get("/{display_id}")
def get_display(display_id: int, db: Session = Depends(get_db)):
    d = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not d:
        raise HTTPException(404, "屏幕不存在")
    return _display_out(d)


@router.put("/batch/group")
def batch_set_group(data: dict, db: Session = Depends(get_db)):
    """批量设置设备分组"""
    from server.models import DeviceGroupModel

    display_ids = data.get("display_ids", [])
    group_id = data.get("group_id")

    if not display_ids:
        raise HTTPException(400, "请选择设备")

    if group_id is not None:
        group = db.query(DeviceGroupModel).get(group_id)
        if not group:
            raise HTTPException(404, "分组不存在")
        group_name = group.name
    else:
        group_name = "default"
        group_id = None

    db.query(DisplayModel).filter(
        DisplayModel.id.in_(display_ids)
    ).update(
        {"group_id": group_id, "group_name": group_name},
        synchronize_session=False
    )
    db.commit()

    return {"ok": True, "updated": len(display_ids)}


@router.put("/batch/layout")
def batch_set_layout(data: dict, db: Session = Depends(get_db)):
    """批量绑定布局"""
    display_ids = data.get("display_ids", [])
    layout_id = data.get("layout_id")

    if not display_ids:
        raise HTTPException(400, "请选择设备")

    db.query(DisplayModel).filter(
        DisplayModel.id.in_(display_ids)
    ).update(
        {"current_layout_id": layout_id},
        synchronize_session=False
    )
    db.commit()

    # 通知设备刷新
    from server.api.player_sync import notify_display
    for did in display_ids:
        notify_display(did, "refresh", {})

    return {"ok": True, "updated": len(display_ids)}


@router.post("/command")
def send_command(data: CommandRequest, request: Request = None, db: Session = Depends(get_db)):
    """向屏幕发送指令（截屏/熄屏/唤醒/重启）"""
    target_ids = data.display_ids if data.display_ids else []
    if not target_ids:
        # 未指定屏幕，发送给所有在线屏幕
        displays = db.query(DisplayModel).filter(DisplayModel.status == "online").all()
        target_ids = [d.id for d in displays]

    for did in target_ids:
        d = db.query(DisplayModel).filter(DisplayModel.id == did).first()
        if d:
            d.add_command(data.command.value)

    db.commit()

    # SSE 实时推送
    from server.api.player_sync import notify_display, notify_all_displays
    if target_ids:
        for did in target_ids:
            notify_display(did, "command", {"command": data.command.value})
    else:
        notify_all_displays("command", {"command": data.command.value})

    # 记录下发日志
    from server.api.command_log import log_command
    for did in target_ids:
        d = db.query(DisplayModel).filter(DisplayModel.id == did).first()
        if d:
            log_command(db, display_id=did, display_name=d.name,
                        command=data.command.value, triggered_by="manual")

    return {"ok": True, "sent_to": len(target_ids)}


@router.put("/{display_id}")
def update_display(display_id: int, data: dict, request: Request = None, db: Session = Depends(get_db)):
    """更新屏幕信息（名称、分组等）"""
    from server.models import DeviceGroupModel

    d = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not d:
        raise HTTPException(404, "屏幕不存在")

    if "name" in data:
        d.name = data["name"]

    if "current_layout_id" in data:
        d.current_layout_id = data["current_layout_id"]

    # 支持两种方式设置分组
    if "group_id" in data and data["group_id"]:
        d.group_id = data["group_id"]
        group = db.query(DeviceGroupModel).get(data["group_id"])
        if group:
            d.group_name = group.name
    elif "group_name" in data:
        d.group_name = data["group_name"]
        group = db.query(DeviceGroupModel).filter(
            DeviceGroupModel.name == data["group_name"]
        ).first()
        if not group:
            group = DeviceGroupModel(name=data["group_name"])
            db.add(group)
            db.flush()
        d.group_id = group.id

    db.commit()
    db.refresh(d)

    # 记录更新日志
    from server.api.audit import log_action
    log_action(db, action="update", resource="display", resource_id=display_id,
               detail={"name": d.name}, request=request)

    # 如果绑定了布局，通知设备立即刷新
    if "current_layout_id" in data:
        from server.api.player_sync import notify_display
        notify_display(display_id, "sync", {})

    return _display_out(d)


@router.post("/{display_id}/screenshot")
async def upload_screenshot(display_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传截图"""
    d = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not d:
        raise HTTPException(404, "屏幕不存在")

    # 检查截图文件大小（最大 10MB）
    MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024
    if file.size and file.size > MAX_SCREENSHOT_SIZE:
        raise HTTPException(413, "截图文件过大，最大 10MB")

    ss_dir = _get_screenshot_dir()
    # 带时间戳命名，保留历史
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"display_{display_id}_{timestamp}.jpg"
    filepath = os.path.join(ss_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    d.screenshot_updated_at = datetime.now()
    db.commit()

    return {"ok": True}


@router.get("/{display_id}/screenshot")
def get_screenshot(display_id: int, db: Session = Depends(get_db)):
    """获取某屏幕的最新截图"""
    d = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not d:
        raise HTTPException(404, "屏幕不存在")

    ss_dir = _get_screenshot_dir()
    # 找该屏幕最新的截图文件
    prefix = f"display_{display_id}_"
    candidates = sorted(
        [f for f in os.listdir(ss_dir) if f.startswith(prefix) and f.endswith(".jpg")],
        reverse=True
    )
    if not candidates:
        raise HTTPException(404, "暂无截图")

    filepath = os.path.join(ss_dir, candidates[0])
    return FileResponse(filepath, media_type="image/jpeg")


def _display_out(d: DisplayModel) -> dict:
    # 查找最新截图
    last_screenshot = _find_latest_screenshot(d.id)

    result = {
        "id": d.id,
        "name": d.name,
        "mac_address": d.mac_address,
        "group_name": d.group_name,
        "group_id": d.group_id,
        "status": d.status,
        "last_heartbeat": d.last_heartbeat,
        "current_layout_id": d.current_layout_id,
        "screenshot_updated_at": d.screenshot_updated_at,
        "last_screenshot": last_screenshot,
        "screen_width": d.screen_width,
        "screen_height": d.screen_height,
        "screen_orientation": d.screen_orientation,
        "platform": d.platform,
        "ip_address": d.ip_address,
        "created_at": d.created_at,
    }

    # 附加分组详情
    if d.group_id:
        from server.models import DeviceGroupModel, SessionLocal
        db = SessionLocal()
        try:
            group = db.query(DeviceGroupModel).get(d.group_id)
            if group:
                result["group"] = {"id": group.id, "name": group.name}
        finally:
            db.close()

    return result


def _find_latest_screenshot(display_id: int) -> Optional[str]:
    """查找指定屏幕的最新截图文件名"""
    ss_dir = _get_screenshot_dir()
    prefix = f"display_{display_id}_"
    try:
        candidates = sorted(
            [f for f in os.listdir(ss_dir) if f.startswith(prefix) and f.endswith(".jpg")],
            reverse=True
        )
        return candidates[0] if candidates else None
    except FileNotFoundError:
        return None


@router.delete("/{display_id}")
def delete_display(display_id: int, request: Request, db: Session = Depends(get_db)):
    """删除屏幕"""
    d = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not d:
        raise HTTPException(404, "屏幕不存在")
    
    # 检查是否被排程引用
    from server.models import ScheduleModel
    schedules = db.query(ScheduleModel).filter(
        ScheduleModel.display_ids.contains(str(display_id))
    ).all()
    if schedules:
        ref_names = [s.name for s in schedules[:5]]
        raise HTTPException(409, f"该屏幕被以下排程引用: {', '.join(ref_names)}，请先删除相关排程")
    
    name = d.name
    db.delete(d)
    db.commit()

    # 记录删除日志
    from server.api.audit import log_action
    log_action(db, action="delete", resource="display", resource_id=display_id,
               detail={"name": name}, request=request)

    return {"ok": True}
