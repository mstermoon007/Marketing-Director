"use strict";
/**
 * Agent 对话接口封装（阶段三：Agent 原生交互）
 *
 * 统一封装：
 *   - chatOnce      非流式一轮对话（降级 / 简单场景）
 *   - streamChat    SSE 流式对话（实时渲染思考过程）
 *   - getAgentHistory  读取会话历史
 *   - uploadReviewFiles 上传复盘图片 / 文件（两阶段）
 *
 * 所有接口自动附带 JWT（见 request.ts），错误已统一归类为 AppError。
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.chatOnce = chatOnce;
exports.streamChat = streamChat;
exports.getAgentHistory = getAgentHistory;
exports.uploadReviewFiles = uploadReviewFiles;
const request_1 = require("./request");
/**
 * 非流式一轮对话。
 */
function chatOnce(opts) {
    return (0, request_1.post)('/agent/chat', {
        message: opts.message,
        session_id: opts.sessionId || '',
        business_id: opts.businessId || '',
        files: opts.files || [],
    });
}
/**
 * 流式对话（SSE）。逐事件回调 onEvent，返回的句柄可 abort（见 StreamHandle）。
 */
function streamChat(opts) {
    return (0, request_1.stream)({
        url: '/agent/chat/stream',
        data: {
            message: opts.message,
            session_id: opts.sessionId || '',
            business_id: opts.businessId || '',
            files: opts.files || [],
        },
        onEvent: (e) => opts.onEvent(e),
        onError: opts.onError,
    });
}
/**
 * 读取某会话历史。
 */
function getAgentHistory(sessionId) {
    return (0, request_1.get)('/agent/history', { session_id: sessionId });
}
/**
 * 上传复盘资料到「两阶段复盘接口」（/review/{plan_id}/upload → /generate）。
 *
 * 注意：阶段四的「数据上传闭环」请改用 api/loops.ts 的 uploadMetrics()，
 * 它走 /metrics/upload 单次上传并直接返回解析后的 KPI。
 *
 * @param planId 关联的周计划 ID（后端两阶段接口所需）
 * @param files  本地临时文件路径数组
 */
function uploadReviewFiles(planId, files) {
    return (0, request_1.upload)(`/review/${planId}`, files);
}
