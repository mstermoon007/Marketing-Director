Component({
  properties: {
    /** 是否正在思考（控制动画显示） */
    active: { type: Boolean, value: true },
    /** 已发生的思考步骤文本 */
    steps: { type: Array, value: [] as string[] },
  },
  data: {},
})
