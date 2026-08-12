"use strict";
/**
 * 诊断详情页（阶段四 · 诊断闭环）
 *
 * 展示 AI 诊断产出的结构化报告：
 *   综合健康度总分 → 五维雷达图 → Top 核心问题 → 季度路线图。
 *
 * 数据来源：对话产出后由 store.setDiagnosis 持久化（store.diagnosis）。
 * 本页只做「只读展示 + 保存/分享」——满足阶段四「诊断闭环：支持保存与分享」。
 *
 * 保存：报告已随对话自动写入本地（wx.storage），并提供「复制诊断要点」一键带走；
 * 分享：onShareAppMessage 生成分享卡片。
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("../../../store/index");
const constants_1 = require("../../../utils/constants");
const date_1 = require("../../../utils/date");
/** 五维固定顺序（与雷达图默认标签一致） */
const DIM_KEYS = ['positioning', 'product', 'channel', 'content', 'conversion'];
const DIM_LABELS = ['定位', '产品', '渠道', '内容', '转化'];
Page({
    data: {
        hasData: false,
        diagnosis: null,
        overallScore: 0,
        scoreLabel: '',
        scoreColor: '#5b8def',
        radar: { labels: DIM_LABELS, values: [] },
        issues: [],
        roadmapPhases: [],
        roadmapGoal: '',
        updatedText: '',
        copiedTip: false,
    },
    _unsub: undefined,
    onLoad() {
        const unsub = (0, index_1.bindStore)(this, (s) => this.build(s.diagnosis));
        this._unsub = unsub;
    },
    onUnload() {
        if (this._unsub)
            this._unsub();
    },
    build(d) {
        var _a, _b;
        if (!d) {
            return { hasData: false, diagnosis: null, radar: { labels: DIM_LABELS, values: [] } };
        }
        const meta = this.scoreMeta((_a = d.overall_score) !== null && _a !== void 0 ? _a : 0);
        return {
            hasData: true,
            diagnosis: d,
            overallScore: (_b = d.overall_score) !== null && _b !== void 0 ? _b : 0,
            scoreLabel: meta.label,
            scoreColor: meta.color,
            radar: this.buildRadar(d),
            issues: (d.top_issues || []).map((it) => (Object.assign(Object.assign({}, it), { levelLabel: constants_1.ISSUE_LEVEL_LABEL[it.level] || '', levelColor: constants_1.ISSUE_LEVEL_COLOR[it.level] || '#999', levelIcon: constants_1.ISSUE_LEVEL_ICON[it.level] || '•' }))),
            roadmapPhases: (d.quarterly_roadmap && d.quarterly_roadmap.phases) || [],
            roadmapGoal: (d.quarterly_roadmap && d.quarterly_roadmap.overall_goal) || '',
            updatedText: d.created_at ? `更新于 ${(0, date_1.formatRelativeTime)(d.created_at)}` : '',
        };
    },
    /** 五维得分 → 雷达图数据 */
    buildRadar(d) {
        const ds = d.dimension_scores || {};
        const values = DIM_KEYS.map((k) => { var _a; return Number((_a = ds[k]) !== null && _a !== void 0 ? _a : 0); });
        return { labels: DIM_LABELS, values };
    },
    /** 综合分 → 等级标签与配色 */
    scoreMeta(score) {
        if (score >= 80)
            return { label: '健康', color: '#07c160' };
        if (score >= 60)
            return { label: '良好', color: '#5b8def' };
        if (score >= 40)
            return { label: '偏弱', color: '#ff976a' };
        return { label: '预警', color: '#ee0a24' };
    },
    /** 一键复制诊断要点（保存/带走） */
    onCopySummary() {
        const d = this.data.diagnosis;
        if (!d)
            return;
        const lines = [];
        lines.push(`【营销健康诊断】综合得分 ${d.overall_score}/100（${this.data.scoreLabel}）`);
        if (d.overall_comment)
            lines.push(`总评：${d.overall_comment}`);
        const ds = d.dimension_scores || {};
        const dimText = DIM_KEYS.filter((k) => ds[k] != null)
            .map((k) => `${DIM_LABELS[DIM_KEYS.indexOf(k)]} ${ds[k]}`)
            .join(' / ');
        if (dimText)
            lines.push(`五维：${dimText}`);
        (d.top_issues || []).forEach((it, i) => {
            lines.push(`${i + 1}. [${constants_1.ISSUE_LEVEL_LABEL[it.level] || ''}] ${it.title} —— ${it.suggestion || ''}`);
        });
        wx.setClipboardData({
            data: lines.join('\n'),
            success: () => {
                this.setData({ copiedTip: true });
                setTimeout(() => this.setData({ copiedTip: false }), 1600);
            },
        });
    },
    goChat() {
        wx.switchTab({ url: '/pages/chat/index' });
    },
    /** 分享诊断报告 */
    onShareAppMessage() {
        const d = this.data.diagnosis;
        const score = d ? d.overall_score : 0;
        return {
            title: d
                ? `我的营销健康诊断：${score}分（${this.data.scoreLabel}）`
                : 'AI 营销健康诊断',
            path: '/pages/chat/index',
        };
    },
});
