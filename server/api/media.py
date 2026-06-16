"""素材管理 API"""

import os
import uuid
import shutil
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from PIL import Image

from server.models import get_db, MediaModel
from shared.schemas import MediaOut, MediaType
from shared.config import get_upload_dir, DEFAULT_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["素材管理"])

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mkv"}
ALLOWED_PPT_EXT = {"pptx", "ppt"}


def _get_media_type(ext: str) -> str:
    ext = ext.lower()
    if ext in ALLOWED_IMAGE_EXT:
        return MediaType.IMAGE.value
    elif ext in ALLOWED_VIDEO_EXT:
        return MediaType.VIDEO.value
    elif ext in ALLOWED_PPT_EXT:
        return MediaType.PPT.value
    else:
        raise HTTPException(400, f"不支持的文件格式: {ext}")


def _create_thumbnail(image_path: str, thumb_path: str, size=(320, 180)):
    """生成缩略图"""
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.LANCZOS)
        img.save(thumb_path, quality=80)
        return thumb_path
    except Exception:
        return None


def _get_video_dimensions(file_path: str):
    """获取视频分辨率（使用 OpenCV）"""
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if w > 0 and h > 0:
                return w, h
    except Exception:
        pass
    return None, None


def _media_out(m: MediaModel) -> MediaOut:
    """将 MediaModel 转换为 MediaOut"""
    return MediaOut(
        id=m.id,
        name=m.name,
        type=MediaType(m.type),
        file_path=m.file_path,
        thumbnail_path=m.thumbnail_path,
        duration_seconds=m.duration_seconds,
        file_size=m.file_size,
        width=m.width,
        height=m.height,
        ppt_images=m.get_ppt_images() or None,
        ppt_slide_duration=m.ppt_slide_duration or 30,
        expires_at=m.expires_at,
        created_at=m.created_at,
    )


@router.post("/upload")
async def upload_media(file: UploadFile = File(...), request: Request = None, db: Session = Depends(get_db)):
    """上传素材文件"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
    media_type = _get_media_type(ext)

    # 检查文件大小
    max_size_mb = DEFAULT_CONFIG.get("max_upload_size_mb", 500)
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size and file.size > max_size_bytes:
        raise HTTPException(413, f"文件过大，最大 {max_size_mb}MB")

    upload_dir = get_upload_dir()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    content = await file.read()
    file_size = len(content)

    with open(file_path, "wb") as f:
        f.write(content)

    # 生成缩略图（图片类型）
    thumbnail_path = None
    duration_seconds = None
    img_width = None
    img_height = None
    if media_type == MediaType.IMAGE.value:
        thumb_name = f"thumb_{unique_name.rsplit('.', 1)[0]}.jpg"
        thumb_path = os.path.join(upload_dir, thumb_name)
        thumbnail_path = _create_thumbnail(file_path, thumb_path)
        if thumbnail_path:
            thumbnail_path = thumb_name  # 存相对路径
        # 获取图片分辨率
        try:
            from PIL import Image as PILImage
            with PILImage.open(file_path) as img:
                img_width, img_height = img.size
        except Exception:
            pass
    elif media_type == MediaType.VIDEO.value:
        # 获取视频分辨率
        try:
            img_width, img_height = _get_video_dimensions(file_path)
        except Exception:
            pass

    # PPT 自动转换：上传后转为图片序列
    ppt_file_path = None
    ppt_all_images = None
    if media_type == MediaType.PPT.value:
        from server.ppt_converter import convert_pptx_upload
        try:
            ppt_dir_name, ppt_images = convert_pptx_upload(file_path, upload_dir)
            if ppt_images:
                ppt_output_dir = os.path.join(upload_dir, ppt_dir_name)
                first_img_path = os.path.join(ppt_output_dir, ppt_images[0])
                if os.path.exists(first_img_path):
                    # 缩略图
                    thumb_name = f"thumb_{ppt_dir_name}.jpg"
                    thumb_path = os.path.join(upload_dir, thumb_name)
                    result = _create_thumbnail(first_img_path, thumb_path)
                    if result:
                        thumbnail_path = thumb_name
                    # file_path 指向第一张幻灯片（Player 可直接下载显示）
                    ppt_file_path = f"{ppt_dir_name}/{ppt_images[0]}"
                    # 保存所有 PPT 图片路径
                    ppt_all_images = [f"{ppt_dir_name}/{img}" for img in ppt_images]
        except Exception as e:
            logger.warning(f"PPT 转换失败: {e}")  # PPT 转换失败不影响上传

    media = MediaModel(
        name=file.filename,
        type=media_type,
        file_path=ppt_file_path or unique_name,
        thumbnail_path=thumbnail_path,
        duration_seconds=duration_seconds,
        file_size=file_size,
        width=img_width,
        height=img_height,
    )
    if ppt_all_images:
        media.set_ppt_images(ppt_all_images)
    db.add(media)
    db.commit()
    db.refresh(media)

    # 记录上传日志
    from server.api.audit import log_action
    log_action(db, action="create", resource="media", resource_id=media.id,
               detail={"name": media.name, "type": media.type}, request=request)

    return _media_out(media)


@router.get("/list")
def list_media(media_type: str = None, db: Session = Depends(get_db)):
    """获取素材列表"""
    q = db.query(MediaModel)
    if media_type:
        q = q.filter(MediaModel.type == media_type)
    items = q.order_by(MediaModel.created_at.desc()).all()
    return [_media_out(m) for m in items]


@router.get("/count")
def count_media(db: Session = Depends(get_db)):
    """获取素材统计"""
    total = db.query(MediaModel).count()
    return {"total": total}


@router.get("/{media_id}/slides")
def get_ppt_slides(media_id: int, db: Session = Depends(get_db)):
    """获取 PPT 转换后的所有页面图片路径"""
    m = db.query(MediaModel).filter(MediaModel.id == media_id).first()
    if not m:
        raise HTTPException(404, "素材不存在")
    if m.type != MediaType.PPT.value:
        raise HTTPException(400, "非 PPT 素材")

    upload_dir = get_upload_dir()
    # file_path 格式为 "ppt_xxx/slide_001.png"，取目录部分
    ppt_dir_name = m.file_path.rsplit("/", 1)[0] if "/" in m.file_path else m.file_path
    ppt_dir = os.path.join(upload_dir, ppt_dir_name)
    if not os.path.isdir(ppt_dir):
        return {"slides": []}

    slides = sorted([
        f for f in os.listdir(ppt_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    return {"slides": [f"{ppt_dir_name}/{s}" for s in slides]}


@router.get("/{media_id}")
def get_media(media_id: int, db: Session = Depends(get_db)):
    m = db.query(MediaModel).filter(MediaModel.id == media_id).first()
    if not m:
        raise HTTPException(404, "素材不存在")
    return _media_out(m)


class MediaUpdate(BaseModel):
    """素材更新"""
    name: Optional[str] = None
    ppt_slide_duration: Optional[int] = None  # PPT 每页播放时长
    expires_at: Optional[str] = None  # 过期时间 ISO 格式，null=不过期


@router.put("/{media_id}")
def update_media(media_id: int, data: MediaUpdate, request: Request = None, db: Session = Depends(get_db)):
    """更新素材信息（名称等）"""
    m = db.query(MediaModel).filter(MediaModel.id == media_id).first()
    if not m:
        raise HTTPException(404, "素材不存在")
    if data.name:
        m.name = data.name.strip()
    if data.ppt_slide_duration is not None and m.type == MediaType.PPT.value:
        m.ppt_slide_duration = max(1, min(86400, data.ppt_slide_duration))
    if data.expires_at is not None:
        if data.expires_at == "" or data.expires_at.lower() == "null":
            m.expires_at = None
        else:
            try:
                from datetime import datetime
                m.expires_at = datetime.fromisoformat(data.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(400, "无效的过期时间格式")
    db.commit()
    db.refresh(m)

    from server.api.audit import log_action
    log_action(db, action="update", resource="media", resource_id=media_id,
               detail={"name": m.name}, request=request)

    return _media_out(m)


@router.delete("/{media_id}")
def delete_media(media_id: int, force: bool = False, request: Request = None, db: Session = Depends(get_db)):
    """删除素材"""
    m = db.query(MediaModel).filter(MediaModel.id == media_id).first()
    if not m:
        raise HTTPException(404, "素材不存在")

    # 检查是否被布局引用
    from server.models import LayoutModel
    layouts = db.query(LayoutModel).all()
    ref_layouts = []
    for layout in layouts:
        zones = layout.get_zones()
        for z in zones:
            if z.get("media_id") == media_id:
                ref_layouts.append(layout.name)
                break
        if layout.bgm_media_id == media_id:
            ref_layouts.append(f"{layout.name}(BGM)")
    if ref_layouts and not force:
        raise HTTPException(409, f"该素材被以下布局引用: {', '.join(ref_layouts)}，请先解除引用或使用 force=true 强制删除")

    upload_dir = get_upload_dir()
    # 删除文件（兼容目录和文件两种路径）
    file_path = os.path.join(upload_dir, m.file_path)
    if os.path.isfile(file_path):
        os.remove(file_path)
    elif os.path.isdir(file_path):
        shutil.rmtree(file_path, ignore_errors=True)
    # PPT 素材：清理转换目录（file_path 可能是 ppt_xxx/slide_001.png，需删整个 ppt_xxx 目录）
    if m.type == MediaType.PPT.value:
        # 从 file_path 中提取 ppt 目录
        parts = m.file_path.split("/")
        if len(parts) >= 2 and parts[0].startswith("ppt_"):
            ppt_dir = os.path.join(upload_dir, parts[0])
            if os.path.isdir(ppt_dir):
                shutil.rmtree(ppt_dir, ignore_errors=True)
        # 也清理可能残留的原始 .pptx 文件
        for f in os.listdir(upload_dir):
            if f.endswith(".pptx") and not os.path.isdir(os.path.join(upload_dir, f)):
                # 检查是否是这个 PPT 的原始文件（通过缩略图前缀关联）
                if m.thumbnail_path and f.replace(".pptx", "") in m.thumbnail_path:
                    try:
                        os.remove(os.path.join(upload_dir, f))
                    except OSError:
                        pass
    if m.thumbnail_path:
        thumb_path = os.path.join(upload_dir, m.thumbnail_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

    db.delete(m)
    db.commit()

    # 记录删除日志
    from server.api.audit import log_action
    log_action(db, action="delete", resource="media", resource_id=media_id,
               detail={"name": m.name, "type": m.type}, request=request)

    return {"ok": True}


def get_media_file_path(relative_path: str) -> str:
    """获取素材文件的绝对路径（防路径遍历）"""
    upload_dir = get_upload_dir()
    abs_path = os.path.normpath(os.path.join(upload_dir, relative_path))
    # 禁止路径遍历：确保解析后的路径在 upload_dir 内
    if not abs_path.startswith(os.path.normpath(upload_dir) + os.sep):
        raise HTTPException(403, "禁止访问")
    if not os.path.exists(abs_path):
        raise HTTPException(404, "文件不存在")
    return abs_path
