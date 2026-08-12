Component({
  properties: {
    /** 完成百分比 0~100 */
    percent: { type: Number, value: 0 },
    label: { type: String, value: '' },
    color: { type: String, value: '#5b8def' },
  },
  data: {
    width: '0%',
  },
  observers: {
    percent(val: number): void {
      const p = Math.max(0, Math.min(100, Math.round(val || 0)))
      this.setData({ width: `${p}%` })
    },
  },
})
