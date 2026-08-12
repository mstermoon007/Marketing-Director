/**
 * Canvas 2D 上下文最小类型
 * 说明：不同版本 @types/wechat-miniprogram 对 CanvasRenderingContext2D 的命名空间不一致，
 *       这里只声明本组件真正用到的绘制 API，避免类型不可用导致编译失败。
 */
interface Ctx2D {
  clearRect(x: number, y: number, w: number, h: number): void
  beginPath(): void
  closePath(): void
  moveTo(x: number, y: number): void
  lineTo(x: number, y: number): void
  arc(x: number, y: number, r: number, sAngle: number, eAngle: number): void
  stroke(): void
  fill(): void
  fillText(text: string, x: number, y: number): void
  scale(x: number, y: number): void
  strokeStyle: string
  fillStyle: string
  lineWidth: number
  font: string
  textAlign: string
  textBaseline: string
}

/** Canvas 节点（type="2d"） */
interface Canvas2DNode {
  width: number
  height: number
  getContext(type: '2d'): Ctx2D
}

Component({
  properties: {
    /** 维度标签（5 维） */
    labels: { type: Array, value: ['定位', '产品', '渠道', '内容', '转化'] as string[] },
    /** 各维度得分 0~100，顺序与 labels 对应 */
    values: { type: Array, value: [] as number[] },
    /** 画布直径（px） */
    size: { type: Number, value: 240 },
  },
  data: {},
  observers: {
    'labels, values': function (this: any): void {
      this.draw()
    },
  },
  lifetimes: {
    ready(): void {
      this.draw()
    },
  },
  methods: {
    draw(): void {
      const labels = (this.data.labels || []) as string[]
      const values = (this.data.values || []) as number[]
      if (!labels.length || !values.length) return

      const query = this.createSelectorQuery()
      query
        .select('#radar')
        .fields({ node: true, size: true })
        .exec((res: any[]) => {
          const info = res && res[0]
          if (!info || !info.node) return
          const canvas = info.node as Canvas2DNode
          const ctx = canvas.getContext('2d')
          const dpr = (wx.getSystemInfoSync().pixelRatio as number) || 2
          const size = this.data.size as number
          canvas.width = size * dpr
          canvas.height = size * dpr
          ctx.scale(dpr, dpr)
          this.render(ctx, size, labels, values)
        })
    },

    render(
      ctx: Ctx2D,
      size: number,
      labels: string[],
      values: number[],
    ): void {
      const cx = size / 2
      const cy = size / 2
      const radius = size / 2 - 34
      const n = labels.length
      const angle = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n

      ctx.clearRect(0, 0, size, size)

      // 网格环
      ctx.strokeStyle = '#23304d'
      ctx.lineWidth = 1
      for (let ring = 1; ring <= 4; ring++) {
        const r = (radius * ring) / 4
        ctx.beginPath()
        for (let i = 0; i <= n; i++) {
          const a = angle(i % n)
          const x = cx + r * Math.cos(a)
          const y = cy + r * Math.sin(a)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
      }

      // 轴线 + 标签
      ctx.fillStyle = '#9fb0cc'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      for (let i = 0; i < n; i++) {
        const a = angle(i)
        const x = cx + radius * Math.cos(a)
        const y = cy + radius * Math.sin(a)
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(x, y)
        ctx.strokeStyle = '#23304d'
        ctx.stroke()
        const lx = cx + (radius + 16) * Math.cos(a)
        const ly = cy + (radius + 16) * Math.sin(a)
        ctx.fillText(labels[i], lx, ly)
      }

      // 数据多边形
      ctx.beginPath()
      for (let i = 0; i <= n; i++) {
        const idx = i % n
        const v = Math.max(0, Math.min(100, values[idx] || 0)) / 100
        const a = angle(idx)
        const x = cx + radius * v * Math.cos(a)
        const y = cy + radius * v * Math.sin(a)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.fillStyle = 'rgba(91,141,239,0.28)'
      ctx.fill()
      ctx.strokeStyle = '#5b8def'
      ctx.lineWidth = 2
      ctx.stroke()

      // 顶点
      for (let i = 0; i < n; i++) {
        const v = Math.max(0, Math.min(100, values[i] || 0)) / 100
        const a = angle(i)
        const x = cx + radius * v * Math.cos(a)
        const y = cy + radius * v * Math.sin(a)
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, Math.PI * 2)
        ctx.fillStyle = '#5b8def'
        ctx.fill()
      }
    },
  },
})
