/**
 * 阶段时间线组件，展示三阶段12周进度与关键动作
 *
 * @file    index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { PhaseItem } from '../../types/index'

import { PHASES, weekToPhaseIndex } from '../../utils/date'

interface PhaseTimelineProperties {
  currentWeek: number
  phases: PhaseItem[]
}

interface ActionStatus {
  text: string
  icon: string
}

interface DisplayPhase extends PhaseItem {
  isCurrent: boolean
  isCompleted: boolean
  isPending: boolean
  actionsWithStatus: ActionStatus[]
}

interface PhaseTimelineData {
  currentPhaseIndex: number
  displayPhases: DisplayPhase[]
}

const MAX_WEEK = 12
const MIN_WEEK = 1

/**
 * 将默认PHASES转换为PhaseItem格式
 *
 * @returns PhaseItem数组
 */
function buildDefaultPhaseItems(): PhaseItem[] {
  return PHASES.map((p): PhaseItem => ({
    phase_index: p.index,
    phase_name: p.name,
    weeks_cover: p.weeksCover,
    key_actions: p.keyActions,
    success_criteria: p.successCriteria,
  }))
}

interface PhaseComputeResult {
  currentPhaseIndex: number
  displayPhases: DisplayPhase[]
}

/**
 * 计算阶段显示数据
 *
 * @param currentWeek 当前周数
 * @param phases 阶段数据（为空时使用默认）
 * @returns 显示数据
 */
function computeDisplayData(currentWeek: number, phases: PhaseItem[]): PhaseComputeResult {
  const inputPhases: PhaseItem[] = phases?.length > 0 ? phases : buildDefaultPhaseItems()
  const safeWeek = Math.max(MIN_WEEK, Math.min(MAX_WEEK, currentWeek ?? MIN_WEEK))
  const currentPhaseIndex = weekToPhaseIndex(safeWeek)

  const displayPhases: DisplayPhase[] = inputPhases.map((phase: PhaseItem): DisplayPhase => {
    const idx = phase.phase_index
    const isCurrent = idx === currentPhaseIndex
    const isCompleted = idx < currentPhaseIndex
    const isPending = idx > currentPhaseIndex

    let icon = '⬜'
    if (isCompleted) icon = '✅'
    if (isCurrent) icon = '🔄'

    const actionsWithStatus: ActionStatus[] = (phase.key_actions ?? []).map((text: string): ActionStatus => ({
      text,
      icon,
    }))

    return {
      ...phase,
      isCurrent,
      isCompleted,
      isPending,
      actionsWithStatus,
    }
  })

  return {
    currentPhaseIndex,
    displayPhases,
  }
}

Component<PhaseTimelineProperties, PhaseTimelineData, { computeDisplayData: (currentWeek: number, phases: PhaseItem[]) => void }>({
  properties: {
    currentWeek: {
      type: Number,
      value: 1,
    },
    phases: {
      type: Array,
      value: [],
    },
  },

  data: {
    currentPhaseIndex: 1,
    displayPhases: [] as DisplayPhase[],
  },

  observers: {
    'currentWeek, phases': function (currentWeek: number, phases: PhaseItem[]): void {
      this.computeDisplayData(currentWeek, phases)
    },
  },

  lifetimes: {
    attached: function (): void {
      this.computeDisplayData(this.properties.currentWeek, this.properties.phases)
    },
  },

  methods: {
    /**
     * 计算并更新阶段显示数据
     *
     * @param currentWeek 当前周数
     * @param phases 阶段数据
     */
    computeDisplayData(currentWeek: number, phases: PhaseItem[]): void {
      this.setData(computeDisplayData(currentWeek, phases))
    },
  },
})
