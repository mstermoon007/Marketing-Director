"use strict";
/**
 * 登录鉴权工具，封装微信小程序登录流程与token管理
 *
 * @file    auth.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.isLoggedIn = isLoggedIn;
exports.hasBusinessInfo = hasBusinessInfo;
exports.hasDiagnosis = hasDiagnosis;
exports.wxLogin = wxLogin;
exports.ensureLogin = ensureLogin;
exports.logout = logout;
exports.handleTokenExpired = handleTokenExpired;
const request_1 = require("../api/request");
const storage_1 = require("./storage");
const index_1 = require("../store/index");
/**
 * 是否已登录（有token）
 *
 * @returns 是否已登录
 */
function isLoggedIn() {
    return storage_1.TokenStorage.exists();
}
/**
 * 是否已完成企业信息填写
 *
 * @returns 是否存在企业信息
 */
function hasBusinessInfo() {
    return !!(0, storage_1.getStorage)(storage_1.STORAGE_KEYS.BUSINESS_ID) || !!(0, storage_1.getStorage)(storage_1.STORAGE_KEYS.BUSINESS_INFO);
}
/**
 * 是否已完成诊断（有诊断结果）
 *
 * @returns 是否存在诊断结果
 */
function hasDiagnosis() {
    return !!(0, storage_1.getStorage)(storage_1.STORAGE_KEYS.DIAGNOSIS_ID) || !!(0, storage_1.getStorage)(storage_1.STORAGE_KEYS.DIAGNOSIS);
}
/**
 * 执行微信登录：wx.login code -> 后端换 token
 * 文档6.3.1接口：POST /api/auth/login
 *
 * @returns 登录结果Promise，包含token、user_id、is_new_user
 * @example
 * ```ts
 * const result = await wxLogin()
 * console.log(result.token)
 * ```
 */
async function wxLogin() {
    return new Promise((resolve, reject) => {
        wx.login({
            async success(res) {
                if (!res.code) {
                    reject(new Error('微信登录失败：未获取code'));
                    return;
                }
                try {
                    const result = await (0, request_1.post)('/auth/login', { code: res.code });
                    if (result === null || result === void 0 ? void 0 : result.token) {
                        storage_1.TokenStorage.set(result.token);
                    }
                    if (result === null || result === void 0 ? void 0 : result.user_id) {
                        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.USER_INFO, { user_id: result.user_id });
                    }
                    // 生产环境配置下发：登录成功后持久化，取代原先的本地加密/硬编码方案
                    if (result === null || result === void 0 ? void 0 : result.api_base_url) {
                        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.API_BASE_URL, result.api_base_url);
                    }
                    resolve(result);
                }
                catch (e) {
                    reject(e);
                }
            },
            fail(err) {
                var _a;
                reject(new Error(`wx.login 调用失败: ${(_a = err.errMsg) !== null && _a !== void 0 ? _a : '未知错误'}`));
            },
        });
    });
}
/**
 * 确保已登录（如果未登录则执行登录）
 * 失败后跳转onboarding页（默认不跳转，可选参数）
 *
 * @param redirectOnFail 失败时是否跳转onboarding页，默认false
 * @returns 登录结果或null（失败时）
 */
async function ensureLogin(redirectOnFail = false) {
    var _a, _b;
    if (isLoggedIn()) {
        return {
            token: storage_1.TokenStorage.get(),
            user_id: (_b = (_a = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.USER_INFO)) === null || _a === void 0 ? void 0 : _a.user_id) !== null && _b !== void 0 ? _b : '',
            is_new_user: false,
        };
    }
    try {
        return await wxLogin();
    }
    catch (_c) {
        if (redirectOnFail) {
            // 用 reLaunch 而非 redirectTo：调用方多为 tabBar 页面，
            // redirectTo 会让页面栈失去 tabBar 上下文，reLaunch 语义更正确
            wx.reLaunch({ url: '/pages/onboarding/index' });
        }
        return null;
    }
}
/**
 * 登出：清除登录态 + 跳转引导页
 *
 * @param redirect 是否跳转引导页，默认true
 */
function logout(redirect = true) {
    storage_1.TokenStorage.clear();
    (0, storage_1.removeStorage)(storage_1.STORAGE_KEYS.USER_INFO);
    // 清空会话态 + 本地业务数据（画像/日程/诊断/计划/复盘/KPI/企业列表），
    // 避免下一位用户从 wx.storage 读到上一位用户的数据（数据隔离最后一道闸）。
    index_1.store.clearAll();
    if (redirect) {
        wx.reLaunch({ url: '/pages/onboarding/index' });
    }
}
/**
 * 处理 Token 过期（HTTP 401 / code=1002）
 * 请求封装中自动调用
 */
function handleTokenExpired() {
    storage_1.TokenStorage.clear();
    const pages = getCurrentPages();
    const current = pages[pages.length - 1];
    if (current && !current.route.includes('onboarding')) {
        wx.showToast({ title: '登录已过期，请重新登录', icon: 'none' });
        setTimeout(() => {
            wx.reLaunch({ url: '/pages/onboarding/index' });
        }, 800);
    }
}
