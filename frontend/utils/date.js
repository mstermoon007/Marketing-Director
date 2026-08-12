"use strict";
/**
 * 日期处理工具函数集，含格式化、阶段计算、相对时间等
 *
 * @file    date.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.WEEKDAY_LABELS = exports.QUARTER_TOTAL_WEEKS = exports.PHASES = void 0;
exports.formatDate = formatDate;
exports.formatShortDate = formatShortDate;
exports.getWeekdayLabel = getWeekdayLabel;
exports.getWeekdayIndex = getWeekdayIndex;
exports.weekToPhaseIndex = weekToPhaseIndex;
exports.weekToPhase = weekToPhase;
exports.calculateCurrentWeek = calculateCurrentWeek;
exports.calculateQuarterProgress = calculateQuarterProgress;
exports.generateWeekDates = generateWeekDates;
exports.formatRelativeTime = formatRelativeTime;
exports.formatTimeSlot = formatTimeSlot;
exports.isToday = isToday;
const constants_1 = require("./constants");
Object.defineProperty(exports, "PHASES", { enumerable: true, get: function () { return constants_1.PHASES; } });
Object.defineProperty(exports, "QUARTER_TOTAL_WEEKS", { enumerable: true, get: function () { return constants_1.QUARTER_TOTAL_WEEKS; } });
Object.defineProperty(exports, "WEEKDAY_LABELS", { enumerable: true, get: function () { return constants_1.WEEKDAY_LABELS; } });
/**
 * 格式化日期为 YYYY-MM-DD
 *
 * @param date 日期对象、字符串或时间戳
 * @param sep 分隔符，默认'-'
 * @returns 格式化后的日期字符串，无效日期返回空串
 */
function formatDate(date, sep = '-') {
    const d = new Date(date);
    if (isNaN(d.getTime()))
        return '';
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}${sep}${m}${sep}${day}`;
}
/**
 * 格式化日期为 M月D日（用于任务显示）
 *
 * @param date 日期对象、字符串或时间戳
 * @returns 如"1月15日"，无效日期返回空串
 */
function formatShortDate(date) {
    const d = new Date(date);
    if (isNaN(d.getTime()))
        return '';
    return `${d.getMonth() + 1}月${d.getDate()}日`;
}
/**
 * 获取星期几标签（周日~周六）
 *
 * @param date 日期对象、字符串或时间戳
 * @returns 星期标签，无效日期返回空串
 */
function getWeekdayLabel(date) {
    const d = new Date(date);
    if (isNaN(d.getTime()))
        return '';
    return constants_1.WEEKDAY_LABELS[d.getDay()];
}
/**
 * 获取星期几的index（0=周日，1=周一...）
 *
 * @param date 日期对象、字符串或时间戳
 * @returns 星期索引 0-6
 */
function getWeekdayIndex(date) {
    const d = new Date(date);
    return d.getDay();
}
/**
 * 根据周序号（1-12）判断属于哪个阶段
 *
 * @param weekNumber 周序号 1-12
 * @returns 阶段index 1|2|3
 */
function weekToPhaseIndex(weekNumber) {
    if (weekNumber <= 4)
        return 1;
    if (weekNumber <= 8)
        return 2;
    return 3;
}
/**
 * 根据周序号获取Phase对象
 *
 * @param weekNumber 周序号 1-12
 * @returns Phase对象
 */
function weekToPhase(weekNumber) {
    var _a;
    const idx = weekToPhaseIndex(weekNumber);
    return (_a = constants_1.PHASES.find((p) => p.index === idx)) !== null && _a !== void 0 ? _a : constants_1.PHASES[0];
}
/**
 * 计算当前处于第几周（基于起始日期）
 *
 * @param startDateStr 诊断/计划开始日期 YYYY-MM-DD
 * @param todayStr 今天日期 YYYY-MM-DD，默认今天
 * @returns 当前周数 1-12
 */
function calculateCurrentWeek(startDateStr, todayStr) {
    if (!startDateStr)
        return 1;
    const start = new Date(startDateStr);
    const today = todayStr ? new Date(todayStr) : new Date();
    if (isNaN(start.getTime()))
        return 1;
    start.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    const diffDays = Math.floor((today.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    const week = Math.floor(diffDays / 7) + 1;
    return Math.max(1, Math.min(constants_1.QUARTER_TOTAL_WEEKS, week));
}
/**
 * 计算季度进度百分比
 *
 * @param currentWeek 当前周数
 * @returns 进度百分比 0-100
 */
function calculateQuarterProgress(currentWeek) {
    return Math.min(100, Math.round((Math.min(currentWeek, constants_1.QUARTER_TOTAL_WEEKS) / constants_1.QUARTER_TOTAL_WEEKS) * 100));
}
/**
 * 生成7天日期数组（从指定起始日开始的一周）
 *
 * @param startDateStr YYYY-MM-DD，默认今天所在周的周一
 * @returns 一周7天的日期信息数组
 */
function generateWeekDates(startDateStr) {
    let base;
    if (startDateStr) {
        base = new Date(startDateStr);
    }
    else {
        const now = new Date();
        const day = now.getDay();
        const diffToMonday = day === 0 ? -6 : 1 - day;
        base = new Date(now);
        base.setDate(now.getDate() + diffToMonday);
    }
    if (isNaN(base.getTime()))
        base = new Date();
    const todayStr = formatDate(new Date());
    const result = [];
    for (let i = 0; i < 7; i++) {
        const d = new Date(base);
        d.setDate(base.getDate() + i);
        const dateStr = formatDate(d);
        result.push({
            date: dateStr,
            weekday: getWeekdayLabel(d),
            weekdayIdx: d.getDay(),
            isToday: dateStr === todayStr,
        });
    }
    return result;
}
/**
 * 时间字符串转友好显示
 *
 * @param isoStr ISO 格式时间
 * @returns 相对时间字符串，如"刚刚"、"5分钟前"、"2天前"
 */
function formatRelativeTime(isoStr) {
    if (!isoStr)
        return '';
    const d = new Date(isoStr);
    if (isNaN(d.getTime()))
        return '';
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / (1000 * 60));
    if (diffMin < 1)
        return '刚刚';
    if (diffMin < 60)
        return `${diffMin}分钟前`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24)
        return `${diffHour}小时前`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 30)
        return `${diffDay}天前`;
    return formatDate(d, '/');
}
/**
 * 将 "09:00-09:30" 时间段格式化为友好显示
 *
 * @param slot 时间段字符串
 * @returns 去除空格后的时间段
 */
function formatTimeSlot(slot) {
    if (!slot)
        return '';
    return slot.replace(/ /g, '');
}
/**
 * 判断给定日期是否为今天
 *
 * @param dateStr 日期字符串 YYYY-MM-DD
 * @returns 是否为今天
 */
function isToday(dateStr) {
    return formatDate(dateStr) === formatDate(new Date());
}
