"""Player 同步 API（轮询 + SSE 推送）"""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse, StreamingResponse

from server.models import get_db, DisplayModel, LayoutModel, MediaModel
from server.api.schedule import get_active_schedule_for_display
from server.api.media import get_media_file_path
from shared.schemas import SyncResponse, LayoutOut, MediaOut, MediaType, LayoutType, SplitRatio, ZoneConfig, MarqueeConfig, ScheduleOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/player", tags=["Player 同步"])

# 全局 SSE 客户端注册表: {display_id: asyncio.Queue}
_sse_clients: dict[int, asyncio.Queue] = {}
_sse_lock = asyncio.Lock()


def _get_running_loop() -> asyncio.AbstractEventLoop | None:
    """安全获取当前运行中的事件循环"""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def notify_display(display_id: int, event: str, data: dict):
    """向指定屏幕推送 SSE 事件（线程安全）"""
    q = _sse_clients.get(display_id)
    if not q:
        return
    loop = _get_running_loop()
    if not loop:
        # 在同步上下文中，降级为轮询模式
        return
    try:
        msg = json.dumps({"event": event, "data": data})
        loop.call_soon_threadsafe(q.put_nowait, msg)
    except Exception:
        pass


def notify_all_displays(event: str, data: dict):
    """向所有连接的屏幕推送 SSE 事件（线程安全）"""
    loop = _get_running_loop()
    if not loop:
        return
    msg = json.dumps({"event": event, "data": data})
    for display_id, q in list(_sse_clients.items()):
        try:
            loop.call_soon_threadsafe(q.put_nowait, msg)
        except Exception:
            pass


@router.get("/sync/{display_id}")
def sync(display_id: int, db: Session = Depends(get_db)):
    """Player 定时轮询接口"""
    display = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not display:
        raise HTTPException(404, "屏幕未注册")

    # 更新在线状态
    display.status = "online"
    display.last_heartbeat = datetime.now()

    # 获取待执行指令
    commands = display.get_commands()
    display.clear_commands()
    db.commit()

    # 查询当前排程
    schedule = get_active_schedule_for_display(db, display_id)
    current_schedule = None
    current_layout = None
    media_list = []

    if schedule:
        current_schedule = ScheduleOut(
            id=schedule.id,
            name=schedule.name,
            layout_id=schedule.layout_id,
            display_ids=schedule.get_display_ids(),
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            priority=schedule.priority,
            is_active=schedule.is_active,
            repeat_type=schedule.repeat_type or "none",
            repeat_days=schedule.get_repeat_days() if schedule.repeat_type != "none" else None,
            repeat_start_time=schedule.repeat_start_time,
            repeat_end_time=schedule.repeat_end_time,
            repeat_until=schedule.repeat_until,
            created_at=schedule.created_at,
        )

        layout = db.query(LayoutModel).filter(LayoutModel.id == schedule.layout_id).first()
    elif display.current_layout_id:
        # 无排程时，用设备绑定的布局兜底
        layout = db.query(LayoutModel).filter(LayoutModel.id == display.current_layout_id).first()
    else:
        layout = None

    if layout:
        zones = [ZoneConfig(**z) for z in layout.get_zones()]
        marquee_data = layout.get_marquee()
        marquee = MarqueeConfig(**marquee_data) if marquee_data else None

        current_layout = LayoutOut(
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
            updated_at=layout.updated_at,
        )

        # 收集相关素材
        media_ids = set()
        for z in zones:
            if z.media_id:
                media_ids.add(z.media_id)
        if layout.bgm_media_id:
            media_ids.add(layout.bgm_media_id)

        if media_ids:
            medias = db.query(MediaModel).filter(MediaModel.id.in_(media_ids)).all()
            media_list = [
                MediaOut(
                    id=m.id,
                    name=m.name,
                    type=MediaType(m.type),
                    file_path=m.file_path,
                    thumbnail_path=m.thumbnail_path,
                    duration_seconds=m.duration_seconds,
                    file_size=m.file_size,
                    ppt_images=m.get_ppt_images() or None,
                    ppt_slide_duration=m.ppt_slide_duration or 30,
                    created_at=m.created_at,
                )
                for m in medias
            ]

    return SyncResponse(
        display_id=display_id,
        display_name=display.name,
        current_schedule=current_schedule,
        current_layout=current_layout,
        media_list=media_list,
        commands=commands,
        server_time=datetime.now(),
    )


@router.get("/download/{relative_path:path}")
def download_media(relative_path: str):
    """Player 下载素材文件"""
    filepath = get_media_file_path(relative_path)
    return FileResponse(filepath)


@router.get("/events/{display_id}")
async def sse_events(display_id: int, request: Request, db: Session = Depends(get_db)):
    """SSE 推送端点 —— Player 保持长连接接收实时指令"""
    display = db.query(DisplayModel).filter(DisplayModel.id == display_id).first()
    if not display:
        raise HTTPException(404, "屏幕未注册")

    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    async with _sse_lock:
        _sse_clients[display_id] = queue

    async def event_generator():
        try:
            # 发送初始连接确认
            yield f"event: connected\ndata: {{\"display_id\": {display_id}}}\n\n"

            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break

                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    payload = json.loads(msg)
                    yield f"event: {payload['event']}\ndata: {json.dumps(payload['data'])}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            async with _sse_lock:
                _sse_clients.pop(display_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
