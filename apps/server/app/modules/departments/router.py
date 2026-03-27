from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter, check_store_access, require_permission
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTreeNode
from app.schemas.doctor import DoctorListResponse
from app.schemas.response import PageResponse
from app.modules.departments.service import DepartmentService
from app.core.config import settings

router = APIRouter()


class SortOrderItem(BaseModel):
    id: str
    sort_order: int


class BatchSortRequest(BaseModel):
    items: List[SortOrderItem]

def _to_response(department) -> DepartmentResponse:
    """将 Department 模型转换为响应对象，包含门店名称"""
    data = DepartmentResponse.model_validate(department)
    if department.store:
        data.store_name = department.store.name
    return data

@router.get("", response_model=PageResponse[DepartmentResponse], summary="获取科室列表")
async def get_departments(
    name: Optional[str] = None,
    status: Optional[int] = None,
    parent_id: Optional[str] = None,
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取科室列表"""
    service = DepartmentService(db)
    
    # 门店过滤：门店管理员只能看自己门店的科室
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    departments, total = await service.get_list(
        name=name, status=status, parent_id=parent_id, store_id=store_id, page=page, page_size=page_size
    )
    
    return PageResponse(
        data=[_to_response(d) for d in departments],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/tree", response_model=List[DepartmentTreeNode], summary="获取科室树")
async def get_department_tree(
    status: Optional[int] = 1,
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取科室树（公开接口，支持门店过滤）
    
    用于患者端显示科室列表
    """
    service = DepartmentService(db)
    return await service.get_tree(status=status, store_id=store_id)

@router.get("/hot", response_model=List[DepartmentResponse], summary="获取热门科室")
async def get_hot_departments(
    limit: int = Query(8, ge=1, le=20),
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取热门科室（公开接口，不需要登录）"""
    service = DepartmentService(db)
    departments = await service.get_hot(limit=limit, store_id=store_id)
    return [_to_response(d) for d in departments]


@router.get("/all", response_model=List[DepartmentResponse], summary="获取所有科室")
async def get_all_departments(
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取所有启用的科室（下拉选择用）
    
    用于管理后台选择器场景，返回所有启用状态的科室
    最大返回 1000 条
    """
    service = DepartmentService(db)
    
    # 门店权限过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    departments = await service.get_all_active(store_id=store_id)
    return [_to_response(d) for d in departments]


@router.put("/batch-sort", summary="批量更新排序")
async def batch_update_sort_order(
    data: BatchSortRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:update"))
):
    """批量更新科室排序"""
    service = DepartmentService(db)
    items = [{"id": item.id, "sort_order": item.sort_order} for item in data.items]
    count = await service.batch_update_sort_order(items)
    return {"message": "排序更新成功", "count": count}

@router.get("/{dept_id}", response_model=DepartmentResponse, summary="获取科室详情")
async def get_department(
    dept_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取科室详情"""
    service = DepartmentService(db)
    department = await service.get_by_id(dept_id)
    
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在，请检查后重试")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, department.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此科室")
    
    return _to_response(department)

@router.post("", response_model=DepartmentResponse, summary="创建科室")
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:create"))
):
    """创建科室"""
    # 检查门店访问权限
    store_filter = get_store_filter(current_admin)
    if store_filter:
        # 门店管理员只能在自己门店创建科室
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能在本门店创建科室，请选择正确的门店")
        data.store_id = store_filter
    
    if not data.store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择所属门店")
    
    service = DepartmentService(db)
    department = await service.create(data)
    return _to_response(department)

@router.put("/{dept_id}", response_model=DepartmentResponse, summary="更新科室")
async def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:update"))
):
    """更新科室"""
    service = DepartmentService(db)
    department = await service.get_by_id(dept_id)
    
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在，请检查后重试")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, department.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改此科室")
    
    # 门店管理员不能修改科室的门店归属
    store_filter = get_store_filter(current_admin)
    if store_filter and data.store_id and data.store_id != store_filter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改科室的门店归属")
    
    department = await service.update(dept_id, data)
    return _to_response(department)

@router.delete("/{dept_id}", summary="删除科室")
async def delete_department(
    dept_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:delete"))
):
    """删除科室"""
    service = DepartmentService(db)
    department = await service.get_by_id(dept_id)
    
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在，请检查后重试")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, department.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权删除此科室")
    
    try:
        success = await service.delete(dept_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科室不存在，请检查后重试")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": "删除成功"}


@router.get("/{dept_id}/doctors", response_model=List[DoctorListResponse], summary="获取科室医生")
async def get_department_doctors(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取科室已绑定的医生列表"""
    service = DepartmentService(db)
    
    # 验证科室是否存在
    department = await service.get_by_id(dept_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="科室不存在，请检查后重试"
        )
    
    # 检查门店访问权限
    if not check_store_access(current_admin, department.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此科室")
    
    doctors = await service.get_doctors(dept_id)
    
    result = []
    for d in doctors:
        item = DoctorListResponse(
            id=d.id,
            name=d.name,
            avatar=d.avatar,
            banner=d.banner,
            title=d.title,
            gender=d.gender,
            store_id=d.store_id,
            department_id=d.department_id,
            specialty=d.specialty,
            is_recommended=d.is_recommended,
            tags=d.tags,
            page_style=d.page_style,
        )
        result.append(item)
    
    return result


@router.get("/{dept_id}/available-doctors", response_model=List[DoctorListResponse], summary="获取可绑定医生")
async def get_available_doctors(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取可绑定到此科室的医生列表（同门店的所有医生）"""
    service = DepartmentService(db)
    
    # 验证科室是否存在
    department = await service.get_by_id(dept_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="科室不存在，请检查后重试"
        )
    
    # 检查门店访问权限
    if not check_store_access(current_admin, department.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此科室")
    
    # 获取同门店的所有医生
    doctors = await service.get_all_doctors(store_id=department.store_id)
    
    result = []
    for d in doctors:
        item = DoctorListResponse(
            id=d.id,
            name=d.name,
            avatar=d.avatar,
            banner=d.banner,
            title=d.title,
            gender=d.gender,
            store_id=d.store_id,
            department_id=d.department_id,
            specialty=d.specialty,
            is_recommended=d.is_recommended,
            tags=d.tags,
            page_style=d.page_style,
        )
        result.append(item)
    
    return result


@router.put("/{dept_id}/doctors/batch", summary="批量绑定医生")
async def batch_bind_doctors(
    dept_id: str,
    doctor_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:update"))
):
    """批量绑定医生到科室"""
    service = DepartmentService(db)
    
    # 验证科室是否存在
    department = await service.get_by_id(dept_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="科室不存在，请检查后重试"
        )
    
    # 检查门店访问权限
    if not check_store_access(current_admin, department.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此科室")
    
    try:
        count = await service.batch_bind_doctors(dept_id, doctor_ids)
        return {"message": "绑定成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
