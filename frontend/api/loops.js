"use strict";
/**
 * 闭环业务接口封装（阶段四：功能闭环实现与联通）
 *
 * 对应后端 src/api/loops.py，把「一次性对话输出」升级为可保存 / 可编辑 /
 * 可确认 / 可反馈的完整业务闭环：
 *
 *   计划闭环   confirmPlan / editPlan / regeneratePlan
 *   日程闭环   checkinTodo / syncSchedule / getSchedule
 *   数据闭环   uploadMetrics
 *   复盘闭环   triggerReview / applyReview
 *   持续学习   submitFeedback
 *
 * 所有接口自动附带 JWT（见 request.ts）。
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.confirmPlan = confirmPlan;
exports.editPlan = editPlan;
exports.regeneratePlan = regeneratePlan;
exports.checkinTodo = checkinTodo;
exports.syncSchedule = syncSchedule;
exports.getSchedule = getSchedule;
exports.uploadMetrics = uploadMetrics;
exports.stageFile = stageFile;
exports.stageFiles = stageFiles;
exports.triggerReview = triggerReview;
exports.applyReview = applyReview;
exports.submitFeedback = submitFeedback;
exports.groupTodosByDay = groupTodosByDay;
const request_1 = require("./request");
/**
 * 确认计划 → 后端标记 confirmed + 自动排期落库 todos。
 * 这是「计划闭环 → 日程闭环」的衔接点。
 */
function confirmPlan(planId) {
    return (0, request_1.post)(`/plan/${planId}/confirm`, {});
}
/** 微调计划中的任务，写回后端 days JSON。 */
function editPlan(planId, edits) {
    return (0, request_1.post)(`/plan/${planId}/edit`, { edits: edits });
}
/** 重新生成计划（结合最新记忆 + 反馈评分）。 */
function regeneratePlan(planId) {
    return (0, request_1.post)(`/plan/${planId}/regenerate`, {});
}
// ============================================================
// 二、日程闭环
// ============================================================
/**
 * 任务打卡 / 状态变更 → 落库 todos，供复盘 Agent 读取真实执行情况。
 */
function checkinTodo(opts) {
    const body = { todo_id: opts.todoId };
    if (opts.status !== undefined)
        body.status = opts.status;
    if (opts.notes !== undefined)
        body.notes = opts.notes;
    if (opts.images !== undefined)
        body.images = opts.images;
    return (0, request_1.put)('/schedule/checkin', body);
}
/**
 * 把对话里产出的排期结果补录落库（快捷指令「安排本周日程」场景）。
 */
function syncSchedule(opts) {
    return (0, request_1.post)('/schedule/sync', {
        business_id: opts.businessId || '',
        plan_id: opts.planId || null,
        days: opts.days,
    });
}
/** 读取已落库排期（跨会话持久，反映真实打卡状态）。 */
function getSchedule(businessId = '') {
    return (0, request_1.get)('/schedule', businessId ? { business_id: businessId } : {});
}
/**
 * 上传业务数据（CSV / 截图）→ 后端安全解析 → 落库 metrics → 返回 KPI。
 * 前端只需把 wx.chooseMedia / chooseMessageFile 的临时路径传进来。
 */
function uploadMetrics(filePath, businessId = '') {
    return (0, request_1.uploadFile)('/metrics/upload', filePath, 'file', businessId ? { business_id: businessId } : {});
}
/**
 * 通用文件暂存：小程序本地临时路径 → 服务端可读路径。
 *
 * 必须先走这一步，`streamChat({ files })` 传的路径服务端才打得开；
 * 直接把 wx 的 tempFilePath 丢给后端，Agent 是读不到内容的。
 */
function stageFile(filePath) {
    return (0, request_1.uploadFile)('/files/upload', filePath, 'file');
}
/** 批量暂存，返回服务端路径数组（单个失败不影响其余）。 */
async function stageFiles(filePaths) {
    const out = [];
    for (const p of filePaths) {
        try {
            const r = await stageFile(p);
            if (r && r.file_path)
                out.push(r.file_path);
        }
        catch (err) {
            console.warn('[loops] 文件暂存失败，已跳过：', p, err);
        }
    }
    return out;
}
/** 触发复盘（周末定时 / 手动）。无上传数据时返回 needs_upload=true。 */
function triggerReview(opts = {}) {
    var _a;
    return (0, request_1.post)('/review/trigger', {
        business_id: opts.businessId || '',
        week_number: (_a = opts.weekNumber) !== null && _a !== void 0 ? _a : null,
    });
}
/** 采纳复盘建议 → 重新生成下周计划并自动排期。 */
function applyReview(reviewId, businessId = '') {
    return (0, request_1.post)(`/review/${reviewId}/apply`, { business_id: businessId });
}
/**
 * 提交反馈（👍 rating=1 / 👎 rating=-1 / 修改计划 rating=-1 + comment）。
 * 后端据此更新 strategy_scores，影响后续 RAG 检索排序 → 「越用越懂你」。
 */
function submitFeedback(opts) {
    return (0, request_1.post)('/agent/feedback', {
        target_type: opts.targetType,
        target_id: opts.targetId || null,
        rating: opts.rating,
        comment: opts.comment || null,
        business_id: opts.businessId || null,
        card_ids: opts.cardIds || [],
    });
}
// ============================================================
// 六、辅助：后端 todo → 前端 Task 视图模型
// ============================================================
/** 把后端 todos 按 day_index 聚合成 DayPlan[]（日历视图用）。 */
function groupTodosByDay(todos) {
    const DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const map = new Map();
    (todos || []).forEach((t) => {
        const idx = t.day_index || 1;
        if (!map.has(idx)) {
            map.set(idx, {
                day_index: idx,
                day_name: DAY_NAMES[(idx - 1) % 7] || `第${idx}天`,
                date: t.date || '',
                focus: '',
                tasks: [],
            });
        }
        const day = map.get(idx);
        if (!day.date && t.date)
            day.date = t.date;
        const task = {
            id: t.id,
            time_slot: t.time_slot || '',
            title: t.title,
            how_to: t.how_to || '',
            checklist: t.checklist || [],
            status: t.status,
            done: t.status === 'done',
            notes: t.notes || '',
            images: t.images || [],
            completed_at: t.completed_at,
        };
        day.tasks.push(task);
    });
    return Array.from(map.values()).sort((a, b) => a.day_index - b.day_index);
}
