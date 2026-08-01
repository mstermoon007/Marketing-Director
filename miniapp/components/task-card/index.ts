/**
 * 任务卡片组件，展示任务详情与签到操作
 *
 * @file    index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { Task } from '../../types/index'

import { TASK_STATUS, TASK_STATUS_LABEL } from '../../utils/constants'

interface TaskCardProperties {
  task: Task
  showCheckin: boolean
}

interface TaskCardData {
  statusIcon: string
  statusLabel: string
  isDone: boolean
  isDoing: boolean
  isPending: boolean
}

/**
 * 根据任务状态计算显示数据
 *
 * @param task 任务对象
 * @returns 状态显示数据
 */
function computeTaskStatus(task: Task): { statusIcon: string; statusLabel: string; isDone: boolean; isDoing: boolean; isPending: boolean } {
  const status = task.status ?? (task.done ? TASK_STATUS.DONE : TASK_STATUS.PENDING)
  let icon = ''
  let isDone = false
  let isDoing = false
  let isPending = false

  switch (status) {
    case TASK_STATUS.DONE:
      icon = '✅'
      isDone = true
      break
    case TASK_STATUS.DOING:
      icon = '🔄'
      isDoing = true
      break
    default:
      icon = '⬜'
      isPending = true
      break
  }

  return {
    statusIcon: icon,
    statusLabel: TASK_STATUS_LABEL[status] ?? '未开始',
    isDone,
    isDoing,
    isPending,
  }
}

Component<TaskCardProperties, TaskCardData, WechatMiniprogram.IAnyObject>({
  properties: {
    task: {
      type: Object,
      value: {} as Task,
    },
    showCheckin: {
      type: Boolean,
      value: true,
    },
  },

  data: {
    statusIcon: '',
    statusLabel: '',
    isDone: false,
    isDoing: false,
    isPending: false,
  },

  observers: {
    task: function (task: Task): void {
      if (!task) return
      this.setData(computeTaskStatus(task))
    },
  },

  lifetimes: {
    attached(): void {
      const { task } = this.properties
      if (task && task.id) {
        this.setData(computeTaskStatus(task))
      }
    },
  },

  methods: {
    /**
     * 点击任务卡片触发detail事件
     */
    onTapDetail(): void {
      this.triggerEvent('detail', { task: this.properties.task })
    },

    /**
     * 点击签到按钮触发checkin事件
     */
    onCheckin(): void {
      this.triggerEvent('checkin', { task: this.properties.task })
    },
  },
})
