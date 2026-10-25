"""营销物料路由

医生海报底部小程序码等患者端营销物料接口。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.modules.marketing.schemas import PosterQrcodeResponse
from app.modules.marketing.service import MarketingPosterService

router = APIRouter()


@router.get("/poster-qrcode", response_model=PosterQrcodeResponse, summary="生成医生海报小程序码")
async def get_poster_qrcode(
    scene: str = Query(..., min_length=1, max_length=32, description="场景值（如医生ID），最长 32 字符"),
    page: str | None = Query(None, max_length=128, description="扫码进入的页面路径，缺省进入主页"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """生成医生海报底部的小程序码（PNG base64），需患者登录态"""
    service = MarketingPosterService(db)
    image = await service.generate_poster_qrcode(scene=scene, page=page)
    return PosterQrcodeResponse(image=image)
