"""诊断模块接口（触发AI诊断/查看诊断报告）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.diagnosis import DiagnosisAgent
from src.db.models import BusinessRecord, DiagnosisRecord, SyncSession
from src.models.business import BusinessProfile
from src.services.rule_based_diagnosis import diagnose as rule_diagnose


logger = logging.getLogger(__name__)

router = APIRouter()


class DiagnosisResponse(BaseModel):
    """诊断统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        诊断报告数据载荷。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class DiagnosisStartRequest(BaseModel):
    """[V3.0] 诊断启动请求体（完整业务参数）。

    Parameters
    ----------
    business_id : Optional[str]
        企业ID（可选，无则新建）。
    company_name : str
        企业名称。
    industry : str
        所属行业。
    city : str
        所在城市。
    team_size : str
        团队规模。
    main_product : str
        主营产品/服务描述。
    price_range : str
        价格区间。
    target_customer : str
        目标客户群体。
    current_channels : List[str]
        当前获客渠道列表。
    monthly_budget : str
        月度营销预算。
    biggest_pain : str
        最大营销痛点。
    """

    business_id: Optional[str] = Field(None, description="企业ID（可选，无则新建）")
    company_name: str = Field(..., description="企业名称")
    industry: str = Field(..., description="行业")
    city: str = Field(..., description="所在城市")
    team_size: str = Field("", description="团队规模")
    main_product: str = Field("", description="主营产品/服务描述")
    price_range: str = Field("", description="价格区间")
    target_customer: str = Field("", description="目标客户")
    current_channels: List[str] = Field(default_factory=list, description="当前获客渠道列表")
    monthly_budget: str = Field("", description="月度营销预算")
    biggest_pain: str = Field("", description="最大痛点")


class _DiagnosisPersistentError(Exception):
    """内部标记：诊断需要 fallback 到规则引擎。"""

    pass


def _record_to_profile(record: BusinessRecord) -> BusinessProfile:
    """DB Record 转换为业务模型 BusinessProfile。

    Parameters
    ----------
    record : BusinessRecord
        数据库企业记录。

    Returns
    -------
    BusinessProfile
        转换后的业务模型实例。
    """
    return BusinessProfile(
        id=record.id,
        business_name=record.business_name,
        industry=record.industry,
        city=record.city,
        product_desc=record.product_desc or "",
        price_range=record.price_range or "",
        target_customers=record.target_customers or "",
        competitors=record.competitors or "",
        current_channels=record.current_channels or "",
        monthly_revenue=record.monthly_revenue or "",
        team_size=record.team_size or "",
        biggest_pain=record.biggest_pain or "",
    )


async def _run_diagnosis_with_fallback(profile: BusinessProfile):
    """Agent 3次重试 + 本地规则引擎兜底。

    参考 pipeline.py 思路实现：优先调用 LLM Agent，失败则降级到规则引擎。

    Parameters
    ----------
    profile : BusinessProfile
        企业档案业务模型。

    Returns
    -------
    Tuple[DiagnosisReport, str]
        诊断报告对象与来源标识（"llm" 或 "rule_based"）。

    Raises
    ------
    _DiagnosisPersistentError
        当 LLM Agent 和规则引擎均失败时抛出。
    """
    last_error = None
    for attempt in range(1, 4):
        try:
            agent = DiagnosisAgent()
            report = await agent.run(profile)
            logger.info("诊断Agent第%d次调用成功 | business=%s", attempt, profile.business_name)
            return report, "llm"
        except Exception as e:
            last_error = e
            logger.warning("诊断Agent第%d次调用失败: %s", attempt, e)
            continue

    logger.warning("诊断Agent连续3次失败，回退到本地规则引擎: %s", last_error)
    try:
        report = rule_diagnose(profile)
        return report, "rule_based"
    except Exception as re:
        logger.error("本地规则引擎也失败: %s", re)
        raise _DiagnosisPersistentError(str(re)) from re


@router.post("/diagnosis/{business_id}", response_model=DiagnosisResponse)
async def run_diagnosis(business_id: str) -> DiagnosisResponse:
    """触发AI诊断。

    委托给 DiagnosisAgent 执行 AI 逻辑，API 层只负责 DB 读写和异常处理。

    Parameters
    ----------
    business_id : str
        企业唯一标识ID（路径参数）。

    Returns
    -------
    DiagnosisResponse
        诊断报告响应，包含评分、问题、策略等完整信息。

    Raises
    ------
    HTTPException
        - 404: 企业不存在。
        - 502: 诊断服务不可用或 Agent 异常。
        - 500: 内部处理异常。
    """
    session = SyncSession()
    try:
        record = session.query(BusinessRecord).filter_by(id=business_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="企业不存在")

        profile = _record_to_profile(record)

        report, _ = await _run_diagnosis_with_fallback(profile)

        db_record = DiagnosisRecord(
            id=uuid.uuid4().hex,
            business_id=business_id,
            overall_score=report.overall_score,
            score_summary=report.score_summary,
            score_breakdown=report.score_breakdown,
            top3_problems=report.to_dict()["top3_problems"],
            strategy_summary=report.strategy_summary,
            this_week_focus=report.this_week_focus,
        )
        session.add(db_record)
        session.commit()
        session.refresh(db_record)

        report.id = db_record.id
        report.created_at = db_record.created_at

        logger.info(
            "诊断完成: business=%s score=%d strategy=%s",
            profile.business_name,
            report.overall_score,
            (report.strategy_summary or "")[:30],
        )

        return DiagnosisResponse(data=report.to_dict())

    except _DiagnosisPersistentError as e:
        raise HTTPException(status_code=502, detail=f"诊断服务不可用: {e}") from e
    except ValueError as e:
        logger.error("诊断 Agent 异常: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.exception("诊断失败: %s", e)
        raise HTTPException(status_code=500, detail=f"诊断失败: {e}") from e
    finally:
        session.close()


@router.post("/diagnosis/start", response_model=DiagnosisResponse)
async def start_diagnosis_v3(req: DiagnosisStartRequest) -> DiagnosisResponse:
    """[V3.0] 启动诊断（文档6.2节规范）。

    接收完整业务参数：business_id, company_name, industry, city,
    team_size, main_product, price_range, target_customer,
    current_channels[], monthly_budget, biggest_pain。

    若 business_id 不存在则新建企业记录，然后启动诊断。
    内部：3次Agent重试 + 本地规则引擎兜底。

    Parameters
    ----------
    req : DiagnosisStartRequest
        诊断启动请求体，包含完整业务参数。

    Returns
    -------
    DiagnosisResponse
        诊断报告响应，包含 business_id 与 diagnosis_source 标识。

    Raises
    ------
    HTTPException
        - 502: 诊断服务不可用或 Agent 异常。
        - 500: 内部处理异常。
    """
    session = SyncSession()
    try:
        if req.business_id:
            record = session.query(BusinessRecord).filter_by(id=req.business_id).first()
            if not record:
                req.business_id = None

        if not req.business_id:
            record = BusinessRecord(
                id=uuid.uuid4().hex,
                business_name=req.company_name,
                industry=req.industry,
                city=req.city,
                product_desc=req.main_product,
                price_range=req.price_range,
                target_customers=req.target_customer,
                current_channels=(",".join(req.current_channels) if req.current_channels else ""),
                monthly_revenue=req.monthly_budget,
                team_size=req.team_size,
                biggest_pain=req.biggest_pain,
            )
            session.add(record)
            session.flush()
            req.business_id = record.id
        else:
            record.business_name = req.company_name
            record.industry = req.industry
            record.city = req.city
            record.product_desc = req.main_product
            record.price_range = req.price_range
            record.target_customers = req.target_customer
            record.current_channels = ",".join(req.current_channels) if req.current_channels else ""
            record.monthly_revenue = req.monthly_budget
            record.team_size = req.team_size
            record.biggest_pain = req.biggest_pain

        session.commit()
        session.refresh(record)

        profile = _record_to_profile(record)
        report, source = await _run_diagnosis_with_fallback(profile)

        db_record = DiagnosisRecord(
            id=uuid.uuid4().hex,
            business_id=req.business_id,
            overall_score=report.overall_score,
            score_summary=report.score_summary,
            score_breakdown=report.score_breakdown,
            top3_problems=report.to_dict()["top3_problems"],
            strategy_summary=report.strategy_summary,
            this_week_focus=report.this_week_focus,
        )
        session.add(db_record)
        session.commit()
        session.refresh(db_record)

        report.id = db_record.id
        report.created_at = db_record.created_at

        result_data = report.to_dict()
        result_data["business_id"] = req.business_id
        result_data["diagnosis_source"] = source

        logger.info(
            "[V3.0]诊断完成: business=%s score=%d source=%s",
            profile.business_name,
            report.overall_score,
            source,
        )

        return DiagnosisResponse(data=result_data)

    except _DiagnosisPersistentError as e:
        session.rollback()
        raise HTTPException(status_code=502, detail=f"诊断服务不可用: {e}") from e
    except ValueError as e:
        session.rollback()
        logger.error("诊断 Agent 异常: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.exception("[V3.0]诊断失败: %s", e)
        raise HTTPException(status_code=500, detail=f"诊断失败: {e}") from e
    finally:
        session.close()


@router.get("/diagnosis/latest", response_model=DiagnosisResponse)
async def get_latest_diagnosis_v3(
    business_id: Optional[str] = None,
) -> DiagnosisResponse:
    """[V3.0] 获取最新诊断报告（无路径参数版）。

    若传入 business_id 则返回该企业最新诊断，否则返回全表最新一条。

    Parameters
    ----------
    business_id : Optional[str]
        企业ID（可选查询参数）。

    Returns
    -------
    DiagnosisResponse
        最新诊断报告数据。

    Raises
    ------
    HTTPException
        - 404: 尚未生成诊断报告。
    """
    session = SyncSession()
    try:
        query = session.query(DiagnosisRecord)
        if business_id:
            query = query.filter_by(business_id=business_id)
        record = query.order_by(DiagnosisRecord.created_at.desc()).first()

        if not record:
            raise HTTPException(status_code=404, detail="尚未生成诊断报告")

        return DiagnosisResponse(
            data={
                "id": record.id,
                "business_id": record.business_id,
                "overall_score": record.overall_score,
                "score_summary": record.score_summary,
                "score_breakdown": record.score_breakdown,
                "top3_problems": record.top3_problems,
                "strategy_summary": record.strategy_summary,
                "this_week_focus": record.this_week_focus,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        )
    finally:
        session.close()


@router.get("/diagnosis/{business_id}", response_model=DiagnosisResponse)
async def get_diagnosis(business_id: str) -> DiagnosisResponse:
    """查看最新诊断报告。

    Parameters
    ----------
    business_id : str
        企业唯一标识ID（路径参数）。

    Returns
    -------
    DiagnosisResponse
        该企业最新诊断报告数据。

    Raises
    ------
    HTTPException
        - 404: 尚未生成诊断报告。
    """
    session = SyncSession()
    try:
        record = (
            session.query(DiagnosisRecord)
            .filter_by(business_id=business_id)
            .order_by(DiagnosisRecord.created_at.desc())
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="尚未生成诊断报告")

        return DiagnosisResponse(
            data={
                "id": record.id,
                "business_id": record.business_id,
                "overall_score": record.overall_score,
                "score_summary": record.score_summary,
                "score_breakdown": record.score_breakdown,
                "top3_problems": record.top3_problems,
                "strategy_summary": record.strategy_summary,
                "this_week_focus": record.this_week_focus,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        )
    finally:
        session.close()
