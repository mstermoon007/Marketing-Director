"use strict";
Component({
    properties: {
        /** 维度标签（5 维） */
        labels: { type: Array, value: ['定位', '产品', '渠道', '内容', '转化'] },
        /** 各维度得分 0~100，顺序与 labels 对应 */
        values: { type: Array, value: [] },
        /** 画布直径（px） */
        size: { type: Number, value: 240 },
    },
    data: {},
    observers: {
        'labels, values': function () {
            this.draw();
        },
    },
    lifetimes: {
        ready() {
            this.draw();
        },
    },
    methods: {
        draw() {
            const labels = (this.data.labels || []);
            const values = (this.data.values || []);
            if (!labels.length || !values.length)
                return;
            const query = this.createSelectorQuery();
            query
                .select('#radar')
                .fields({ node: true, size: true })
                .exec((res) => {
                const info = res && res[0];
                if (!info || !info.node)
                    return;
                const canvas = info.node;
                const ctx = canvas.getContext('2d');
                const dpr = wx.getSystemInfoSync().pixelRatio || 2;
                const size = this.data.size;
                canvas.width = size * dpr;
                canvas.height = size * dpr;
                ctx.scale(dpr, dpr);
                this.render(ctx, size, labels, values);
            });
        },
        render(ctx, size, labels, values) {
            const cx = size / 2;
            const cy = size / 2;
            const radius = size / 2 - 34;
            const n = labels.length;
            const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
            ctx.clearRect(0, 0, size, size);
            // 网格环
            ctx.strokeStyle = '#23304d';
            ctx.lineWidth = 1;
            for (let ring = 1; ring <= 4; ring++) {
                const r = (radius * ring) / 4;
                ctx.beginPath();
                for (let i = 0; i <= n; i++) {
                    const a = angle(i % n);
                    const x = cx + r * Math.cos(a);
                    const y = cy + r * Math.sin(a);
                    if (i === 0)
                        ctx.moveTo(x, y);
                    else
                        ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
            // 轴线 + 标签
            ctx.fillStyle = '#9fb0cc';
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            for (let i = 0; i < n; i++) {
                const a = angle(i);
                const x = cx + radius * Math.cos(a);
                const y = cy + radius * Math.sin(a);
                ctx.beginPath();
                ctx.moveTo(cx, cy);
                ctx.lineTo(x, y);
                ctx.strokeStyle = '#23304d';
                ctx.stroke();
                const lx = cx + (radius + 16) * Math.cos(a);
                const ly = cy + (radius + 16) * Math.sin(a);
                ctx.fillText(labels[i], lx, ly);
            }
            // 数据多边形
            ctx.beginPath();
            for (let i = 0; i <= n; i++) {
                const idx = i % n;
                const v = Math.max(0, Math.min(100, values[idx] || 0)) / 100;
                const a = angle(idx);
                const x = cx + radius * v * Math.cos(a);
                const y = cy + radius * v * Math.sin(a);
                if (i === 0)
                    ctx.moveTo(x, y);
                else
                    ctx.lineTo(x, y);
            }
            ctx.closePath();
            ctx.fillStyle = 'rgba(91,141,239,0.28)';
            ctx.fill();
            ctx.strokeStyle = '#5b8def';
            ctx.lineWidth = 2;
            ctx.stroke();
            // 顶点
            for (let i = 0; i < n; i++) {
                const v = Math.max(0, Math.min(100, values[i] || 0)) / 100;
                const a = angle(i);
                const x = cx + radius * v * Math.cos(a);
                const y = cy + radius * v * Math.sin(a);
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fillStyle = '#5b8def';
                ctx.fill();
            }
        },
    },
});
