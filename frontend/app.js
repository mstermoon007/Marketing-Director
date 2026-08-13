"use strict";
/**
 * 应用入口（阶段三：Agent 原生交互重构版）
 *
 * 与旧版（V3.1）的关键差异：
 *   ❌ 移除 legacy key 迁移逻辑（businessId / diagnosisId … 无命名空间旧键）
 *   ❌ 移除启动期导航锁 safeNavigate / _launching / _navLock
 *      —— 新架构首页 pages[0] 即「一键登录」页（onboarding）：未登录先走登录，
 *         已登录由 onboarding.onLoad 直接 switchTab 到 tabBar 的「对话」页；全程仅
 *         switchTab，不再发生 reLaunch/redirectTo，天然不存在
 *         「appLaunch with non-empty page stack」竞态
 *   ❌ 移除散落在 globalData 的业务对象（diagnosisResult / weeklyPlan / latestReview …）
 *      —— 统一收敛到 store/index.ts 单一可信源
 *   ✅ onLaunch 同步 store.loadCache()：从 wx.storage 秒开恢复对话摘要 / 日程 / 画像 / 设置
 *
 * globalData 仅保留「网络层必需」的最小配置：
 *   apiBase / DEV_API_BASE  —— 供 api/request.ts 的 getBase() 解析 BaseURL
 *   （生产环境基址由登录后后端下发并持久化，不再在此注入任何密钥/种子）
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("./store/index");
const storage_1 = require("./utils/storage");
const config_1 = require("./config");
App({
    globalData: {
        /** Dev 环境地址（局域网 IP，config.ts 统一管理） */
        DEV_API_BASE: config_1.DEV_DEFAULT_URL,
        /** 显式覆盖地址：留空表示走 config.ts 的三级降级链路 */
        apiBase: '',
        /** 当前登录态 token（只读镜像，写入以 TokenStorage 为准） */
        authToken: null,
    },
    /**
     * 全局运行时错误捕获（诊断用）。
     * 小程序「整页空白不渲染」往往由 onLoad / 模块初始化阶段的异常导致，
     * 这类异常默认只进 console、不弹红页，肉眼难以定位。
     * 这里统一把错误打印并弹窗，便于在真机/模拟器上一眼看到根因。
     */
    onError(msg) {
        console.error('[app] 运行时错误：', msg);
        try {
            wx.showModal({
                title: '运行时错误（诊断）',
                content: String(msg || '未知错误').slice(0, 500),
                showCancel: false,
                confirmText: '知道了',
            });
        }
        catch ( /* ignore */_a) { /* ignore */ }
    },
    /** 未处理的 Promise 拒绝（如 await 后未被 catch 的异常） */
    onUnhandledRejection(err) {
        console.error('[app] 未处理的 Promise 拒绝：', err === null || err === void 0 ? void 0 : err.reason);
    },
    /** 路由到不存在的页面时给出提示，避免静默白屏 */
    onPageNotFound(res) {
        console.error('[app] 页面不存在：', res === null || res === void 0 ? void 0 : res.path);
    },
    /**
     * 启动流程（全部同步、无网络阻塞、无跳转）：
     *   ① 清理历史脏键（幂等，仅一次性收尾旧版缓存）
     *   ② store.loadCache() 从 storage 恢复 → 首帧即有内容，实现秒开 & 离线可读
     *   ③ 恢复 token 镜像
     *   ④ Dev 环境打印缓存自检报告
     */
    onLaunch() {
        try {
            const cleared = (0, storage_1.clearDevAndLegacyCaches)();
            if (cleared.removed.length) {
                console.info('[app] 清理遗留脏键：', cleared.removed.join(', '));
            }
            // 关键：先读缓存再渲染，保证对话页首帧直接有历史消息
            index_1.store.loadCache();
            const token = storage_1.TokenStorage.get();
            if (token)
                this.globalData.authToken = token;
            if (this.isDev())
                (0, storage_1.storageSelfCheckReport)();
        }
        catch (err) {
            // 启动异常一律降级：不 throw，避免基础库把渲染层直接炸崩
            console.error('[app] onLaunch 初始化异常（已降级继续运行）：', err);
        }
    },
    /** 是否非正式版环境 */
    isDev() {
        var _a, _b, _c;
        try {
            const envVer = (_c = (_b = (_a = wx === null || wx === void 0 ? void 0 : wx.getAccountInfoSync) === null || _a === void 0 ? void 0 : _a.call(wx)) === null || _b === void 0 ? void 0 : _b.miniProgram) === null || _c === void 0 ? void 0 : _c.envVersion;
            return envVer !== 'release';
        }
        catch (_d) {
            return true;
        }
    },
    /** 退出登录：清 token + 清全局仓库（不做任何跳转，由调用页自行决定） */
    logout() {
        storage_1.TokenStorage.clear();
        this.globalData.authToken = null;
        index_1.store.clearAll();
    },
});
