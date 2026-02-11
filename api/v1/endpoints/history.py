# -*- coding: utf-8 -*-
"""
===================================
历史记录接口
===================================

职责：
1. 提供 GET /api/v1/history 历史列表查询接口
2. 提供 GET /api/v1/history/{query_id} 历史详情查询接口
"""

import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends

from api.deps import get_database_manager
from api.v1.schemas.history import (
    HistoryListResponse,
    HistoryItem,
    NewsIntelItem,
    NewsIntelResponse,
    AnalysisReport,
    ReportMeta,
    ReportSummary,
    ReportStrategy,
    ReportDetails,
)
from api.v1.schemas.common import ErrorResponse
from src.storage import DatabaseManager
from src.services.history_service import HistoryService

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_numeric(value: Any) -> Optional[float]:
    """Parse a numeric value that may contain Chinese unit suffixes like '万股', '亿元', '%'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    # Remove trailing units/suffixes
    text = text.replace(',', '').replace('，', '')
    # Handle percentage: '2.15%' -> 2.15
    if text.endswith('%'):
        try:
            return float(text[:-1])
        except ValueError:
            return None
    # Handle '亿' multiplier
    for suffix in ['亿元', '亿股', '亿']:
        if suffix in text:
            try:
                return float(text.split(suffix)[0].strip()) * 1e8
            except ValueError:
                return None
    # Handle '万' multiplier
    for suffix in ['万股', '万元', '万手', '万']:
        if suffix in text:
            try:
                return float(text.split(suffix)[0].strip()) * 1e4
            except ValueError:
                return None
    # Remove other trailing non-numeric chars (元, 股, etc.)
    import re
    match = re.match(r'^([+-]?\d+(?:\.\d+)?)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _extract_market_data(context_snapshot: Any, raw_result: Any = None) -> Dict[str, Any]:
    """
    Extract market data from context_snapshot and/or raw_result.

    Tries multiple sources in order:
    1. raw_result.current_price / change_pct / market_snapshot (most reliable)
    2. context_snapshot.enhanced_context.realtime
    3. context_snapshot.realtime_quote_raw
    """
    data: Dict[str, Any] = {}

    # --- Source 1: raw_result (contains AnalysisResult.to_dict()) ---
    raw = raw_result
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raw = None
    if isinstance(raw, dict):
        if raw.get("current_price") is not None:
            data["current_price"] = raw["current_price"]
        if raw.get("change_pct") is not None:
            data["change_pct"] = raw["change_pct"]
        # market_snapshot has OHLCV
        ms = raw.get("market_snapshot") or {}
        if isinstance(ms, dict):
            for src_key, dst_key in [("open", "open_price"), ("high", "high_price"), ("low", "low_price"),
                                      ("prev_close", "prev_close"), ("volume", "volume"), ("amount", "amount"),
                                      ("amplitude", "amplitude"), ("turnover_rate", "turnover_rate"),
                                      ("volume_ratio", "volume_ratio")]:
                if ms.get(src_key) is not None:
                    data.setdefault(dst_key, ms[src_key])

    # --- Source 2: context_snapshot ---
    snapshot = context_snapshot
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except (json.JSONDecodeError, TypeError):
            snapshot = None

    if isinstance(snapshot, dict):
        enhanced_context = snapshot.get("enhanced_context") or {}
        realtime = enhanced_context.get("realtime") or {}

        data.setdefault("current_price", realtime.get("price"))
        data.setdefault("change_pct", realtime.get("change_pct") or realtime.get("change_60d"))
        data.setdefault("turnover_rate", realtime.get("turnover_rate"))
        data.setdefault("volume_ratio", realtime.get("volume_ratio"))

        # Fallback: realtime_quote_raw
        realtime_quote_raw = snapshot.get("realtime_quote_raw") or {}
        data.setdefault("current_price", realtime_quote_raw.get("price"))
        data.setdefault("change_pct", realtime_quote_raw.get("change_pct") or realtime_quote_raw.get("pct_chg"))

        # OHLCV from daily_data or realtime_quote_raw
        daily_data = enhanced_context.get("daily_data") or {}
        for src_key, dst_key in [("open", "open_price"), ("high", "high_price"), ("low", "low_price"),
                                  ("prev_close", "prev_close"), ("volume", "volume"), ("amount", "amount"),
                                  ("amplitude", "amplitude"), ("turnover_rate", "turnover_rate"),
                                  ("volume_ratio", "volume_ratio")]:
            if isinstance(daily_data, dict):
                data.setdefault(dst_key, daily_data.get(src_key))
            data.setdefault(dst_key, realtime_quote_raw.get(src_key))

    # Sanitize: parse all values to float (handles '2528.18 万股' etc.)
    return {k: v for k, v in ((k, _parse_numeric(v)) for k, v in data.items()) if v is not None}


@router.get(
    "",
    response_model=HistoryListResponse,
    responses={
        200: {"description": "历史记录列表"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取历史分析列表",
    description="分页获取历史分析记录摘要，支持按股票代码和日期范围筛选"
)
def get_history_list(
    stock_code: Optional[str] = Query(None, description="股票代码筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> HistoryListResponse:
    """
    获取历史分析列表
    
    分页获取历史分析记录摘要，支持按股票代码和日期范围筛选
    
    Args:
        stock_code: 股票代码筛选
        start_date: 开始日期
        end_date: 结束日期
        page: 页码
        limit: 每页数量
        db_manager: 数据库管理器依赖
        
    Returns:
        HistoryListResponse: 历史记录列表
    """
    try:
        service = HistoryService(db_manager)
        
        # 使用 def 而非 async def，FastAPI 自动在线程池中执行
        result = service.get_history_list(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit
        )
        
        # 转换为响应模型
        items = [
            HistoryItem(
                query_id=item.get("query_id", ""),
                stock_code=item.get("stock_code", ""),
                stock_name=item.get("stock_name"),
                report_type=item.get("report_type"),
                sentiment_score=item.get("sentiment_score"),
                operation_advice=item.get("operation_advice"),
                created_at=item.get("created_at")
            )
            for item in result.get("items", [])
        ]
        
        return HistoryListResponse(
            total=result.get("total", 0),
            page=page,
            limit=limit,
            items=items
        )
        
    except Exception as e:
        logger.error(f"查询历史列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"查询历史列表失败: {str(e)}"
            }
        )


@router.get(
    "/{query_id}",
    response_model=AnalysisReport,
    responses={
        200: {"description": "报告详情"},
        404: {"description": "报告不存在", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取历史报告详情",
    description="根据 query_id 获取完整的历史分析报告"
)
def get_history_detail(
    query_id: str,
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> AnalysisReport:
    """
    获取历史报告详情
    
    根据 query_id 获取完整的历史分析报告
    
    Args:
        query_id: 分析记录唯一标识
        db_manager: 数据库管理器依赖
        
    Returns:
        AnalysisReport: 完整分析报告
        
    Raises:
        HTTPException: 404 - 报告不存在
    """
    try:
        service = HistoryService(db_manager)
        
        # 使用 def 而非 async def，FastAPI 自动在线程池中执行
        result = service.get_history_detail(query_id)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"未找到 query_id={query_id} 的分析记录"
                }
            )
        
        # 从 context_snapshot 和 raw_result 中提取价格和行情信息
        market_data = _extract_market_data(
            result.get("context_snapshot"),
            raw_result=result.get("raw_result")
        )

        # 构建响应模型
        meta = ReportMeta(
            query_id=result.get("query_id", query_id),
            stock_code=result.get("stock_code", ""),
            stock_name=result.get("stock_name"),
            report_type=result.get("report_type"),
            created_at=result.get("created_at"),
            current_price=market_data.get("current_price"),
            change_pct=market_data.get("change_pct"),
            open_price=market_data.get("open_price"),
            high_price=market_data.get("high_price"),
            low_price=market_data.get("low_price"),
            prev_close=market_data.get("prev_close"),
            volume=market_data.get("volume"),
            amount=market_data.get("amount"),
            turnover_rate=market_data.get("turnover_rate"),
            volume_ratio=market_data.get("volume_ratio"),
            amplitude=market_data.get("amplitude"),
        )
        
        summary = ReportSummary(
            analysis_summary=result.get("analysis_summary"),
            operation_advice=result.get("operation_advice"),
            trend_prediction=result.get("trend_prediction"),
            sentiment_score=result.get("sentiment_score"),
            sentiment_label=result.get("sentiment_label")
        )
        
        strategy = ReportStrategy(
            ideal_buy=result.get("ideal_buy"),
            secondary_buy=result.get("secondary_buy"),
            stop_loss=result.get("stop_loss"),
            take_profit=result.get("take_profit")
        )
        
        details = ReportDetails(
            news_content=result.get("news_content"),
            raw_result=result.get("raw_result"),
            context_snapshot=result.get("context_snapshot")
        )
        
        return AnalysisReport(
            meta=meta,
            summary=summary,
            strategy=strategy,
            details=details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询历史详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"查询历史详情失败: {str(e)}"
            }
        )


@router.get(
    "/{query_id}/news",
    response_model=NewsIntelResponse,
    responses={
        200: {"description": "新闻情报列表"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取历史报告关联新闻",
    description="根据 query_id 获取关联的新闻情报列表（为空也返回 200）"
)
def get_history_news(
    query_id: str,
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> NewsIntelResponse:
    """
    获取历史报告关联新闻

    Args:
        query_id: 分析记录唯一标识
        limit: 返回数量限制
        db_manager: 数据库管理器依赖

    Returns:
        NewsIntelResponse: 新闻情报列表
    """
    try:
        service = HistoryService(db_manager)
        items = service.get_news_intel(query_id=query_id, limit=limit)

        response_items = [
            NewsIntelItem(
                title=item.get("title", ""),
                snippet=item.get("snippet"),
                url=item.get("url", "")
            )
            for item in items
        ]

        return NewsIntelResponse(
            total=len(response_items),
            items=response_items
        )

    except Exception as e:
        logger.error(f"查询新闻情报失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"查询新闻情报失败: {str(e)}"
            }
        )
