import { TASK_STATUS, TASK_STATUS_LABEL } from '../../utils/constants'

Component({
  properties: {
    task: { type: Object, value: {} as Record<string, unknown> },
    /** 所属日名称（日程页展示用） */
    dayName: { type: String, value: '' },
  },
  data: {
    statusLabel: '',
    checked: false,
  },
  observers: {
    task(val: any): void {
      const status = (val && val.status) || TASK_STATUS.PENDING
      this.setData({
        statusLabel: TASK_STATUS_LABEL[status as keyof typeof TASK_STATUS_LABEL] || '未开始',
        checked: status === TASK_STATUS.DONE,
      })
    },
  },
  methods: {
    onToggle(): void {
      const t = this.data.task as { id?: string }
      this.triggerEvent('toggle', { id: t.id })
    },
  },
})
