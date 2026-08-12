"use strict";
/**
 * 全局常量定义，包含阶段、任务状态、行业、预算等配置
 *
 * @file    constants.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ERROR_LEVEL = exports.AGENT_INTENT_COLOR = exports.AGENT_INTENT_LABEL = exports.AGENT_INTENTS = exports.QUARTER_TOTAL_WEEKS = exports.API_CODE = exports.ISSUE_LEVEL_ICON = exports.ISSUE_LEVEL_COLOR = exports.ISSUE_LEVEL_LABEL = exports.ISSUE_LEVEL = exports.WEEK_SCHEDULE_RULES = exports.WEEKDAY_LABELS = exports.MARKETING_CHANNELS = exports.MONTHLY_BUDGETS = exports.PRICE_RANGES = exports.TEAM_SIZES = exports.INDUSTRIES = exports.REVIEW_TYPE_LABEL = exports.REVIEW_TYPES = exports.TASK_STATUS_LABEL = exports.TASK_STATUS = exports.PHASES = void 0;
exports.PHASES = [
    {
        index: 1,
        name: '启动期',
        weeksCover: '1-4',
        keyActions: ['账号基建', '竞品调研', '核心素材库建立', '话术体系建立'],
        successCriteria: '完成3个平台账号搭建，积累20条核心素材',
    },
    {
        index: 2,
        name: '放量期',
        weeksCover: '5-8',
        keyActions: ['规律内容发布', '获取首批有效咨询', '启动转介绍'],
        successCriteria: '每周稳定发布5条内容，获取10+有效咨询',
    },
    {
        index: 3,
        name: '收获+裂变期',
        weeksCover: '9-12',
        keyActions: ['重点追单转化', '设计裂变活动', '复盘成功案例'],
        successCriteria: '转化率提升至20%，完成1次裂变活动',
    },
];
exports.TASK_STATUS = {
    PENDING: 'pending',
    DOING: 'doing',
    DONE: 'done',
};
exports.TASK_STATUS_LABEL = {
    [exports.TASK_STATUS.PENDING]: '未开始',
    [exports.TASK_STATUS.DOING]: '进行中',
    [exports.TASK_STATUS.DONE]: '已完成',
};
exports.REVIEW_TYPES = {
    WEEKLY: 'weekly',
    MONTHLY: 'monthly',
    QUARTERLY: 'quarterly',
};
exports.REVIEW_TYPE_LABEL = {
    [exports.REVIEW_TYPES.WEEKLY]: '周复盘',
    [exports.REVIEW_TYPES.MONTHLY]: '月复盘',
    [exports.REVIEW_TYPES.QUARTERLY]: '季度复盘',
};
exports.INDUSTRIES = [
    '餐饮',
    '零售',
    '教育',
    '美容',
    '服务',
    '制造',
    '医疗',
    '房产',
    '中介',
    '其他',
];
exports.TEAM_SIZES = [
    '1-5人',
    '6-20人',
    '21-50人',
    '51-200人',
    '200人以上',
];
exports.PRICE_RANGES = [
    '0-50元',
    '50-200元',
    '200-1000元',
    '1000-5000元',
    '5000元以上',
];
exports.MONTHLY_BUDGETS = [
    '0-1000元',
    '1000-5000元',
    '5000-10000元',
    '1万-3万元',
    '3万-10万元',
    '10万元以上',
];
exports.MARKETING_CHANNELS = [
    '线下门店',
    '美团外卖',
    '大众点评',
    '小红书',
    '抖音',
    '微信公众号',
    '朋友圈广告',
    '社群运营',
    '线下地推',
    '转介绍',
    '视频号',
    '知乎',
];
exports.WEEKDAY_LABELS = [
    '周日',
    '周一',
    '周二',
    '周三',
    '周四',
    '周五',
    '周六',
];
exports.WEEK_SCHEDULE_RULES = {
    1: { type: '准备日', label: '周一', desc: '本周计划梳理、素材准备' },
    2: { type: '执行日', label: '周二', desc: '核心营销动作' },
    3: { type: '执行日', label: '周三', desc: '核心营销动作' },
    4: { type: '执行日', label: '周四', desc: '核心营销动作' },
    5: { type: '执行日', label: '周五', desc: '核心营销动作' },
    6: { type: '汇总日', label: '周六', desc: '数据整理、周复盘填写' },
    0: { type: '休息日', label: '周日', desc: '休息调整' },
};
exports.ISSUE_LEVEL = {
    HIGH: 'high',
    MEDIUM: 'medium',
    LOW: 'low',
};
exports.ISSUE_LEVEL_LABEL = {
    [exports.ISSUE_LEVEL.HIGH]: '严重',
    [exports.ISSUE_LEVEL.MEDIUM]: '中等',
    [exports.ISSUE_LEVEL.LOW]: '轻微',
};
exports.ISSUE_LEVEL_COLOR = {
    [exports.ISSUE_LEVEL.HIGH]: '#ee0a24',
    [exports.ISSUE_LEVEL.MEDIUM]: '#ff976a',
    [exports.ISSUE_LEVEL.LOW]: '#07c160',
};
exports.ISSUE_LEVEL_ICON = {
    [exports.ISSUE_LEVEL.HIGH]: '🔴',
    [exports.ISSUE_LEVEL.MEDIUM]: '🟡',
    [exports.ISSUE_LEVEL.LOW]: '🟢',
};
exports.API_CODE = {
    SUCCESS: 0,
    PARAM_ERROR: 1001,
    NOT_LOGIN: 1002,
    NO_PERMISSION: 1003,
    DIAGNOSIS_PROCESSING: 2001,
    DIAGNOSIS_FAILED: 2002,
    SERVER_ERROR: 5000,
};
exports.QUARTER_TOTAL_WEEKS = 12;
// ============================================================
// ===== Agent 意图 / 流式事件（阶段三：Agent 原生交互） =====
// ============================================================
/** Agent 意图枚举（与后端 src/agent_core/state.py 对齐） */
exports.AGENT_INTENTS = {
    DIAGNOSE: 'diagnose',
    PLAN: 'plan',
    SCHEDULE: 'schedule',
    REVIEW: 'review',
    CHAT: 'chat',
};
/** 意图 → 中文标签 */
exports.AGENT_INTENT_LABEL = {
    [exports.AGENT_INTENTS.DIAGNOSE]: '诊断',
    [exports.AGENT_INTENTS.PLAN]: '计划',
    [exports.AGENT_INTENTS.SCHEDULE]: '日程',
    [exports.AGENT_INTENTS.REVIEW]: '复盘',
    [exports.AGENT_INTENTS.CHAT]: '咨询',
};
/** 意图 → 强调色 */
exports.AGENT_INTENT_COLOR = {
    [exports.AGENT_INTENTS.DIAGNOSE]: '#5B8DEF',
    [exports.AGENT_INTENTS.PLAN]: '#7C6FF0',
    [exports.AGENT_INTENTS.SCHEDULE]: '#07C160',
    [exports.AGENT_INTENTS.REVIEW]: '#FF9F2E',
    [exports.AGENT_INTENTS.CHAT]: '#9AA7BD',
};
/** 错误分级（前端统一处理） */
exports.ERROR_LEVEL = {
    /** 网络层：断网 / 超时 / 服务端不可达 */
    NETWORK: 'network',
    /** 鉴权：401 / 未登录 */
    AUTH: 'auth',
    /** 业务：后端明确返回的错误（参数/权限/处理失败） */
    BUSINESS: 'business',
    /** 未知 / 解析失败 */
    UNKNOWN: 'unknown',
};
