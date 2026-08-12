"""企业信息模块接口（创建/查询企业档案）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.auth import get_current_user
from sqlalchemy import select

from backend.db.models import AsyncSessionLocal, BusinessRecord
from backend.models.business import BusinessProfile


logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


class BusinessCreateRequest(BaseModel):
    """创建企业信息请求。

    Parameters
    ----------
    business_name : str
        企业名称（必填）。
    industry : str
        所属行业（必填）。
    city : str
        所在城市（必填）。
    product_desc : str
        产品/服务描述。
    price_range : str
        价格区间。
    target_customers : str
        目标客户群体。
    competitors : str
        竞争对手分析。
    current_channels : str
        当前获客方式。
    monthly_revenue : str
        月营业额。
    team_size : str
        团队规模。
    biggest_pain : str
        最大营销痛点。
    """

    business_name: str = Field(..., description="企业名称")
    industry: str = Field(..., description="行业")
    city: str = Field(..., description="所在城市")
    product_desc: str = Field("", description="产品/服务描述")
    price_range: str = Field("", description="价格区间")
    target_customers: str = Field("", description="目标客户")
    competitors: str = Field("", description="竞争对手")
    current_channels: str = Field("", description="当前获客方式")
    monthly_revenue: str = Field("", description="月营业额")
    team_size: str = Field("", description="团队规模")
    biggest_pain: str = Field("", description="最大痛点")


class BusinessResponse(BaseModel):
    """企业信息统一响应格式。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


@router.post("/business", response_model=BusinessResponse)
async def create_business(req: BusinessCreateRequest) -> BusinessResponse:
    """创建企业信息档案。"""
    profile = BusinessProfile(**req.model_dump())
    if not profile.is_complete():
        raise HTTPException(
            status_code=422,
            detail="必填字段不完整：企业名称、行业、城市、产品描述、目标客户",
        )

    record = BusinessRecord(**req.model_dump())
    async with AsyncSessionLocal() as session:
        try:
            session.add(record)
            await session.commit()
            await session.refresh(record)

            logger.info("企业创建成功: %s (id=%s)", record.business_name, record.id)

            return BusinessResponse(
                data={
                    "id": record.id,
                    "business_name": record.business_name,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            )
        except Exception as e:
            await session.rollback()
            logger.exception("创建企业失败: %s", e)
            raise HTTPException(status_code=500, detail=f"创建失败: {e}") from e


@router.post("/business/create", response_model=BusinessResponse)
async def create_business_v3(req: BusinessCreateRequest) -> BusinessResponse:
    """[V3.0 别名] 创建企业信息档案。"""
    return await create_business(req)


@router.get("/business/info", response_model=BusinessResponse)
async def get_business_info(
    business_id: Optional[str] = None,
) -> BusinessResponse:
    """[V3.0] 获取企业信息（无路径参数版）。"""
    async with AsyncSessionLocal() as session:
        try:
            if business_id:
                result = await session.execute(
                    select(BusinessRecord).filter_by(id=business_id)
                )
                record = result.scalar_one_or_none()
                if not record:
                    raise HTTPException(status_code=404, detail="企业不存在")
            else:
                result = await session.execute(
                    select(BusinessRecord).order_by(BusinessRecord.created_at.desc())
                )
                record = result.scalars().first()
                if not record:
                    raise HTTPException(status_code=404, detail="暂无企业信息")

            return BusinessResponse(
                data={
                    "id": record.id,
                    "business_name": record.business_name,
                    "industry": record.industry,
                    "city": record.city,
                    "product_desc": record.product_desc,
                    "price_range": record.price_range,
                    "target_customers": record.target_customers,
                    "competitors": record.competitors,
                    "current_channels": record.current_channels,
                    "monthly_revenue": record.monthly_revenue,
                    "team_size": record.team_size,
                    "biggest_pain": record.biggest_pain,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("获取企业信息失败: %s", e)
            raise HTTPException(status_code=500, detail=f"获取失败: {e}") from e


@router.get("/business/{business_id}", response_model=BusinessResponse)
async def get_business(business_id: str) -> BusinessResponse:
    """查询企业信息。"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(BusinessRecord).filter_by(id=business_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                raise HTTPException(status_code=404, detail="企业不存在")

            return BusinessResponse(
                data={
                    "id": record.id,
                    "business_name": record.business_name,
                    "industry": record.industry,
                    "city": record.city,
                    "product_desc": record.product_desc,
                    "price_range": record.price_range,
                    "target_customers": record.target_customers,
                    "competitors": record.competitors,
                    "current_channels": record.current_channels,
                    "monthly_revenue": record.monthly_revenue,
                    "team_size": record.team_size,
                    "biggest_pain": record.biggest_pain,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("获取企业信息失败: %s", e)
            raise HTTPException(status_code=500, detail=f"获取失败: {e}") from e
