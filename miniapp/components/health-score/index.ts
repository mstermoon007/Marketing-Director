/**
 * 健康度评分组件，展示总评分与各维度得分
 *
 * @file    index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

interface DimensionScore {
  key: string
  name: string
  score: number
  color: string
}

interface HealthScoreProperties {
  overallScore: number
  overallComment: string
  dimensionScores: Record<string, number>
}

interface HealthScoreData {
  scoreColor: string
  sortedDimensions: DimensionScore[]
  ringOffset: number
}

const DIMENSION_NAMES: Record<string, string> = {
  positioning: '定位精准度',
  product: '产品竞争力',
  channel: '渠道覆盖度',
  content: '内容吸引力',
  conversion: '转化效率',
}

const DIMENSION_ORDER: string[] = ['positioning', 'product', 'channel', 'content', 'conversion']

const RING_CIRCUMFERENCE = 2 * Math.PI * 120

/**
 * 根据分数获取颜色
 *
 * @param score 分数 0-100
 * @returns CSS颜色变量
 */
function getScoreColor(score: number): string {
  if (score < 60) return 'var(--color-danger)'
  if (score < 80) return 'var(--color-warning)'
  return 'var(--color-success)'
}

/**
 * 计算环形进度条offset
 *
 * @param score 分数 0-100
 * @returns SVG stroke-dashoffset
 */
function computeRingOffset(score: number): number {
  const progress = Math.min(100, Math.max(0, score)) / 100
  return RING_CIRCUMFERENCE * (1 - progress)
}

/**
 * 构建维度排序后的得分数据
 *
 * @param dimensionScores 维度得分原始数据
 * @returns 排序后的维度得分数组
 */
function buildSortedDimensions(dimensionScores: Record<string, number>): DimensionScore[] {
  return DIMENSION_ORDER.map((key: string): DimensionScore => {
    const score = dimensionScores[key] ?? 0
    return {
      key,
      name: DIMENSION_NAMES[key] ?? key,
      score: Math.min(100, Math.max(0, score)),
      color: getScoreColor(score),
    }
  })
}

Component<HealthScoreProperties, HealthScoreData, WechatMiniprogram.IAnyObject>({
  properties: {
    overallScore: {
      type: Number,
      value: 0,
    },
    overallComment: {
      type: String,
      value: '营销健康度评分中...',
    },
    dimensionScores: {
      type: Object,
      value: {} as Record<string, number>,
    },
  },

  data: {
    scoreColor: 'var(--color-text-secondary)',
    sortedDimensions: [] as DimensionScore[],
    ringOffset: 0,
  },

  observers: {
    overallScore: function (overallScore: number): void {
      const scoreColor = getScoreColor(overallScore)
      const ringOffset = computeRingOffset(overallScore)
      this.setData({ scoreColor, ringOffset })
    },

    dimensionScores: function (dimensionScores: Record<string, number>): void {
      const sortedDimensions = buildSortedDimensions(dimensionScores)
      this.setData({ sortedDimensions })
    },
  },

  lifetimes: {
    attached(): void {
      const { overallScore, dimensionScores } = this.properties
      const scoreColor = getScoreColor(overallScore)
      const ringOffset = computeRingOffset(overallScore)
      const sortedDimensions = buildSortedDimensions(dimensionScores)
      this.setData({ scoreColor, ringOffset, sortedDimensions })
    },
  },
})
