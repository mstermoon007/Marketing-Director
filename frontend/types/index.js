"use strict";
/**
 * 全局类型定义 V3.0
 *
 * 与开发文档7.4节 数据模型定义 严格对齐
 *  - Business：company_name / main_product / monthly_budget 等
 *  - Diagnosis：dimension_scores / overall_comment / top_issues / quarterly_roadmap 等
 *  - SevenDayPlan：week_number / phase_name / focus 等
 *  - Task：三态 status (pending/doing/done)
 *
 */
Object.defineProperty(exports, "__esModule", { value: true });
/*
 * 说明（阶段三重构）：
 *   原第 7 节 `GlobalState`（globalData 的 ID + 对象两级结构）与第 9 节
 *   「兼容旧类型别名」（Problem / LegacySevenDayPlan / Roadmap）已随旧页面一并删除。
 *   全局运行时状态统一由 store/index.ts 的 StoreState 承载，
 *   app.ts 的 globalData 仅保留网络层必需的 apiBase / DEV_API_BASE。
 */
