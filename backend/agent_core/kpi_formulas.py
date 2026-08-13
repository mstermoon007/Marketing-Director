"""
零售门店 KPI 公式工具箱（离线，无大模型依赖）
============================================

把 ``/Users/zhanggaozhang/TRAE-CN/SKILL-/SKILL-03.md`` 的 19 个门店核心经营指标
落地为「公式注册表 + 基准诊断」纯函数，供 ``calculate_kpi`` 在**不靠大模型**的前提下
计算零售效率指标并给出健康区间判断。

指标名（inputs 键）沿用 SKILL-03 的中文口径，与用户上传 CSV 的列名一致：
营业额、业绩指标、同期营业额、当期营业额、店铺面积、总人数、客单数、销售件数、
VIP消费额、无条码件数、丢失货品金额、销售金额、实际上岗人数、定编人数、
岗位集体业绩、期初库存量、期末库存量、进货金额、分类销售额、折让金额、吊牌金额。
"""

from __future__ import annotations

from typing import Callable, Optional


def _div(a: float, b: float) -> Optional[float]:
    try:
        return a / b if b else None
    except (TypeError, ZeroDivisionError):
        return None


# 每条公式：key(稳定id) / name / formula_str / inputs(必须在 numbers 中存在的键)
#          / compute(inputs)->float|None / benchmark(value)->(level, diagnosis, advice) / category
RETAIL_KPI_FORMULAS: list[dict] = [
    {
        "key": "达标率", "name": "达标率", "category": "业绩达成",
        "formula_str": "营业额 / 业绩指标 × 100%",
        "inputs": ["营业额", "业绩指标"],
        "compute": lambda v: _div(v["营业额"], v["业绩指标"]) * 100,
        "benchmark": lambda x: (
            "达标" if x >= 100 else "未达标",
            f"达标率 {x:.0f}%，{'已完成' if x >= 100 else '未完成'}业绩指标。",
            "未达标时回溯缺口，拆解到每日动作补齐。" if x < 100 else "保持节奏并适度加量。",
        ),
    },
    {
        "key": "同期业绩增长率", "name": "同期业绩增长率", "category": "业绩趋势",
        "formula_str": "(同期营业额 - 当期营业额) / 同期营业额 × 100%",
        "inputs": ["同期营业额", "当期营业额"],
        "compute": lambda v: _div(v["当期营业额"] - v["同期营业额"], v["同期营业额"]) * 100,
        "benchmark": lambda x: (
            "上升" if x >= 0 else "下滑",
            f"同比增长 {x:+.0f}%。",
            "上升则乘势加力；下滑需复盘回落原因并调整获客动作。" if x < 0 else "保持增长动能。",
        ),
    },
    {
        "key": "坪效", "name": "坪效", "category": "空间效率",
        "formula_str": "营业额 / 店铺面积",
        "inputs": ["营业额", "店铺面积"],
        "compute": lambda v: _div(v["营业额"], v["店铺面积"]),
        "benchmark": lambda x: (
            "—", f"坪效 {x:.1f}（营业额/面积）。", "提升陈列与动线，提高单位面积产出。",
        ),
    },
    {
        "key": "人效", "name": "人效", "category": "人员效率",
        "formula_str": "营业额 / 总人数",
        "inputs": ["营业额", "总人数"],
        "compute": lambda v: _div(v["营业额"], v["总人数"]),
        "benchmark": lambda x: (
            "—", f"人效 {x:.1f}（营业额/人数）。", "优化排班与培训，提升人均产出。",
        ),
    },
    {
        "key": "ATV", "name": "ATV(平均交易价值)", "category": "人员效率",
        "formula_str": "营业额 / 客单数",
        "inputs": ["营业额", "客单数"],
        "compute": lambda v: _div(v["营业额"], v["客单数"]),
        "benchmark": lambda x: (
            "—", f"ATV {x:.1f}（营业额/客单数）。", "提升附加销售与货品组合，拉高客单。",
        ),
    },
    {
        "key": "连带率", "name": "连带销售率", "category": "人员效率",
        "formula_str": "销售件数 / 客单数",
        "inputs": ["销售件数", "客单数"],
        "compute": lambda v: _div(v["销售件数"], v["客单数"]),
        "benchmark": lambda x: (
            "偏高" if x >= 2 else "偏低",
            f"连带率 {x:.2f} 双/单。",
            "加强搭配推荐，目标 ≥2。" if x < 2 else "保持附加推销能力。",
        ),
    },
    {
        "key": "ASP", "name": "ASP(平均销售单价)", "category": "人员效率",
        "formula_str": "营业额 / 销售件数",
        "inputs": ["营业额", "销售件数"],
        "compute": lambda v: _div(v["营业额"], v["销售件数"]),
        "benchmark": lambda x: (
            "—", f"ASP {x:.1f}（营业额/件数）。", "结合 ATV 分析顾客消费承受力与货品定价。",
        ),
    },
    {
        "key": "VIP占比", "name": "VIP占比", "category": "顾客运营",
        "formula_str": "VIP消费额 / 营业额",
        "inputs": ["VIP消费额", "营业额"],
        "compute": lambda v: _div(v["VIP消费额"], v["营业额"]) * 100,
        "benchmark": lambda x: (
            "健康" if 45 <= x <= 55 else ("偏低" if x < 45 else "偏高"),
            f"VIP占比 {x:.0f}%。",
            "45%-55% 为健康区间。" + (
                "低于45%：顾客流失或开发弱，需强化新客。"
                if x < 45 else "高于55%：新客开发太弱，需拓新。"
                if x > 55 else "利益最大化，业绩稳定。"
            ),
        ),
    },
    {
        "key": "无条码率", "name": "无条码率", "category": "商品管理",
        "formula_str": "无条码件数 / 销售件数 × 100%",
        "inputs": ["无条码件数", "销售件数"],
        "compute": lambda v: _div(v["无条码件数"], v["销售件数"]) * 100,
        "benchmark": lambda x: (
            "偏高" if x > 2 else "正常",
            f"无条码率 {x:.1f}%。",
            "偏高需加强吊牌管理（行业关注 <2.5%）。" if x > 2 else "吊牌管理良好。",
        ),
    },
    {
        "key": "丢失率", "name": "丢失率", "category": "损耗控制",
        "formula_str": "丢失货品金额 / 销售金额 × 100%",
        "inputs": ["丢失货品金额", "销售金额"],
        "compute": lambda v: _div(v["丢失货品金额"], v["销售金额"]) * 100,
        "benchmark": lambda x: (
            "偏高" if x > 0.6 else "正常",
            f"丢失率 {x:.1f}%（行业约0.6%）。",
            "偏高需加强防盗与排班。" if x > 0.6 else "防盗能力良好。",
        ),
    },
    {
        "key": "岗位完成率", "name": "岗位完成率", "category": "人力资源",
        "formula_str": "实际上岗人数 / 定编人数 × 100%",
        "inputs": ["实际上岗人数", "定编人数"],
        "compute": lambda v: _div(v["实际上岗人数"], v["定编人数"]) * 100,
        "benchmark": lambda x: (
            "缺编" if x < 90 else "满编",
            f"岗位完成率 {x:.0f}%。",
            "缺编时补齐编制或调整排班。" if x < 90 else "编制满足。",
        ),
    },
    {
        "key": "岗位贡献率", "name": "岗位贡献率", "category": "人力资源",
        "formula_str": "岗位集体业绩 / 营业额 × 100%",
        "inputs": ["岗位集体业绩", "营业额"],
        "compute": lambda v: _div(v["岗位集体业绩"], v["营业额"]) * 100,
        "benchmark": lambda x: (
            "—", f"岗位贡献率 {x:.0f}%。", "反映该岗位实际技能水平与产出占比。",
        ),
    },
    {
        "key": "库存周转比", "name": "库存周转比", "category": "商品管理",
        "formula_str": "月营业额 / ((期初库存量 + 期末库存量) / 2)",
        "inputs": ["营业额", "期初库存量", "期末库存量"],
        "compute": lambda v: _div(v["营业额"], (v["期初库存量"] + v["期末库存量"]) / 2),
        "benchmark": lambda x: (
            "—", f"库存周转比 {x:.2f}。", "反映货品流动速度，周转越高越畅销。",
        ),
    },
    {
        "key": "进销比", "name": "进销比", "category": "商品管理",
        "formula_str": "进货金额 / 销售金额",
        "inputs": ["进货金额", "销售金额"],
        "compute": lambda v: _div(v["进货金额"], v["销售金额"]),
        "benchmark": lambda x: (
            "合理" if 0.8 <= x <= 1.2 else ("偏低" if x < 0.8 else "偏高"),
            f"进销比 {x:.2f}（理论理想值=1）。",
            "库存大时适当<1，库存小时适当>1。" if 0.8 <= x <= 1.2 else (
                "偏低：库存偏小，注意补货。" if x < 0.8 else "偏高：库存积压，控进货。"
            ),
        ),
    },
    {
        "key": "分类货品销售占比", "name": "分类货品销售占比", "category": "商品管理",
        "formula_str": "分类销售额 / 营业额 × 100%",
        "inputs": ["分类销售额", "营业额"],
        "compute": lambda v: _div(v["分类销售额"], v["营业额"]) * 100,
        "benchmark": lambda x: (
            "—", f"分类销售占比 {x:.0f}%。", "用于要货/组货与促销判断，对比区域消费取向。",
        ),
    },
    {
        "key": "折扣率", "name": "折扣率", "category": "利润分析",
        "formula_str": "折让金额 / 吊牌金额 × 100%",
        "inputs": ["折让金额", "吊牌金额"],
        "compute": lambda v: _div(v["折让金额"], v["吊牌金额"]) * 100,
        "benchmark": lambda x: (
            "偏高" if x > 15 else "正常",
            f"折扣率 {x:.0f}%。",
            "营业额高但折扣率也高说明在做促销、毛利低，与推广占比共评。" if x > 15 else "毛利控制良好。",
        ),
    },
]


def calculate_retail_kpis(numbers: dict) -> list[dict]:
    """根据传入的指标，计算所有可算的零售 KPI 并附基准诊断。

    Parameters
    ----------
    numbers : dict
        实际数据（键为 SKILL-03 中文指标名，如 {"营业额": 8000, "店铺面积": 100}）。

    Returns
    -------
    list[dict]：每项 {key, name, value, formula, category, benchmark_level,
                  diagnosis, advice}；输入不全的公式自动跳过。
    """
    numbers = numbers or {}
    results: list[dict] = []
    for f in RETAIL_KPI_FORMULAS:
        try:
            if not all(k in numbers and numbers[k] not in (None, "") for k in f["inputs"]):
                continue
            vals = {k: float(numbers[k]) for k in f["inputs"]}
            value = f["compute"](vals)
            if value is None:
                continue
            level, diagnosis, advice = f["benchmark"](value)
            results.append({
                "key": f["key"],
                "name": f["name"],
                "value": round(value, 2),
                "formula": f["formula_str"],
                "category": f["category"],
                "benchmark_level": level,
                "diagnosis": diagnosis,
                "advice": advice,
            })
        except (TypeError, ValueError, ZeroDivisionError, KeyError):
            continue
    return results
