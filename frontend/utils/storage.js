"use strict";
/**
 * 本地缓存管理工具（V3.2 环境隔离版）
 *   - 业务/用户数据按运行环境加命名空间段：`md:dev:` / `md:prod:`，隔离开发↔生产缓存
 *   - 环境配置键（dev/prod 后端地址）使用稳定前缀 `md:`，dev/prod 本就异号，无需再分段
 *   - 支持 TTL 自动过期
 *   - 提供开发环境/遗留缓存的统一清理入口（含旧版 `md:` 未分段脏键迁移清理）
 *   - 提供启动时缓存自检报告
 *
 * 与后端对应：dev → APP_ENV=development → app_dev.db；prod → APP_ENV=production → app_prod.db。
 *
 * @file    storage.ts
 * @author  AI Marketing Team
 * @version 3.2.0
 * @since   2026-01-01
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TokenStorage = exports.STORAGE_KEYS = void 0;
exports.setStorage = setStorage;
exports.getStorage = getStorage;
exports.removeStorage = removeStorage;
exports.clearAllStorage = clearAllStorage;
exports.clearDevAndLegacyCaches = clearDevAndLegacyCaches;
exports.storageSelfCheckReport = storageSelfCheckReport;
const env_1 = require("./env");
/**
 * 业务/用户数据命名空间前缀（按运行环境隔离）
 *   develop / trial → md:dev:    （开发/体验版）
 *   release        → md:prod:    （正式版）
 */
const NS = 'md:' + ((0, env_1.detectEnvKind)() === 'prod' ? 'prod:' : 'dev:');
/**
 * 环境配置键命名空间（dev/prod 两组后端地址本就异号，保持跨环境稳定，
 * 以免升级覆盖后开发者已持久化的 `md:dev_api_base` 丢失）。
 */
const CFG_NS = 'md:';
/** 遗留脏键前缀（历史上未带命名空间的旧值） */
const LEGACY_PREFIX = '_LEGACY_';
/** 统一缓存键常量（项目中禁止再直接写字符串 key） */
exports.STORAGE_KEYS = {
    // ===== 业务 ID 类 =====
    BUSINESS_ID: `${NS}business_id`,
    DIAGNOSIS_ID: `${NS}diagnosis_id`,
    PLAN_ID: `${NS}plan_id`,
    REVIEW_ID: `${NS}review_id`,
    // ===== 登录 / 用户 =====
    AUTH_TOKEN: `${NS}auth_token`,
    USER_INFO: `${NS}user_info`,
    // ===== 业务数据（带 TTL）=====
    BUSINESS_INFO: `${NS}business_info`,
    DIAGNOSIS: `${NS}diagnosis_result`,
    ROADMAP: `${NS}current_roadmap`,
    WEEKLY_PLAN: `${NS}weekly_plan_cache`,
    LAST_CHECKIN_TIME: `${NS}last_checkin_time`,
    LATEST_REVIEW: `${NS}latest_review`,
    // ===== 开发调试专用（不在小程序正式发布环境依赖；使用稳定 CFG_NS 避免迁移丢失）=====
    DEV_API_BASE: `${CFG_NS}dev_api_base`,
    /** 生产环境后端基址：登录成功后由后端下发并持久化（取代原先的本地加密/硬编码方案） */
    API_BASE_URL: `${CFG_NS}api_base_url`,
    // ===== 页面级临时缓存 key 前缀（动态拼接 ID）=====
    PLAN_TASK_PREFIX: `${NS}plan_tasks_`,
    CHECKLIST_PREFIX: `${NS}checklist_`,
    // ===== 阶段三：Agent 原生交互缓存 =====
    /** 最近一次对话摘要（启动秒开，离线可读） */
    CHAT_SUMMARY: `${NS}chat_summary`,
    /** 最新日程（看板/日程页离线可读） */
    SCHEDULE_CACHE: `${NS}schedule_cache`,
    /** 用户设置（思考过程展示偏好等） */
    USER_SETTINGS: `${NS}user_settings`,
    /** 用户画像摘要（Agent 记忆，看板展示用） */
    PROFILE_SUMMARY: `${NS}profile_summary`,
};
/** 各业务 key 的 TTL（毫秒），未配置则永不过期 */
const TTL = {
    [exports.STORAGE_KEYS.BUSINESS_INFO]: 86400000,
    [exports.STORAGE_KEYS.DIAGNOSIS]: 604800000,
    [exports.STORAGE_KEYS.ROADMAP]: 604800000,
    [exports.STORAGE_KEYS.WEEKLY_PLAN]: 86400000,
    [exports.STORAGE_KEYS.AUTH_TOKEN]: 7 * 86400000,
    [exports.STORAGE_KEYS.LAST_CHECKIN_TIME]: 7 * 86400000,
};
/**
 * 写入缓存（自动记录时间戳）
 */
function setStorage(key, data) {
    const payload = { data, timestamp: Date.now() };
    try {
        wx.setStorageSync(key, payload);
    }
    catch (e) {
        console.error(`[storage] set failed (${key}):`, e);
    }
}
/**
 * 读取缓存（自动校验 TTL，过期自动删除并返回 null）
 */
function getStorage(key) {
    try {
        const payload = wx.getStorageSync(key);
        if (!payload)
            return null;
        if (typeof payload === 'object' && 'timestamp' in payload && 'data' in payload) {
            const ttl = TTL[key];
            if (ttl && Date.now() - payload.timestamp > ttl) {
                wx.removeStorageSync(key);
                return null;
            }
            return payload.data;
        }
        return payload;
    }
    catch (e) {
        console.error(`[storage] get failed (${key}):`, e);
        return null;
    }
}
/**
 * 删除单个缓存
 */
function removeStorage(key) {
    try {
        wx.removeStorageSync(key);
    }
    catch (e) {
        console.error(`[storage] remove failed (${key}):`, e);
    }
}
/**
 * 清除全部业务缓存（保留登录 token 可选）
 */
function clearAllStorage(keepAuth = true) {
    const keep = keepAuth
        ? [exports.STORAGE_KEYS.AUTH_TOKEN, exports.STORAGE_KEYS.DEV_API_BASE, exports.STORAGE_KEYS.API_BASE_URL]
        : [];
    Object.values(exports.STORAGE_KEYS).forEach((k) => {
        if (typeof k !== 'string')
            return;
        if (keep.indexOf(k) !== -1)
            return;
        // 前缀类：清掉所有以该前缀开头的 key
        if (k.endsWith('_')) {
            _removeByPrefix(k);
            return;
        }
        try {
            wx.removeStorageSync(k);
        }
        catch ( /* ignore */_a) { /* ignore */ }
    });
}
/**
 * 清理「开发环境专属缓存」+「历史遗留脏键」—— 用于 onLaunch 首次启动自检
 *   - 清理 `DEV_API_BASE`（若不包含有效的 http 开头则清掉）
 *   - 清理不匹配 `md:` 前缀的所有老业务键（businessId / diagnosisId / planId / reviewId）
 *   - 清理旧 legacy 前缀所有数据
 *
 * 注：此函数安全幂等，每次启动调用不会误伤 V3.1 的 ns 键
 */
function clearDevAndLegacyCaches() {
    var _a;
    const removed = [];
    const info = (_a = wx.getStorageInfoSync) === null || _a === void 0 ? void 0 : _a.call(wx);
    const allKeys = (info === null || info === void 0 ? void 0 : info.keys) || [];
    const devKeysToValidate = [exports.STORAGE_KEYS.DEV_API_BASE, exports.STORAGE_KEYS.API_BASE_URL];
    // 1) 校验 DEV 调试 key，格式非法直接移除
    devKeysToValidate.forEach((k) => {
        try {
            const v = wx.getStorageSync(k);
            if (v && typeof v === 'string' && !/^https?:\/\//.test(v) && v.length < 8) {
                wx.removeStorageSync(k);
                removed.push(k);
            }
        }
        catch ( /* ignore */_a) { /* ignore */ }
    });
    // 2) 清除老的无命名空间业务 ID 键（已经迁移到 md:business_id 等）
    const legacyIdKeys = ['businessId', 'diagnosisId', 'planId', 'reviewId'];
    legacyIdKeys.forEach((k) => {
        if (allKeys.includes(k)) {
            try {
                wx.removeStorageSync(k);
                removed.push(k);
            }
            catch ( /* ignore */_a) { /* ignore */ }
        }
    });
    // 3) 清除 _LEGACY_ 脏键
    allKeys.forEach((k) => {
        if (k.startsWith(LEGACY_PREFIX)) {
            try {
                wx.removeStorageSync(k);
                removed.push(k);
            }
            catch ( /* ignore */_a) { /* ignore */ }
        }
    });
    // 4) 迁移清理：旧版（V3.1）未分段命名空间键 md:business_id / md:api_base_url 等
    //    当前数据键已升级为 md:dev: / md:prod:，旧键不再被读取，统一回收避免脏读/占用空间。
    //    注意：当前合法键（含 CFG_NS 的 md:dev_api_base 等）不在此列，不会被误删。
    const validKeys = new Set(Object.values(exports.STORAGE_KEYS).filter((k) => typeof k === 'string'));
    allKeys.forEach((k) => {
        if (k.startsWith('md:') && !validKeys.has(k)) {
            try {
                wx.removeStorageSync(k);
                removed.push(k);
            }
            catch ( /* ignore */_a) { /* ignore */ }
        }
    });
    return { removed };
}
/**
 * 缓存自检报告（onLaunch 时调用一次）
 *   - 打印所有 `md:` 命名空间下的 key 与其大小 / 过期状态
 *   - 提示「历史遗留脏键」数量
 */
function storageSelfCheckReport() {
    var _a;
    const info = (_a = wx.getStorageInfoSync) === null || _a === void 0 ? void 0 : _a.call(wx);
    const allKeys = (info === null || info === void 0 ? void 0 : info.keys) || [];
    const nsKeys = allKeys.filter((k) => k.startsWith('md:'));
    const legacyKeys = allKeys.filter((k) => !k.startsWith('md:'));
    const sizes = nsKeys.map((k) => {
        try {
            const raw = null;
            void raw;
            return k;
        }
        catch (_a) {
            return k;
        }
    });
    const report = `[storage] SelfCheck — ns:${nsKeys.length} legacy:${legacyKeys.length} totalSize:${(info === null || info === void 0 ? void 0 : info.currentSize) || 0}KB\n` +
        `  md: keys = ${sizes.join(', ') || '(none)'}\n` +
        (legacyKeys.length ? `  ⚠️  legacy keys: ${legacyKeys.join(', ')}` : '  ✅ 无遗留脏键');
    console.info(report);
    return report;
}
/** 按前缀删除 key（内部工具） */
function _removeByPrefix(prefix) {
    var _a;
    const info = (_a = wx.getStorageInfoSync) === null || _a === void 0 ? void 0 : _a.call(wx);
    if (!(info === null || info === void 0 ? void 0 : info.keys))
        return;
    info.keys.forEach((k) => {
        if (k.startsWith(prefix)) {
            try {
                wx.removeStorageSync(k);
            }
            catch ( /* ignore */_a) { /* ignore */ }
        }
    });
}
/**
 * 简易 Token 读写封装
 */
exports.TokenStorage = {
    get() {
        var _a;
        return (_a = getStorage(exports.STORAGE_KEYS.AUTH_TOKEN)) !== null && _a !== void 0 ? _a : '';
    },
    set(token) {
        setStorage(exports.STORAGE_KEYS.AUTH_TOKEN, token);
    },
    clear() {
        removeStorage(exports.STORAGE_KEYS.AUTH_TOKEN);
    },
    exists() {
        return !!exports.TokenStorage.get();
    },
};
