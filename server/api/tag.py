"""标签管理 API"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.models import get_db, TagModel, MediaModel, media_tags

router = APIRouter(prefix="/tags", tags=["标签管理"])


class TagCreate(BaseModel):
    name: str
    color: str = "#3B82F6"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class MediaTagUpdate(BaseModel):
    tag_ids: List[int]


@router.get("")
def list_tags(db: Session = Depends(get_db)):
    """获取所有标签"""
    tags = db.query(TagModel).order_by(TagModel.id).all()
    result = []
    for t in tags:
        count = db.query(media_tags).filter(media_tags.c.tag_id == t.id).count()
        result.append({
            "id": t.id,
            "name": t.name,
            "color": t.color,
            "count": count,
            "created_at": t.created_at,
        })
    return result


@router.post("")
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """创建标签"""
    existing = db.query(TagModel).filter(TagModel.name == data.name).first()
    if existing:
        raise HTTPException(400, "标签名已存在")
    tag = TagModel(name=data.name, color=data.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "name": tag.name, "color": tag.color, "count": 0}


@router.put("/{tag_id}")
def update_tag(tag_id: int, data: TagUpdate, db: Session = Depends(get_db)):
    """更新标签"""
    tag = db.query(TagModel).filter(TagModel.id == tag_id).first()
    if not tag:
        raise HTTPException(404, "标签不存在")
    if data.name is not None:
        existing = db.query(TagModel).filter(
            TagModel.name == data.name, TagModel.id != tag_id
        ).first()
        if existing:
            raise HTTPException(400, "标签名已存在")
        tag.name = data.name
    if data.color is not None:
        tag.color = data.color
    db.commit()
    return {"id": tag.id, "name": tag.name, "color": tag.color}


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """删除标签"""
    tag = db.query(TagModel).filter(TagModel.id == tag_id).first()
    if not tag:
        raise HTTPException(404, "标签不存在")
    db.execute(media_tags.delete().where(media_tags.c.tag_id == tag_id))
    db.delete(tag)
    db.commit()
    return {"ok": True}


@router.get("/media/{media_id}")
def get_media_tags(media_id: int, db: Session = Depends(get_db)):
    """获取素材的标签"""
    tag_ids = [r[0] for r in db.query(media_tags.c.tag_id).filter(
        media_tags.c.media_id == media_id
    ).all()]
    tags = db.query(TagModel).filter(TagModel.id.in_(tag_ids)).all() if tag_ids else []
    return [{"id": t.id, "name": t.name, "color": t.color} for t in tags]


@router.put("/media/{media_id}")
def set_media_tags(media_id: int, data: MediaTagUpdate, db: Session = Depends(get_db)):
    """设置素材的标签（替换）"""
    media = db.query(MediaModel).filter(MediaModel.id == media_id).first()
    if not media:
        raise HTTPException(404, "素材不存在")
    db.execute(media_tags.delete().where(media_tags.c.media_id == media_id))
    for tag_id in data.tag_ids:
        tag = db.query(TagModel).filter(TagModel.id == tag_id).first()
        if tag:
            db.execute(media_tags.insert().values(media_id=media_id, tag_id=tag_id))
    db.commit()
    return {"ok": True}
