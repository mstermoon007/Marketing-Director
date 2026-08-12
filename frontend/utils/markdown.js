"use strict";
/**
 * 轻量 Markdown → HTML 转换器（阶段三）
 *
 * 用于 <rich-text> 渲染 Agent 回复。支持常用语法：
 *   标题(#/##/###)、加粗**、斜体*、行内代码`、代码块```、无序/有序列表、
 *   引用 >、分割线 ---、链接 [text](url)、换行。
 *
 * 安全：所有原始文本先做 HTML 转义；链接仅允许 http/https；
 * 生成的 HTML 交由 rich-text 渲染（不执行脚本）。
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.markdownToHtml = markdownToHtml;
function escapeHtml(s) {
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
function inline(text) {
    let t = escapeHtml(text);
    // 行内代码
    t = t.replace(/`([^`]+)`/g, (_m, c) => `<code style="background:#1f2a44;color:#9fd0ff;padding:1px 5px;border-radius:4px;font-size:13px;">${c}</code>`);
    // 加粗
    t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // 斜体
    t = t.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
    // 链接
    t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, txt, url) => `<a href="${url}" style="color:#5B8DEF;">${txt}</a>`);
    return t;
}
function markdownToHtml(md) {
    if (!md)
        return '';
    const lines = md.replace(/\r\n/g, '\n').split('\n');
    const html = [];
    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        // 代码块 ```
        if (/^```/.test(line)) {
            const buf = [];
            i++;
            while (i < lines.length && !/^```/.test(lines[i])) {
                buf.push(escapeHtml(lines[i]));
                i++;
            }
            i++; // 跳过结束 ```
            html.push(`<div style="background:#0f1626;border:1px solid #23304d;border-radius:8px;padding:10px 12px;margin:8px 0;font-size:13px;color:#cfe0ff;white-space:pre-wrap;word-break:break-word;">${buf.join('\n')}</div>`);
            continue;
        }
        // 空行
        if (line.trim() === '') {
            i++;
            continue;
        }
        // 分割线
        if (/^---+$/.test(line.trim())) {
            html.push('<hr style="border:none;border-top:1px solid #23304d;margin:10px 0;"/>');
            i++;
            continue;
        }
        // 标题
        const h = line.match(/^(#{1,3})\s+(.*)$/);
        if (h) {
            const level = h[1].length;
            const sizes = { 1: '19px', 2: '17px', 3: '15px' };
            const m = sizes[level] || '15px';
            html.push(`<p style="font-size:${m};font-weight:700;color:#fff;margin:10px 0 6px;">${inline(h[2])}</p>`);
            i++;
            continue;
        }
        // 引用
        if (/^>\s?/.test(line)) {
            const buf = [];
            while (i < lines.length && /^>\s?/.test(lines[i])) {
                buf.push(inline(lines[i].replace(/^>\s?/, '')));
                i++;
            }
            html.push(`<div style="border-left:3px solid #5B8DEF;background:#101a2e;padding:6px 12px;margin:8px 0;color:#b9c6de;">${buf.join('<br/>')}</div>`);
            continue;
        }
        // 无序列表
        if (/^\s*[-*]\s+/.test(line)) {
            const items = [];
            while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
                items.push(`<li style="margin:3px 0;">${inline(lines[i].replace(/^\s*[-*]\s+/, ''))}</li>`);
                i++;
            }
            html.push(`<ul style="padding-left:20px;margin:6px 0;color:#dbe4f5;">${items.join('')}</ul>`);
            continue;
        }
        // 有序列表
        if (/^\s*\d+\.\s+/.test(line)) {
            const items = [];
            while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
                items.push(`<li style="margin:3px 0;">${inline(lines[i].replace(/^\s*\d+\.\s+/, ''))}</li>`);
                i++;
            }
            html.push(`<ol style="padding-left:20px;margin:6px 0;color:#dbe4f5;">${items.join('')}</ol>`);
            continue;
        }
        // 段落（合并连续普通行）
        const para = [];
        while (i < lines.length &&
            lines[i].trim() !== '' &&
            !/^```/.test(lines[i]) &&
            !/^#{1,3}\s/.test(lines[i]) &&
            !/^>\s?/.test(lines[i]) &&
            !/^\s*[-*]\s+/.test(lines[i]) &&
            !/^\s*\d+\.\s+/.test(lines[i]) &&
            !/^---+$/.test(lines[i].trim())) {
            para.push(inline(lines[i]));
            i++;
        }
        html.push(`<p style="margin:6px 0;line-height:1.7;color:#dbe4f5;">${para.join('<br/>')}</p>`);
    }
    return html.join('');
}
