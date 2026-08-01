"""企业信息模块接口（创建/查询企业档案）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db.models import BusinessRecord, SyncSession
from src.models.business import BusinessProfile


logger = logging.getLogger(__name__)

router = APIRouter()


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
    """企业信息统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        响应数据载荷。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


@router.post("/business", response_model=BusinessResponse)
async def create_business(req: BusinessCreateRequest) -> BusinessResponse:
    """创建企业信息档案。

    这是整条链路的起点。小老板填写基本信息后，从这里开始后续流程。

    Parameters
    ----------
    req : BusinessCreateRequest
        企业创建请求体，包含企业基本信息。

    Returns
    -------
    BusinessResponse
        创建成功的企业信息，包含 id、business_name、created_at。

    Raises
    ------
    HTTPException
        - 422: 必填字段不完整。
        - 500: 数据库写入失败。

    Examples
    --------
    >>> req = BusinessCreateRequest(
    ...     business_name="示例公司",
    ...     industry="餐饮",
    ...     city="北京",
    ...     product_desc="特色火锅",
    ...     target_customers="年轻白领"
    ... )
    >>> resp = await create_business(req)
    >>> resp.code
    0
    """
    profile = BusinessProfile(**req.model_dump())
    if not profile.is_complete():
        raise HTTPException(
            status_code=422,
            detail="必填字段不完整：企业名称、行业、城市、产品描述、目标客户",
        )

    record = BusinessRecord(**req.model_dump())
    session = SyncSession()

    try:
        session.add(record)
        session.commit()
        session.refresh(record)

        logger.info("企业创建成功: %s (id=%s)", record.business_name, record.id)

        return BusinessResponse(
            data={
                "id": record.id,
                "business_name": record.business_name,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        )
    except Exception as e:
        session.rollback()
        logger.exception("创建企业失败: %s", e)
        raise HTTPException(status_code=500, detail=f"创建失败: {e}") from e
    finally:
        session.close()


@router.post("/business/create", response_model=BusinessResponse)
async def create_business_v3(req: BusinessCreateRequest) -> BusinessResponse:
    """[V3.0 别名] 创建企业信息档案。

    与 POST /api/business 内部调用同一逻辑，作为文档V3.0规范命名别名。

    Parameters
    ----------
    req : BusinessCreateRequest
        企业创建请求体，包含企业基本信息。

    Returns
    -------
    BusinessResponse
        创建成功的企业信息。
    """
    return await create_business(req)


@router.get("/business/info", response_model=BusinessResponse)
async def get_business_info(
    business_id: Optional[str] = None,
) -> BusinessResponse:
    """[V3.0] 获取企业信息（无路径参数版）。

    优先从 query/header 获取 business_id，若无则返回最新一条企业记录。

    Parameters
    ----------
    business_id : Optional[str]
        企业ID（可选），未提供则返回最新企业记录。

    Returns
    -------
    BusinessResponse
        企业完整档案信息。

    Raises
    ------
    HTTPException
        - 404: 企业不存在或暂无企业信息。
    """
    session = SyncSession()
    try:
        if business_id:
            record = session.query(BusinessRecord).filter_by(id=business_id).first()
            if not record:
                raise HTTPException(status_code=404, detail="企业不存在")
        else:
            record = (
                session.query(BusinessRecord).order_by(BusinessRecord.created_at.desc()).first()
            )
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
    finally:
        session.close()


@router.get("/business/{business_id}", response_model=BusinessResponse)
async def get_business(business_id: str) -> BusinessResponse:
    """查询企业信息。

    Parameters
    ----------
    business_id : str
        企业唯一标识ID。

    Returns
    -------
    BusinessResponse
        企业完整档案信息。

    Raises
    ------
    HTTPException
        - 404: 企业不存在。
    """
    session = SyncSession()
    try:
        record = session.query(BusinessRecord).filter_by(id=business_id).first()
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
    finally:
        session.close()
