"""设备分组 API"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.models import get_db, DeviceGroupModel, DisplayModel

router = APIRouter(prefix="/device-groups", tags=["设备分组"])


class GroupCreate(BaseModel):
    name: str
    description: str = ""
    sort_order: int = 0


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class GroupSortItem(BaseModel):
    id: int
    sort_order: int


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    sort_order: int
    device_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("")
def list_groups(db: Session = Depends(get_db)):
    """获取所有分组"""
    groups = db.query(DeviceGroupModel).order_by(
        DeviceGroupModel.sort_order,
        DeviceGroupModel.id
    ).all()

    result = []
    for g in groups:
        device_count = db.query(DisplayModel).filter(DisplayModel.group_id == g.id).count()
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "sort_order": g.sort_order,
            "device_count": device_count,
            "created_at": g.created_at,
        })

    # 添加"未分组"统计
    ungrouped_count = db.query(DisplayModel).filter(
        DisplayModel.group_id == None
    ).count()

    return {
        "groups": result,
        "ungrouped_count": ungrouped_count
    }


@router.post("")
def create_group(data: GroupCreate, request: Request = None, db: Session = Depends(get_db)):
    """创建分组"""
    existing = db.query(DeviceGroupModel).filter(
        DeviceGroupModel.name == data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="分组名称已存在")

    group = DeviceGroupModel(
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    from server.api.audit import log_action
    log_action(db, action="create", resource="group", resource_id=group.id,
               detail={"name": group.name}, request=request)

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "sort_order": group.sort_order,
        "device_count": 0,
        "created_at": group.created_at,
    }


@router.put("/{group_id}")
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db)):
    """更新分组"""
    group = db.query(DeviceGroupModel).get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    if data.name is not None:
        existing = db.query(DeviceGroupModel).filter(
            DeviceGroupModel.name == data.name,
            DeviceGroupModel.id != group_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="分组名称已存在")

        old_name = group.name
        group.name = data.name
        # 同步更新关联设备的 group_name
        db.query(DisplayModel).filter(
            DisplayModel.group_id == group_id,
            DisplayModel.group_name == old_name
        ).update({"group_name": data.name})

    if data.description is not None:
        group.description = data.description
    if data.sort_order is not None:
        group.sort_order = data.sort_order

    db.commit()
    db.refresh(group)

    from server.api.audit import log_action
    log_action(db, action="update", resource="group", resource_id=group_id,
               detail={"name": group.name}, request=request)

    device_count = db.query(DisplayModel).filter(DisplayModel.group_id == group.id).count()

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "sort_order": group.sort_order,
        "device_count": device_count,
        "created_at": group.created_at,
    }


@router.delete("/{group_id}")
def delete_group(group_id: int, request: Request = None, db: Session = Depends(get_db)):
    """删除分组"""
    group = db.query(DeviceGroupModel).get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    name = group.name
    # 将关联设备的 group_id 设为 None
    db.query(DisplayModel).filter(
        DisplayModel.group_id == group_id
    ).update({"group_id": None})

    db.delete(group)
    db.commit()

    from server.api.audit import log_action
    log_action(db, action="delete", resource="group", resource_id=group_id,
               detail={"name": name}, request=request)

    return {"message": "分组已删除"}


@router.put("/sort")
def update_group_sort(items: List[GroupSortItem], db: Session = Depends(get_db)):
    """批量更新分组排序"""
    for item in items:
        group = db.query(DeviceGroupModel).get(item.id)
        if group:
            group.sort_order = item.sort_order

    db.commit()
    return {"message": "排序已更新"}
