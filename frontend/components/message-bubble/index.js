"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const constants_1 = require("../../utils/constants");
/** 结构化卡片类型 → 中文标题 */
const CARD_LABEL = {
    diagnosis: '📊 诊断报告',
    plan: '🗺️ 营销计划',
    schedule: '📅 每周日程',
    review: '🔄 复盘报告',
    raw: '📦 结构化结果',
};
/** 不同卡片的行动号召文案（闭环：明确下一步动作） */
const CARD_CTA = {
    diagnosis: '查看完整报告 / 保存分享 →',
    plan: '微调并确认计划 →',
    schedule: '查看日程并打卡 →',
    review: '查看复盘与下周建议 →',
    raw: '点击查看 →',
};
/** 从卡片里提取业务主键，供页面跳转与反馈上报使用 */
function extractRefId(card) {
    if (!card)
        return '';
    switch (card.kind) {
        case 'diagnosis':
            return (card.report && card.report.id) || '';
        case 'plan':
            return (card.plan && card.plan.id) || '';
        case 'review':
            return (card.report && card.report.id) || '';
        default:
            return '';
    }
}
Component({
    properties: {
        role: { type: String, value: 'agent' },
        content: { type: String, value: '' },
        intent: { type: String, value: '' },
        thinkingSteps: { type: Array, value: [] },
        toolCalls: { type: Array, value: [] },
        /** 结构化结果卡片（后端 data 解析） */
        card: { type: Object, value: null },
        /** 是否仍在流式生成中 */
        streaming: { type: Boolean, value: false },
        /** 消息唯一 ID（反馈上报时回传，便于定位） */
        msgId: { type: String, value: '' },
        /** 已提交的反馈：1 赞 / -1 踩 / 0 未评价 */
        feedback: { type: Number, value: 0 },
    },
    data: {
        intentLabel: '',
        cardTitle: '',
        cardKind: '',
        cardCta: '',
        cardRefId: '',
        /** 仅在「有实质产出的 agent 消息」上展示反馈条 */
        showFeedback: false,
    },
    observers: {
        intent(val) {
            this.setData({ intentLabel: val ? constants_1.AGENT_INTENT_LABEL[val] || '' : '' });
        },
        card(val) {
            const kind = val && val.kind ? String(val.kind) : '';
            this.setData({
                cardKind: kind,
                cardTitle: kind ? CARD_LABEL[kind] || '📦 结构化结果' : '',
                cardCta: kind ? CARD_CTA[kind] || '点击查看 →' : '',
                cardRefId: extractRefId(val),
            });
            this.refreshFeedbackVisible();
        },
        'role, streaming, content'() {
            this.refreshFeedbackVisible();
        },
    },
    methods: {
        /** 有内容、非流式中的 agent 消息才展示 👍/👎 */
        refreshFeedbackVisible() {
            const p = this.properties;
            const visible = p.role === 'agent' && !p.streaming && !!(p.content || '').trim();
            if (this.data.showFeedback !== visible)
                this.setData({ showFeedback: visible });
        },
        /** 点击结果卡片 → 冒泡给页面，由页面决定跳看板还是计划详情 */
        onCardTap() {
            if (!this.data.cardKind)
                return;
            this.triggerEvent('cardtap', {
                kind: this.data.cardKind,
                refId: this.data.cardRefId,
                card: this.properties.card,
            });
        },
        /** 👍 / 👎 → 冒泡给页面调用 feedback 端点（持续学习） */
        onFeedback(e) {
            const rating = Number(e.currentTarget.dataset.rating) || 0;
            // 再次点击同一个按钮 = 取消评价
            const next = this.properties.feedback === rating ? 0 : rating;
            this.triggerEvent('feedback', {
                rating: next,
                msgId: this.properties.msgId,
                kind: this.data.cardKind || 'chat',
                refId: this.data.cardRefId,
            });
        },
    },
});
