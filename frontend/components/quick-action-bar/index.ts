Component({
  properties: {
    /** 快捷操作：{label, prompt} */
    actions: {
      type: Array,
      value: [] as Array<{ label: string; prompt: string }>,
    },
  },
  methods: {
    onTap(e: WechatMiniprogram.TouchEvent): void {
      const idx = e.currentTarget.dataset.index
      const item = this.data.actions[idx]
      if (item) {
        this.triggerEvent('select', { prompt: item.prompt, label: item.label })
      }
    },
  },
})
