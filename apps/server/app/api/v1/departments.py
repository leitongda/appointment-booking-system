from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTreeNode
from app.schemas.response import PageResponse
from app.services.department_service import DepartmentService

router = APIRouter()

@router.get("", response_model=PageResponse[DepartmentResponse])
async def get_departments(
    name: Optional[str] = None,
    status: Optional[int] = None,
    parent_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取科室列表"""
    service = DepartmentService(db)
    departments, total = await service.get_list(
        name=name, status=status, parent_id=parent_id, page=page, page_size=page_size
    )
    
    return PageResponse(
        data=[DepartmentResponse.model_validate(d) for d in departments],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/tree", response_model=List[DepartmentTreeNode])
async def get_department_tree(
    status: Optional[int] = 1,
    db: AsyncSession = Depends(get_db)
):
    """获取科室树"""
    service = DepartmentService(db)
    return await service.get_tree(status=status)

@router.get("/hot", response_model=List[DepartmentResponse])
async def get_hot_departments(
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """获取热门科室"""
    service = DepartmentService(db)
    departments = await service.get_hot(limit=limit)
    return [DepartmentResponse.model_validate(d) for d in departments]

@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(dept_id: str, db: AsyncSession = Depends(get_db)):
    """获取科室详情"""
    service = DepartmentService(db)
    department = await service.get_by_id(dept_id)
    
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在")
    
    return DepartmentResponse.model_validate(department)

@router.post("", response_model=DepartmentResponse)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建科室"""
    service = DepartmentService(db)
    department = await service.create(data)
    return DepartmentResponse.model_validate(department)

@router.put("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新科室"""
    service = DepartmentService(db)
    department = await service.update(dept_id, data)
    
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在")
    
    return DepartmentResponse.model_validate(department)

@router.delete("/{dept_id}")
async def delete_department(dept_id: str, db: AsyncSession = Depends(get_db)):
    """删除科室"""
    service = DepartmentService(db)
    
    try:
        success = await service.delete(dept_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": "删除成功"}
