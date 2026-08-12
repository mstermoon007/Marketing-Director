"use strict";
/**
 * 统一API请求封装 V3.0
 *
 * 文档6.1节规范实现：
 *  - 统一响应格式：{ code: 0, data: {...}, message: "ok" }
 *  - Token自动注入（Authorization: Bearer xxx）
 *  - code=1002（未登录/Token过期）自动清态跳转onboarding
 *  - 环境配置（dev/prod）baseUrl 切换
 *  - PUT/DELETE 完整HTTP方法
 *
 * 向后兼容：保持 get/post/upload 函数签名不变，不破坏现有调用方
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.requestUtil = void 0;
exports.get = get;
exports.post = post;
exports.put = put;
exports.del = del;
exports.upload = upload;
exports.uploadFile = uploadFile;
exports.stream = stream;
const storage_1 = require("../utils/storage");
const auth_1 = require("../utils/auth");
const constants_1 = require("../utils/constants");
const error_1 = require("../utils/error");
const config_1 = require("../config");
// ======================== 常量集中定义 ========================
/** 旧占位符域名（生产校验：命中则判定为未配置） */
const PLACEHOLDER_DOMAIN = 'example.com';
// ===== 超时配置（环境分级，避免 WAServiceMainContext 全局 timeout 兜底炸崩渲染层）=====
/** Dev 环境（开发者工具 / 真机调试）：后端没起时 10s 快速失败，不傻等 30s */
const DEV_TIMEOUT = 10000;
/** Prod 环境（正式版）：正常网络 30s 超时 */
const PROD_TIMEOUT = 30000;
/** Dev 环境上传超时：上传慢多给点时间，但不要 60s */
const DEV_UPLOAD_TIMEOUT = 20000;
/** Prod 环境上传超时 */
const PROD_UPLOAD_TIMEOUT = 60000;
/** getBase() 解密总超时：避免 prod 场景下 showModal 等用户操作阻塞初始化整 3s 还没拿到 base → 快速降级 */
const GET_BASE_RESOLVE_TIMEOUT = 3000;
/**
 * 流式（SSE）请求超时：分块连接本身会持续较长时间，且后端有心跳保活，
 * 因此使用远大于一次性请求的超时（微信 wx.request timeout 上限约 60s）。
 * 配合后端 SSE 心跳注释行，避免 WAServiceMainContext 的 Error: timeout。
 */
const STREAM_TIMEOUT = 60000;
/** 按环境返回默认请求超时（毫秒） */
const defaultTimeoutMs = () => (detectEnvKind() === 'dev' ? DEV_TIMEOUT : PROD_TIMEOUT);
/** 按环境返回默认上传超时（毫秒） */
const defaultUploadTimeoutMs = () => detectEnvKind() === 'dev' ? DEV_UPLOAD_TIMEOUT : PROD_UPLOAD_TIMEOUT;
/**
 * 通用 Promise 超时工具：Promise.race([task, rejectAfter(ms)])
 * 用于任何可能被用户交互/解密/IO 阻塞的异步调用，防止卡死 → 基础库全局 timeout 兜底炸崩
 */
const withTimeout = (task, ms, desc = 'operation') => Promise.race([
    task,
    new Promise((_, reject) => {
        const _t = setTimeout(() => {
            clearTimeout(_t);
            reject(new Error(`${desc} 超时 (${ms}ms)，请检查后端服务或网络`));
        }, ms);
    }),
]);
/**
 * 终极兜底：检测并提示回环地址。
 * 不再自动替换为硬编码 IP，而是警告用户通过 Storage 配置真实 IP。
 */
const _sanitizeLocalhostUrl = (url) => {
    if (!url)
        return url;
    if (/^(https?:\/\/)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i.test(url)) {
        console.warn('[request] 检测到 localhost URL，真机调试将无法连接。\n' +
            '  请在 Console 执行：\n' +
            `  wx.setStorageSync('${storage_1.STORAGE_KEYS.DEV_API_BASE}', 'http://你的本机IP:${config_1.DEV_PORT}/api')`);
    }
    return url;
};
/**
 * Dev 环境 BaseURL 三级降级（委托至 config.ts 统一管理）：
 *   1. Storage(md:dev_api_base) — Console 设置一次即可持久化
 *   2. globalData.DEV_API_BASE — app.ts onLaunch 注入
 *   3. config.ts 默认值（localhost 兜底）— 仅开发工具模拟器可用
 */
const _resolveDevBaseUrl = () => (0, config_1.resolveDevBaseUrl)();
/**
 * 根据小程序 envVersion 判定环境
 *   develop  → dev（开发者工具 + 真机调试）
 *   trial    → dev（体验版）
 *   release  → prod（正式版，配置由登录后后端下发，不再本地解密）
 */
const detectEnvKind = () => {
    var _a, _b, _c, _d;
    try {
        const app = getApp();
        // 1) 显式 apiBase（兼容老代码，优先级最高，排除占位符域名）
        if (((_a = app === null || app === void 0 ? void 0 : app.globalData) === null || _a === void 0 ? void 0 : _a.apiBase) &&
            !app.globalData.apiBase.includes(PLACEHOLDER_DOMAIN) &&
            /^https?:\/\//.test(app.globalData.apiBase)) {
            return 'dev';
        }
        // 2) 微信官方 envVersion 判断
        const envVer = (_d = (_c = (_b = wx === null || wx === void 0 ? void 0 : wx.getAccountInfoSync) === null || _b === void 0 ? void 0 : _b.call(wx)) === null || _c === void 0 ? void 0 : _c.miniProgram) === null || _d === void 0 ? void 0 : _d.envVersion;
        if (envVer === 'release')
            return 'prod';
        return 'dev';
    }
    catch (_e) {
        return 'dev';
    }
};
/**
 * 读取登录后持久化的生产地址（后端下发）
 */
const _readStoredProdBaseUrl = () => {
    var _a;
    try {
        const fromStorage = (_a = wx === null || wx === void 0 ? void 0 : wx.getStorageSync) === null || _a === void 0 ? void 0 : _a.call(wx, storage_1.STORAGE_KEYS.API_BASE_URL);
        if (typeof fromStorage === 'string' && fromStorage)
            return fromStorage;
    }
    catch ( /* ignore */_b) { /* ignore */ }
    return null;
};
/**
 * 校验生产地址格式（必须是 https 的合法域名，排除占位符）
 */
const _isValidProdBaseUrl = (url) => {
    return (!!url &&
        !url.includes(PLACEHOLDER_DOMAIN) &&
        url.length >= 16 &&
        /^https:\/\/[a-z0-9.-]+(:\d+)?(\/.*)?$/i.test(url));
};
/** 生产地址缓存（小程序生命周期仅解析 1 次） */
let _cachedProdBaseUrl = undefined;
/**
 * BaseURL 获取链路：
 *   Dev  → globalData.DEV_API_BASE → Storage(md:dev_api_base) → 局域网 IP
 *   Prod → 登录成功后后端下发的 API_BASE_URL（持久化）→ 回退 PROD_DEFAULT_URL → 仍失败弹窗阻断
 *
 * 注意：无论哪条链路返回的 URL，最终在 wx.request 前都会被 _sanitizeLocalhostUrl 替换。
 */
const getBase = async () => {
    var _a;
    // 最高优先级：globalData.apiBase（兼容老代码），但跳过 localhost/回环地址
    try {
        const app = getApp();
        const base = (_a = app === null || app === void 0 ? void 0 : app.globalData) === null || _a === void 0 ? void 0 : _a.apiBase;
        if (base &&
            !/^(https?:\/\/)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i.test(base)) {
            return base;
        }
    }
    catch (_b) {
        /* ignore */
    }
    const env = detectEnvKind();
    if (env === 'dev') {
        const resolved = _resolveDevBaseUrl();
        // ⚠️ 若最终仍是回环地址（理论上不会），打印 WARN 引导用户
        if (/^(https?:\/\/)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i.test(resolved)) {
            console.warn('[request] Dev BaseURL 命中回环地址。请执行：\n' +
                `  wx.setStorageSync('${storage_1.STORAGE_KEYS.DEV_API_BASE}', '${config_1.DEV_DEFAULT_URL}')\n` +
                '然后关闭小程序重新打开。');
        }
        else {
            console.info(`[request] Dev BaseURL: ${resolved}`);
        }
        return resolved;
    }
    // ================ PROD 场景（release）================
    if (_cachedProdBaseUrl !== undefined) {
        if (_cachedProdBaseUrl)
            return _cachedProdBaseUrl;
    }
    // 生产地址来自「登录成功后后端下发并持久化」的配置，不再本地硬编码/加密
    const stored = _readStoredProdBaseUrl();
    const prodUrl = _isValidProdBaseUrl(stored)
        ? stored
        : (_isValidProdBaseUrl(config_1.PROD_DEFAULT_URL) ? config_1.PROD_DEFAULT_URL : null);
    if (prodUrl) {
        _cachedProdBaseUrl = prodUrl;
        return prodUrl;
    }
    // 失败：明确弹窗 → 抛错阻断
    _cachedProdBaseUrl = null;
    const hint = `生产环境 BaseURL 未配置\n` +
        `登录成功后后端会下发 api_base_url 并持久化；若仍为空：\n` +
        `  · 后端配置环境变量 PUBLIC_API_BASE_URL（公开生产域名）\n` +
        `  · 或前端 frontend/config.ts 的 PROD_DEFAULT_URL 填入公开生产域名`;
    console.error('[request] PROD_URL_INVALID: 后端未下发 api_base_url 且无引导地址');
    try {
        wx.showModal({
            title: '请先配置生产环境',
            content: hint,
            showCancel: false,
            confirmText: '知道了',
        });
    }
    catch (_c) {
        /* ignore */
    }
    throw new Error('[config] 生产环境URL未配置（后端未下发 api_base_url，且无 PROD_DEFAULT_URL 引导地址）');
};
/**
 * 核心请求函数：统一拦截逻辑
 *
 * 注意：getBase() 在 prod 场景下是 async 的（需要解密密文），
 * 所以本函数内部先「await getBase()」拿到最终 baseUrl，
 * 再进入 wx.request 的 Promise 回调式处理。
 */
function _requestCore(opts) {
    return (async () => {
        // getBase() 超时保护：prod 解密场景有 showModal 等用户交互可能阻塞，3s 没拿到就快速失败
        const base = await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL');
        return new Promise((resolve, reject) => {
            const header = Object.assign({ 'Content-Type': 'application/json' }, (opts.header || {}));
            // 1. 自动注入 Token
            if (!opts.skipAuth) {
                const token = storage_1.TokenStorage.get();
                if (token) {
                    header['Authorization'] = `Bearer ${token}`;
                }
            }
            const finalUrl = base + opts.url;
            // 🔴 终极兜底：如果仍然是 localhost/127.0.0.1，强制替换为局域网 IP（任何情况都不会向 localhost 发请求）
            const safeUrl = _sanitizeLocalhostUrl(finalUrl);
            if (safeUrl !== finalUrl) {
                console.warn('[request] 检测到 localhost URL，已强制替换为局域网 IP：', finalUrl, '→', safeUrl);
            }
            console.info(`[request] ${opts.method} ${safeUrl}`);
            const reqTimeout = opts.timeout || defaultTimeoutMs();
            wx.request({
                url: safeUrl,
                method: opts.method,
                data: opts.data,
                header,
                timeout: reqTimeout,
                success(res) {
                    const statusCode = res.statusCode;
                    // 401 / 403 → 当 token 过期处理
                    if (statusCode === 401 || statusCode === 403) {
                        (0, auth_1.handleTokenExpired)();
                        reject(new Error('登录已过期'));
                        return;
                    }
                    const r = (res.data || {});
                    if (opts.skipCodeCheck) {
                        resolve(r);
                        return;
                    }
                    if (typeof r.code === 'number') {
                        if (r.code === constants_1.API_CODE.SUCCESS) {
                            resolve(r.data);
                        }
                        else if (r.code === constants_1.API_CODE.NOT_LOGIN) {
                            (0, auth_1.handleTokenExpired)();
                            reject(new Error(r.message || '请先登录'));
                        }
                        else {
                            reject(new Error(r.message || `请求失败 (code=${r.code})`));
                        }
                    }
                    else {
                        // 后端未按规范返回 code：兜底
                        resolve(r);
                    }
                },
                fail(err) {
                    const msg = (err === null || err === void 0 ? void 0 : err.errMsg) || '网络请求失败';
                    if (msg.includes('timeout')) {
                        reject(new Error('请求超时，请重试'));
                    }
                    else if (msg.includes('fail') || msg.includes('abort')) {
                        reject(new Error('网络连接异常，请检查网络'));
                    }
                    else {
                        reject(new Error(msg));
                    }
                },
            });
        });
    })();
}
// ========== 对外方法：保持签名与老版本 100% 兼容 ==========
/** GET */
function get(path, data, opts) {
    return _requestCore(Object.assign({ url: path, method: 'GET', data }, opts));
}
/** POST JSON */
function post(path, body = {}, opts) {
    return _requestCore(Object.assign({ url: path, method: 'POST', data: body }, opts));
}
/** PUT JSON */
function put(path, body = {}, opts) {
    return _requestCore(Object.assign({ url: path, method: 'PUT', data: body }, opts));
}
/** DELETE */
function del(path, data, opts) {
    return _requestCore(Object.assign({ url: path, method: 'DELETE', data }, opts));
}
/**
 * 上传文件（逐文件 + 生成两阶段模式）
 *
 * 适配后端两阶段接口：
 *   1) POST /review/{plan_id}/upload  — 逐个暂存
 *   2) POST /review/{plan_id}/generate — 汇总生成复盘报告
 *
 * 兼容旧接口：若后端不支持两阶段，失败后回退到单次 POST /review/plan_xxx。
 * 此部分保留原实现，仅注入Authorization header。
 */
function upload(path, files) {
    return (async () => {
        // getBase() 超时保护：prod 解密场景有 showModal 等用户交互可能阻塞
        const base = _sanitizeLocalhostUrl(await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL'));
        const upTimeout = defaultUploadTimeoutMs();
        const reqTimeout = defaultTimeoutMs();
        return new Promise((resolve, reject) => {
            if (files.length === 0) {
                reject(new Error('请选择文件'));
                return;
            }
            // 构造通用 header（含 token）
            const token = storage_1.TokenStorage.get();
            const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
            let completed = 0;
            let failed = false;
            let legacyFallbackTried = false;
            // 逐个文件 stage 上传
            files.forEach((filePath) => {
                wx.uploadFile({
                    url: base + path + '/upload',
                    filePath,
                    name: 'file',
                    header: authHeader,
                    timeout: upTimeout,
                    success(res) {
                        try {
                            const r = JSON.parse(res.data);
                            if (r.code !== 0 && r.code !== undefined) {
                                failed = true;
                                reject(new Error(r.message || '上传失败'));
                                return;
                            }
                            completed++;
                            if (completed === files.length && !failed) {
                                // 全部上传完 → 调用 generate
                                wx.request({
                                    url: base + path + '/generate',
                                    method: 'POST',
                                    timeout: reqTimeout,
                                    header: Object.assign({ 'Content-Type': 'application/json' }, authHeader),
                                    success(genRes) {
                                        var _a;
                                        const gr = genRes.data;
                                        if (typeof gr.code === 'number' && gr.code !== 0) {
                                            reject(new Error(gr.message || '生成复盘报告失败'));
                                        }
                                        else {
                                            resolve(((_a = gr.data) !== null && _a !== void 0 ? _a : gr));
                                        }
                                    },
                                    fail(genErr) {
                                        reject(new Error(genErr.errMsg || '生成复盘报告失败'));
                                    },
                                });
                            }
                        }
                        catch (_a) {
                            failed = true;
                            reject(new Error('解析上传响应失败'));
                        }
                    },
                    fail(err) {
                        // 旧接口兼容：/upload 路径失败 → 回退到原整体上传
                        const msg = String(err.errMsg || '');
                        const isNotFound = msg.includes('url not found') || msg.includes('404') || msg.includes('not exist');
                        if (isNotFound && !legacyFallbackTried) {
                            legacyFallbackTried = true;
                            _uploadLegacy(base, path, files, authHeader, upTimeout).then(resolve).catch(reject);
                            return;
                        }
                        if (legacyFallbackTried)
                            return;
                        failed = true;
                        reject(new Error(err.errMsg || '上传失败'));
                    },
                });
            });
        });
    })();
}
/**
 * 通用单文件上传（阶段四闭环：数据上传 → 指标解析）
 *
 * 与 upload() 的两阶段复盘流程不同，这里是「一次 POST 一个文件」的通用形态，
 * 适用于 /metrics/upload 这类直接返回解析结果的端点。
 *
 * @param path      形如 '/metrics/upload'
 * @param filePath  wx.chooseMedia / chooseMessageFile 返回的本地临时路径
 * @param name      form-data 字段名（后端 UploadFile 参数名，默认 'file'）
 * @param formData  附加表单字段（会被 wx 转成字符串）
 */
function uploadFile(path, filePath, name = 'file', formData = {}) {
    return (async () => {
        const base = _sanitizeLocalhostUrl(await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL'));
        const token = storage_1.TokenStorage.get();
        const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
        return new Promise((resolve, reject) => {
            if (!filePath) {
                reject(new Error('请选择文件'));
                return;
            }
            wx.uploadFile({
                url: base + path,
                filePath,
                name,
                formData,
                header: authHeader,
                timeout: defaultUploadTimeoutMs(),
                success(res) {
                    var _a;
                    if (res.statusCode === 401 || res.statusCode === 403) {
                        (0, auth_1.handleTokenExpired)();
                        reject(new Error('登录已过期，请重新登录'));
                        return;
                    }
                    let parsed;
                    try {
                        parsed = JSON.parse(res.data);
                    }
                    catch (_b) {
                        reject(new Error('解析上传响应失败'));
                        return;
                    }
                    // 兼容 {code,data,message} 与裸对象（FastAPI 直返 dict）两种返回
                    if (parsed && typeof parsed.code === 'number') {
                        if (parsed.code === constants_1.API_CODE.NOT_LOGIN) {
                            (0, auth_1.handleTokenExpired)();
                            reject(new Error(parsed.message || '请先登录'));
                            return;
                        }
                        if (parsed.code !== constants_1.API_CODE.SUCCESS) {
                            reject(new Error(parsed.message || '上传失败'));
                            return;
                        }
                        resolve(((_a = parsed.data) !== null && _a !== void 0 ? _a : parsed));
                        return;
                    }
                    resolve(parsed);
                },
                fail(err) {
                    reject(new Error(err.errMsg || '上传失败'));
                },
            });
        });
    })();
}
/** 回退：旧版一次性上传接口（兼容） */
function _uploadLegacy(base, path, files, authHeader, upTimeout = 60000) {
    return new Promise((resolve, reject) => {
        const results = [];
        let completed = 0;
        files.forEach((filePath) => {
            wx.uploadFile({
                url: base + path,
                filePath,
                timeout: upTimeout,
                name: 'files',
                header: authHeader,
                success(res) {
                    var _a;
                    try {
                        const r = JSON.parse(res.data);
                        results.push(r);
                        completed++;
                        if (completed === files.length) {
                            const last = results[results.length - 1];
                            if (typeof last.code === 'number' && last.code !== 0) {
                                reject(new Error(last.message || '解析响应失败'));
                            }
                            else {
                                resolve(((_a = last.data) !== null && _a !== void 0 ? _a : last));
                            }
                        }
                    }
                    catch (_b) {
                        completed++;
                        reject(new Error('解析响应失败'));
                    }
                },
                fail(err) {
                    reject(new Error(err.errMsg || '上传失败'));
                },
            });
        });
    });
}
// ========== 流式（SSE / 分块）请求 ==========
/**
 * UTF-8 字节数组 → 字符串（不依赖 TextDecoder，兼容低版本基础库）
 */
function utf8Decode(bytes) {
    let out = '';
    let i = 0;
    const len = bytes.length;
    while (i < len) {
        const c = bytes[i++];
        if (c < 0x80) {
            out += String.fromCharCode(c);
        }
        else if (c >= 0xc0 && c < 0xe0) {
            const c2 = bytes[i++];
            out += String.fromCharCode(((c & 0x1f) << 6) | (c2 & 0x3f));
        }
        else if (c >= 0xe0 && c < 0xf0) {
            const c2 = bytes[i++];
            const c3 = bytes[i++];
            out += String.fromCharCode(((c & 0x0f) << 12) | ((c2 & 0x3f) << 6) | (c3 & 0x3f));
        }
        else {
            const c2 = bytes[i++];
            const c3 = bytes[i++];
            const c4 = bytes[i++];
            const cp = ((c & 0x07) << 18) | ((c2 & 0x3f) << 12) | ((c3 & 0x3f) << 6) | (c4 & 0x3f);
            const u = cp - 0x10000;
            out += String.fromCharCode(0xd800 + (u >> 10), 0xdc00 + (u & 0x3ff));
        }
    }
    return out;
}
/**
 * 从累加缓冲中切出完整 SSE 事件（以 \n\n 分隔），返回事件数组与剩余未完缓冲。
 */
function parseSSEBuffer(buffer) {
    var _a;
    const parts = buffer.split('\n\n');
    const rest = (_a = parts.pop()) !== null && _a !== void 0 ? _a : '';
    const events = [];
    for (const part of parts) {
        const lines = part.split('\n').filter((l) => l.startsWith('data:'));
        for (const line of lines) {
            const json = line.slice(5).trim();
            if (!json)
                continue;
            try {
                events.push(JSON.parse(json));
            }
            catch (_b) {
                /* 忽略不完整/非法片段 */
            }
        }
    }
    return { events, rest };
}
/**
 * 流式请求（SSE）：用 wx.request({enableChunked:true}) 接收分块，
 * 解析 `data: {json}\n\n` 事件并逐个回调。用于 Agent 思考过程实时渲染。
 *
 * 注意：SSE 走 JSON body（非纯文本），content-type 仍为 application/json。
 */
function stream(opts) {
    let aborted = false;
    let task = null;
    let settled = false;
    let resolveFn = () => { };
    let rejectFn = () => { };
    const promise = new Promise((resolve, reject) => {
        resolveFn = resolve;
        rejectFn = reject;
    });
    const onErr = (msg, isAbort = false) => {
        var _a;
        const appErr = (0, error_1.classifyError)(new Error(msg));
        if (!isAbort)
            (_a = opts.onError) === null || _a === void 0 ? void 0 : _a.call(opts, appErr);
        if (!settled) {
            settled = true;
            rejectFn(appErr);
        }
    };
    (async () => {
        try {
            const base = _sanitizeLocalhostUrl(await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL'));
            // 若在中止后才拿到 base，不再发起请求
            if (aborted)
                return;
            const token = storage_1.TokenStorage.get();
            const header = Object.assign({ 'Content-Type': 'application/json', Accept: 'text/event-stream' }, (opts.header || {}));
            if (token)
                header['Authorization'] = `Bearer ${token}`;
            let buffer = '';
            task = wx.request({
                url: base + opts.url,
                method: opts.method || 'POST',
                data: opts.data,
                header,
                timeout: opts.timeout || STREAM_TIMEOUT,
                enableChunked: true,
                success(res) {
                    const statusCode = res === null || res === void 0 ? void 0 : res.statusCode;
                    // 🔴 非 2xx 必须显式报错：鉴权失效(401/403)或服务端错误(5xx) 会让 SSE 根本不开始，
                    // 若静默吞掉，前端 agent 气泡永远空白 → 用户看到「发消息无反应」。
                    if (statusCode && statusCode >= 400) {
                        if (statusCode === 401 || statusCode === 403) {
                            (0, auth_1.handleTokenExpired)();
                        }
                        onErr(`流式请求失败 (HTTP ${statusCode})`);
                        return;
                    }
                    if (!settled) {
                        settled = true;
                        resolveFn();
                    }
                },
                fail(err) {
                    if (aborted)
                        return;
                    onErr((err === null || err === void 0 ? void 0 : err.errMsg) || '流式请求失败');
                },
            });
            task.onChunkReceived((res) => {
                if (aborted)
                    return;
                try {
                    const text = utf8Decode(new Uint8Array(res.data));
                    buffer += text;
                    const { events, rest } = parseSSEBuffer(buffer);
                    buffer = rest;
                    for (const e of events)
                        opts.onEvent(e);
                }
                catch (e) {
                    // 解码异常不中断整个流，仅记录
                    console.error('[stream] chunk decode error', e);
                }
            });
        }
        catch (e) {
            onErr((e === null || e === void 0 ? void 0 : e.message) || '流式请求初始化失败');
        }
    })();
    const abort = () => {
        if (aborted)
            return;
        aborted = true;
        try {
            task === null || task === void 0 ? void 0 : task.abort();
        }
        catch (_a) {
            /* ignore */
        }
        if (!settled) {
            settled = true;
            const err = (0, error_1.classifyError)(new Error('stream aborted'));
            err.isAbort = true;
            rejectFn(err);
        }
    };
    return { promise, abort };
}
// ========== 工具方法 ==========
exports.requestUtil = {
    /** 获取当前 baseUrl（调试用，注意：生产环境是异步解密） */
    getBaseUrl: getBase,
    /** 获取当前环境 */
    detectEnv: detectEnvKind,
    /** 重新设置 baseUrl（本地调试） */
    setBase(url) {
        try {
            const app = getApp();
            if (app === null || app === void 0 ? void 0 : app.globalData)
                app.globalData.apiBase = url;
        }
        catch (_a) {
            /* ignore */
        }
    },
};
