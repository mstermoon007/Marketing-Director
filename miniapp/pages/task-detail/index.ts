/**
 * 任务详情页 Task Detail，Checklist、图文记录与打卡完成
 *
 * @file    pages/task-detail/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { DayPlan, SevenDayPlan, Task, TaskDetail } from '../../types/index'

import { TASK_STATUS, TASK_STATUS_LABEL } from '../../utils/constants'

import { get, post } from '../../api/request'

interface TextNote {
  id: string
  content: string
  created_at: string
}

interface ImageNote {
  id: string
  url: string
}

interface TaskDetailPageData {
  loading: boolean
  task: TaskDetail | null
  statusLabel: string
  statusClass: string
  checklistStates: boolean[]
  images: ImageNote[]
  textNotes: TextNote[]
  estimatedMinutes: number
  timeSlot: string
  isDone: boolean
}

Page<TaskDetailPageData, {}>({
  data: {
    loading: true,
    task: null,
    statusLabel: '未开始',
    statusClass: 'status-pending',
    checklistStates: [],
    images: [],
    textNotes: [],
    estimatedMinutes: 0,
    timeSlot: '',
    isDone: false,
  },

  /**
   * 页面加载：从 URL 参数取 task_id，缺失则 toast 返回
   *
   * @param options 路由参数 task_id
   * @returns Promise<void>
   * @example
   * ```ts
   * wx.navigateTo({ url: '/pages/task-detail/index?task_id=abc123' })
   * ```
   */
  async onLoad(options: { task_id?: string }): Promise<void> {
    const taskId = options.task_id
    if (!taskId) {
      wx.showToast({ title: '任务ID缺失', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1000)
      return
    }
    await this.loadTaskDetail(taskId)
  },

  /**
   * 加载任务详情：API → 失败则在 App.globalData.weeklyPlan 里查找 fallback
   *
   * @param taskId 任务ID
   * @returns Promise<void>
   */
  async loadTaskDetail(taskId: string): Promise<void> {
    this.setData({ loading: true })

    try {
      const task = await get<TaskDetail>('/task/detail', { task_id: taskId })
      this.renderTask(task, taskId)
    } catch (err) {
      try {
        const app = getApp<IAppOption>()
        const weeklyPlan = app.globalData.weeklyPlan as SevenDayPlan | null
        let foundTask: Task | undefined

        if (weeklyPlan?.days) {
          for (const day of weeklyPlan.days) {
            if (day.tasks) {
              foundTask = day.tasks.find((t: Task) => t.id === taskId)
              if (foundTask) break
            }
          }
        }

        if (foundTask) {
          this.renderTask(foundTask as TaskDetail, taskId)
        } else {
          throw err
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        console.error(`[task-detail] loadTaskDetail failed:`, msg)
        wx.showToast({ title: msg || '加载任务失败', icon: 'none' })
        this.setData({ loading: false })
      }
    }
  },

  /**
   * 渲染任务：状态映射、checklist 回显、图片/文字笔记提取
   *
   * @param task   任务详情
   * @param taskId 任务ID（用于 checklist storage key）
   */
  renderTask(task: TaskDetail, taskId: string): void {
    const status = task.status || (task.done ? TASK_STATUS.DONE : TASK_STATUS.PENDING)
    const statusLabel = TASK_STATUS_LABEL[status] || '未开始'

    let statusClass = 'status-pending'
    if (status === TASK_STATUS.DONE) statusClass = 'status-done'
    else if (status === TASK_STATUS.DOING) statusClass = 'status-doing'

    const isDone = status === TASK_STATUS.DONE

    const savedChecklist = wx.getStorageSync(`checklist_${taskId}`)
    let checklistStates: boolean[]
    if (savedChecklist && Array.isArray(savedChecklist)) {
      checklistStates = savedChecklist
    } else {
      checklistStates = task.checklist ? task.checklist.map(() => false) : []
    }

    const images: ImageNote[] = []
    const textNotes: TextNote[] = []

    if (task.execution_logs) {
      task.execution_logs.forEach((log) => {
        if (log.type === 'image') {
          images.push({
            id: log.id,
            url: log.content,
          })
        } else if (log.type === 'text') {
          textNotes.push({
            id: log.id,
            content: log.content,
            created_at: log.created_at,
          })
        }
      })
    }

    if (task.images) {
      task.images.forEach((url, idx) => {
        if (!images.find((img) => img.url === url)) {
          images.push({
            id: `img_${idx}_${Date.now()}`,
            url,
          })
        }
      })
    }

    this.setData({
      task,
      statusLabel,
      statusClass,
      checklistStates,
      images,
      textNotes,
      estimatedMinutes: task.estimated_minutes || 0,
      timeSlot: task.time_slot || '',
      isDone,
      loading: false,
    })
  },

  /**
   * Checklist 项切换：取反写回 data + 持久化到 Storage
   *
   * @param e dataset.idx 为子项索引
   * @returns void
   */
  onToggleChecklist(e: WechatMiniprogram.BaseEvent): void {
    const idx = e.currentTarget?.dataset?.idx as number
    if (idx === undefined || idx === null) return

    const states = [...this.data.checklistStates]
    states[idx] = !states[idx]
    this.setData({ checklistStates: states })

    const taskId = this.data.task?.id
    if (taskId) {
      wx.setStorageSync(`checklist_${taskId}`, states)
    }
  },

  /**
   * 添加图片：相册/拍照选择后 push 到 images 并立即预览
   *
   * @returns void
   */
  onAddImage(): void {
    if (this.data.isDone) {
      wx.showToast({ title: '任务已完成，无法添加', icon: 'none' })
      return
    }

    wx.chooseMedia({
      count: 9,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newImages: ImageNote[] = res.tempFiles.map((file, idx) => ({
          id: `newimg_${Date.now()}_${idx}`,
          url: file.tempFilePath,
        }))
        this.setData({
          images: [...this.data.images, ...newImages],
        })
        wx.previewImage({
          urls: newImages.map((img) => img.url),
          current: newImages[0].url,
        })
      },
    })
  },

  /**
   * 预览图片
   *
   * @param e dataset.idx 为 images 数组索引
   * @returns void
   */
  onPreviewImage(e: WechatMiniprogram.BaseEvent): void {
    const idx = e.currentTarget?.dataset?.idx as number
    if (idx === undefined || idx === null) return
    const urls = this.data.images.map((img) => img.url)
    wx.previewImage({
      urls,
      current: urls[idx],
    })
  },

  /**
   * 删除图片：已完成任务禁止删除
   *
   * @param e dataset.idx 为 images 数组索引
   * @returns void
   */
  onRemoveImage(e: WechatMiniprogram.BaseEvent): void {
    const idx = e.currentTarget?.dataset?.idx as number
    if (idx === undefined || idx === null) return
    if (this.data.isDone) {
      wx.showToast({ title: '任务已完成，无法删除', icon: 'none' })
      return
    }
    const images = [...this.data.images]
    images.splice(idx, 1)
    this.setData({ images })
  },

  /**
   * 添加文字笔记：弹可编辑 Modal，确认后 unshift 到 textNotes
   *
   * @returns void
   */
  onAddTextNote(): void {
    if (this.data.isDone) {
      wx.showToast({ title: '任务已完成，无法添加', icon: 'none' })
      return
    }

    wx.showModal({
      title: '添加文字记录',
      content: '',
      editable: true,
      placeholderText: '请输入执行备注...',
      success: (res) => {
        if (res.confirm && res.content && res.content.trim()) {
          const newNote: TextNote = {
            id: `note_${Date.now()}`,
            content: res.content.trim(),
            created_at: new Date().toISOString(),
          }
          this.setData({
            textNotes: [newNote, ...this.data.textNotes],
          })
        }
      },
    })
  },

  /**
   * 标记完成并打卡：聚合文字+图片 → POST /task/checkin → 回写状态 → 返回
   *
   * @returns Promise<void>
   */
  async onMarkDone(): Promise<void> {
    const task = this.data.task
    if (!task || this.data.isDone) return

    const notes = this.data.textNotes.map((n) => n.content).join('\n')
    const images = this.data.images.map((img) => img.url)

    try {
      this.setData({ loading: true })
      wx.showLoading({ title: '提交中...', mask: true })
      await post('/task/checkin', {
        task_id: task.id,
        notes,
        images,
      })
      wx.hideLoading()

      this.setData({
        isDone: true,
        statusLabel: TASK_STATUS_LABEL[TASK_STATUS.DONE],
        statusClass: 'status-done',
      })

      wx.showToast({ title: '打卡成功', icon: 'success' })

      const taskId = task.id
      const checklistKey = `checklist_${taskId}`
      try { wx.removeStorageSync(checklistKey) } catch (_) { /* ignore */ }

      setTimeout(() => {
        wx.navigateBack()
      }, 1200)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[task-detail] onMarkDone failed:`, msg)
      wx.hideLoading()
      wx.showToast({ title: msg || '提交失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})
