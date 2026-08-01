/**
 * 雷达图组件，SVG绘制五维营销能力分布图
 *
 * @file    index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

interface RadarScores {
  positioning: number
  product: number
  channel: number
  content: number
  conversion: number
}

interface Dimension {
  key: string
  name: string
  score: number
  angleDeg: number
  angleRad: number
  color: string
  labelX: number
  labelY: number
  axisEndX: number
  axisEndY: number
}

interface DataPoint {
  x: number
  y: number
  score: number
}

interface RadarChartProperties {
  scores: RadarScores
}

interface RadarChartData {
  dimensions: Dimension[]
  gridLevels: number[]
  gridPolygons: string[]
  scorePolygonPoints: string
  dataPoints: DataPoint[]
}

type RadarScoreKey = keyof RadarScores

interface DimensionConfig {
  key: RadarScoreKey
  name: string
  angleDeg: number
  color: string
}

const DIMENSION_CONFIG: DimensionConfig[] = [
  { key: 'positioning', name: '定位', angleDeg: 90, color: '#1989fa' },
  { key: 'product', name: '产品', angleDeg: 18, color: '#07c160' },
  { key: 'channel', name: '渠道', angleDeg: -54, color: '#ff976a' },
  { key: 'content', name: '内容', angleDeg: -126, color: '#7232dd' },
  { key: 'conversion', name: '转化', angleDeg: -198, color: '#ee0a24' },
]

const MAX_RADIUS = 80
const LABEL_OFFSET = 16
const GRID_LEVELS: number[] = [25, 50, 75, 100]

/**
 * 角度转换：度数 -> 弧度
 *
 * @param deg 角度值
 * @returns 弧度值
 */
function degToRad(deg: number): number {
  return (deg * Math.PI) / 180
}

interface CartesianPoint {
  x: number
  y: number
}

/**
 * 极坐标转直角坐标（SVG坐标系，Y轴向下为正）
 *
 * @param radius 半径
 * @param angleRad 弧度角
 * @returns 直角坐标点 { x, y }
 */
function polarToCartesian(radius: number, angleRad: number): CartesianPoint {
  const x = radius * Math.cos(angleRad)
  const y = -radius * Math.sin(angleRad)
  return { x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 }
}

/**
 * 构建多边形SVG点串
 *
 * @param radius 半径
 * @returns SVG polygon points 属性值
 */
function buildPolygonPoints(radius: number): string {
  return DIMENSION_CONFIG.map((cfg: DimensionConfig): string => {
    const { x, y } = polarToCartesian(radius, degToRad(cfg.angleDeg))
    return `${x},${y}`
  }).join(' ')
}

/**
 * 归一化分数到 0-100 安全范围
 *
 * @param scores 原始分数
 * @returns 安全分数对象
 */
function sanitizeScores(scores: RadarScores): RadarScores {
  return {
    positioning: Math.max(0, Math.min(100, Number(scores?.positioning) ?? 0)),
    product: Math.max(0, Math.min(100, Number(scores?.product) ?? 0)),
    channel: Math.max(0, Math.min(100, Number(scores?.channel) ?? 0)),
    content: Math.max(0, Math.min(100, Number(scores?.content) ?? 0)),
    conversion: Math.max(0, Math.min(100, Number(scores?.conversion) ?? 0)),
  }
}

interface RadarComputedResult {
  dimensions: Dimension[]
  gridPolygons: string[]
  scorePolygonPoints: string
  dataPoints: DataPoint[]
}

/**
 * 计算雷达图全部绘制数据
 *
 * @param scores 维度得分
 * @returns 渲染所需的完整数据集
 */
function computeRadarData(scores: RadarScores): RadarComputedResult {
  const safeScores = sanitizeScores(scores)

  const gridPolygons: string[] = GRID_LEVELS.map((pct: number): string => {
    const r = (MAX_RADIUS * pct) / 100
    return buildPolygonPoints(r)
  })

  const scorePoints: CartesianPoint[] = DIMENSION_CONFIG.map((cfg: DimensionConfig): CartesianPoint => {
    const score = safeScores[cfg.key]
    const r = (MAX_RADIUS * score) / 100
    const rad = degToRad(cfg.angleDeg)
    return polarToCartesian(r, rad)
  })

  const scorePolygonPoints: string = scorePoints.map((p: CartesianPoint): string => `${p.x},${p.y}`).join(' ')

  const dataPoints: DataPoint[] = scorePoints.map((p: CartesianPoint, i: number): DataPoint => ({
    ...p,
    score: safeScores[DIMENSION_CONFIG[i].key],
  }))

  const dimensions: Dimension[] = DIMENSION_CONFIG.map((cfg: DimensionConfig): Dimension => {
    const rad = degToRad(cfg.angleDeg)
    const axisEnd = polarToCartesian(MAX_RADIUS, rad)
    const labelPos = polarToCartesian(MAX_RADIUS + LABEL_OFFSET, rad)
    return {
      key: cfg.key,
      name: cfg.name,
      score: safeScores[cfg.key],
      angleDeg: cfg.angleDeg,
      angleRad: rad,
      color: cfg.color,
      labelX: labelPos.x,
      labelY: labelPos.y,
      axisEndX: axisEnd.x,
      axisEndY: axisEnd.y,
    }
  })

  return {
    dimensions,
    gridPolygons,
    scorePolygonPoints,
    dataPoints,
  }
}

Component<RadarChartProperties, RadarChartData, { computeRadarData: (scores: RadarScores) => void }>({
  properties: {
    scores: {
      type: Object,
      value: {
        positioning: 0,
        product: 0,
        channel: 0,
        content: 0,
        conversion: 0,
      },
    },
  },

  data: {
    dimensions: [] as Dimension[],
    gridLevels: GRID_LEVELS,
    gridPolygons: [] as string[],
    scorePolygonPoints: '',
    dataPoints: [] as DataPoint[],
  },

  observers: {
    scores: function (scores: RadarScores): void {
      this.computeRadarData(scores)
    },
  },

  lifetimes: {
    attached: function (): void {
      this.computeRadarData(this.properties.scores as RadarScores)
    },
  },

  methods: {
    /**
     * 计算并更新雷达图数据
     *
     * @param scores 维度得分
     */
    computeRadarData(scores: RadarScores): void {
      this.setData(computeRadarData(scores))
    },
  },
})
