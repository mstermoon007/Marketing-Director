/**
 * 运行环境判定（develop/trial -> dev，release -> prod）
 *
 * 与后端 APP_ENV 对应：dev 走开发库、prod 走生产库。
 * 同时供 utils/storage 为本地缓存按环境加命名空间前缀，隔离开发/生产数据。
 *
 * 本模块不依赖其它业务模块，避免循环引用。
 */

/** 旧占位符域名（生产校验：命中则判定为未配置） */
export const PLACEHOLDER_DOMAIN = 'example.com'

export type EnvKind = 'dev' | 'prod'

export function detectEnvKind(): EnvKind {
  try {
    const app = getApp<IAppOption>()
    // 1) 显式 apiBase（兼容老代码，优先级最高，排除占位符域名）
    if (
      app?.globalData?.apiBase &&
      !app.globalData.apiBase.includes(PLACEHOLDER_DOMAIN) &&
      /^https?:\/\//.test(app.globalData.apiBase)
    ) {
      return 'dev'
    }
    // 2) 微信官方 envVersion 判断
    const envVer = (wx as any)?.getAccountInfoSync?.()?.miniProgram?.envVersion
    if (envVer === 'release') return 'prod'
    return 'dev'
  } catch {
    return 'dev'
  }
}
