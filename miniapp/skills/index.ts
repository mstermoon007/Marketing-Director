/**
 * 技能模块 — 行业技能调用 v2
 * 参考开发思路文档：技能模块 — 按行业分类存储营销知识
 *
 * 功能：
 * - 提供行业技能映射表
 * - 地产行业支持细分（二手房中介/新房代理/商铺租赁等）
 * - 在诊断前根据行业匹配对应的技能标签
 * - 支持获取行业建议内容用于展示
 */

/** 行业技能映射（地产为核心，支持子类细分） */
export const INDUSTRY_SKILLS: Record<string, { key: string; label: string; icon: string; category: string }> = {
  // ── 地产行业（核心）──
  '地产': { key: 'real_estate', label: '地产', icon: '🏢', category: 'real_estate' },
  '房地产': { key: 'real_estate', label: '地产', icon: '🏢', category: 'real_estate' },
  '房产': { key: 'real_estate', label: '地产', icon: '🏢', category: 'real_estate' },
  '房产中介': { key: 'real_estate', label: '房产中介', icon: '🏠', category: 'real_estate' },
  '房产经纪': { key: 'real_estate', label: '房产经纪', icon: '📋', category: 'real_estate' },
  '中介': { key: 'real_estate', label: '房产中介', icon: '🏠', category: 'real_estate' },
  '地产经纪': { key: 'real_estate', label: '地产经纪', icon: '📊', category: 'real_estate' },
  '置业顾问': { key: 'real_estate', label: '置业顾问', icon: '🏢', category: 'real_estate' },
  '二手房中介': { key: 'real_estate', label: '二手房中介', icon: '🏠', category: 'real_estate' },
  '新房代理': { key: 'real_estate', label: '新房代理', icon: '🏗️', category: 'real_estate' },
  '商铺租赁': { key: 'real_estate', label: '商铺租赁', icon: '🏪', category: 'real_estate' },
  '综合地产': { key: 'real_estate', label: '综合地产', icon: '🏢', category: 'real_estate' },

  // ── 其他行业（暂不深化）──
  '家装': { key: 'renovation', label: '家装', icon: '🔨', category: 'other' },
  '装修': { key: 'renovation', label: '家装', icon: '🔨', category: 'other' },
  '装饰': { key: 'renovation', label: '家装', icon: '🔨', category: 'other' },
  '装潢': { key: 'renovation', label: '家装', icon: '🔨', category: 'other' },
  '室内设计': { key: 'renovation', label: '家装', icon: '🔨', category: 'other' },
  '餐饮': { key: 'restaurant', label: '餐饮', icon: '🍽️', category: 'other' },
  '餐厅': { key: 'restaurant', label: '餐饮', icon: '🍽️', category: 'other' },
  '饭店': { key: 'restaurant', label: '餐饮', icon: '🍽️', category: 'other' },
  '美食': { key: 'restaurant', label: '餐饮', icon: '🍽️', category: 'other' },
  '教培': { key: 'education', label: '教育培训', icon: '📚', category: 'other' },
  '培训': { key: 'education', label: '教育培训', icon: '📚', category: 'other' },
  '教育': { key: 'education', label: '教育培训', icon: '📚', category: 'other' },
  '美容': { key: 'beauty', label: '美业', icon: '💄', category: 'other' },
  '美发': { key: 'beauty', label: '美业', icon: '💇', category: 'other' },
  '美业': { key: 'beauty', label: '美业', icon: '💄', category: 'other' },
  '其他': { key: 'generic', label: '通用行业', icon: '💡', category: 'other' },
  '其它': { key: 'generic', label: '通用行业', icon: '💡', category: 'other' },
}

/** 地产行业子类选项（用于表单选择） */
export const REAL_ESTATE_SUBCATEGORIES = [
  { value: '二手房中介', label: '二手房中介', icon: '🏠', desc: '主营二手房买卖中介服务' },
  { value: '新房代理', label: '新房代理', icon: '🏗️', desc: '代理新房销售、楼盘分销' },
  { value: '商铺租赁', label: '商铺租赁', icon: '🏪', desc: '商铺、写字楼租赁服务' },
  { value: '综合地产', label: '综合地产', icon: '🏢', desc: '综合型地产经纪服务' },
]

/** 行业诊断建议（前端展示用） */
export const INDUSTRY_DIAGNOSIS_TIPS: Record<string, string[]> = {
  real_estate: [
    '【房源获取】打造独家房源体系，老业主回访+业主群深耕',
    '【带看转化】带看前充分了解客户需求，带看后2小时内跟进',
    '【社区渗透】维护3-5个服务小区的业主群，提供房产咨询价值',
    '【线上获客】每周3-5条短视频（实景看房+区域分析），建立专业人设',
    '【数据运营】建立客户管理表，每周复盘带看量、成交量、转化率',
  ],
  renovation: [
    '展示施工过程和案例对比图，在短视频平台获客',
    '老客户转介绍是成本最低的获客方式',
    '注重报价透明和合同细节，建立客户信任',
  ],
  restaurant: [
    '做好本地生活平台（美团/大众点评）的店铺页面',
    '建立顾客微信群，定期推送优惠活动',
    '拍摄菜品制作过程的短视频，吸引自然流量',
  ],
  education: [
    '发布知识类短视频，吸引精准家长关注',
    '免费资料包引流，建立私域转化链路',
    '整理学员成功案例，作为核心营销素材',
  ],
  beauty: [
    '小红书是核心获客渠道，坚持发布前后对比案例',
    '打造技师个人IP，用朋友圈展示日常作品',
    '设计"闺蜜同行"等转介绍激励方案',
  ],
  generic: [
    '选择1-2个核心获客渠道，先跑通再扩展',
    '坚持内容输出，建立线上存在感',
    '系统化管理客户信息，跟进转化',
  ],
}

/** 地产行业诊断维度说明（用于诊断报告展示） */
export const REAL_ESTATE_DIAGNOSIS_DIMENSIONS = [
  { key: '房源获取', icon: '🔑', desc: '独家房源占比、业主关系维护' },
  { key: '带看转化', icon: '👁️', desc: '带看成功率、客户跟进效率' },
  { key: '社区渗透', icon: '🏘️', desc: '业主群覆盖、转介绍比例' },
  { key: '线上获客', icon: '📱', desc: '短视频/小红书/私域运营' },
  { key: '专业形象', icon: '⭐', desc: '专业知识、口碑评价' },
  { key: '数据运营', icon: '📊', desc: '客户管理、指标监控' },
]

/** 已注册的技能类型 */
export type SkillKey = keyof typeof INDUSTRY_DIAGNOSIS_TIPS

/**
 * 根据行业名称获取技能信息
 */
export function getIndustrySkill(industry: string): { key: SkillKey; label: string; icon: string; category: string } {
  if (!industry) {
    return { key: 'generic', label: '通用行业', icon: '💡', category: 'other' }
  }

  const skill = INDUSTRY_SKILLS[industry]
  if (skill) {
    return skill
  }

  for (const [alias, info] of Object.entries(INDUSTRY_SKILLS)) {
    if (industry.includes(alias) || alias.includes(industry)) {
      return info
    }
  }

  return { key: 'generic', label: '通用行业', icon: '💡', category: 'other' }
}

/**
 * 获取行业诊断建议
 */
export function getDiagnosisTips(industry: string): string[] {
  const skill = getIndustrySkill(industry)
  return INDUSTRY_DIAGNOSIS_TIPS[skill.key] || INDUSTRY_DIAGNOSIS_TIPS.generic
}

/**
 * 获取诊断时注入的技能上下文
 */
export function getSkillContext(industry: string): string {
  const skill = getIndustrySkill(industry)
  return `industry_skill=${skill.key}`
}

/**
 * 生成诊断前的准备信息
 */
export function prepareDiagnosisWithSkill(industry: string) {
  const skill = getIndustrySkill(industry)
  const tips = getDiagnosisTips(industry)

  return {
    skillKey: skill.key,
    skillLabel: skill.label,
    skillIcon: skill.icon,
    skillCategory: skill.category,
    tips,
    context: getSkillContext(industry),
  }
}

/**
 * 列出所有可用的行业分类（用于表单下拉选择）
 */
export function listIndustryOptions(): { value: string; label: string; icon: string }[] {
  const seen = new Set<string>()
  const options: { value: string; label: string; icon: string }[] = []

  for (const [value, info] of Object.entries(INDUSTRY_SKILLS)) {
    if (!seen.has(info.label)) {
      seen.add(info.label)
      options.push({ value, label: info.label, icon: info.icon })
    }
  }

  return options
}

/**
 * 获取地产行业子类选项
 */
export function listRealEstateSubcategories() {
  return REAL_ESTATE_SUBCATEGORIES
}

/**
 * 获取地产诊断维度列表
 */
export function getRealEstateDimensions() {
  return REAL_ESTATE_DIAGNOSIS_DIMENSIONS
}

/**
 * 判断是否为地产行业
 */
export function isRealEstate(industry: string): boolean {
  return getIndustrySkill(industry).key === 'real_estate'
}
