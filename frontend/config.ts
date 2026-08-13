/**
 * 环境配置集中管理（V3.5）
 *
 * 微信小程序不支持传统 .env 文件，采用以下优先级读取开发环境配置：
 *   1. Storage(md:dev_api_base) — 持久化，换网络时只需改一次
 *   2. globalData.DEV_API_BASE — app.ts onLaunch 注入
 *   3. 本文件默认值（localhost）— 仅开发工具模拟器可用
 *
 * 首次使用 / 换网络环境时，在开发者工具 Console 执行：
 *   wx.setStorageSync('md:dev_api_base', 'http://你的本机IP:8000/api')
 *
 * 查看本机 IP：
 *   macOS: ifconfig | grep "inet " | grep -v 127.0.0.1
 *
 * @file    config.ts
 * @author  AI Marketing Team
 * @version 3.5.0
 */

import { STORAGE_KEYS } from './utils/storage'

// ======================== 环境默认配置 ========================
/** 开发环境后端端口（需与后端 uvicorn --port 保持一致） */
export const DEV_PORT = 8000

/**
 * 云端 CloudRun 公网地址（仅生产/体验版 bootstrap 用）。
 *
 * ⚠️ 不能为空：正式版（release）首次启动尚无登录态时，getBase() 只能依赖本地址
 * 发出第一次 /auth/login；若为空，微信一键登录在正式版会直接不可用（鸡生蛋问题）。
 *
 * 注意：本地址【仅】用于生产/体验版引导。开发版（develop）默认走 DEV_DEFAULT_URL（本地后端），
 * 不再默认指向此处，以免开发/联调数据误写生产库（后端按 APP_ENV 分库：prod → app_prod.db）。
 */
export const PROD_DEFAULT_URL: string =
  'https://marketing-agent-295298-11-1466398119.sh.run.tcloudbase.com/api'

/**
 * 开发环境默认 API 地址 —— 必须与生产地址解耦，绝不指向 PROD_DEFAULT_URL。
 *
 * 旧实现 `DEV_DEFAULT_URL = PROD_DEFAULT_URL` 会让开发/联调数据默认写进生产库
 * （生产部署 APP_ENV=production → app_prod.db），属数据隔离漏洞。
 *
 * 这里默认指向本地后端（端口见 DEV_PORT=8000，需本地 `uvicorn --port 8000` 或 Docker 起服务）。
 * 如需连云端开发后端，在开发者工具 Console 执行一次即可持久化覆盖：
 *   wx.setStorageSync('md:dev_api_base', 'https://你的-dev-cloudrun/api')
 * 真机/模拟器连本机后端请用局域网 IP（非 localhost）。
 * resolveDevBaseUrl 优先级：Storage(md:dev_api_base) → globalData.DEV_API_BASE → 本默认值。
 */
export const DEV_DEFAULT_URL: string = 'http://localhost:8000/api'

// ======================== 运行时解析 ========================
/**
 * 获取当前有效的 Dev BaseURL
 * 优先级：Storage → globalData → 本文件默认值
 */
export function resolveDevBaseUrl(): string {
  // 1. Storage 持久化配置（最高优先级）
  try {
    const stored = (wx as any)?.getStorageSync?.(STORAGE_KEYS.DEV_API_BASE)
    if (stored && /^https?:\/\//.test(stored)) return stored
  } catch { /* ignore */ }

  // 2. globalData 运行时注入
  try {
    const app = getApp<IAppOption>()
    const g = (app?.globalData as any)?.DEV_API_BASE
    if (g && /^https?:\/\//.test(g)) return g
  } catch { /* ignore */ }

  // 3. 默认值
  return DEV_DEFAULT_URL
}