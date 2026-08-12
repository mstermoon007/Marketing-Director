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
 * 云端 CloudRun 公网地址（生产 bootstrap，同时作为开发环境兜底）。
 *
 * ⚠️ 不能为空：正式版（release）首次启动时尚未有登录态，getBase() 只能依赖本地址
 * 才能发出第一次 /auth/login 请求；若为空，getBase() 会直接抛错，导致「微信一键登录」
 * 在正式版完全不可用（鸡生蛋问题）。
 *
 * 开发工具模拟器在「探测不到本机局域网 IP / 本机没起后端」时也会回退到这里，
 * 避免硬编码错误 LAN IP（如 192.168.0.105）导致 502、登录永远失败。
 * 如需纯本地开发，用 Console 执行 wx.setStorageSync('md:dev_api_base', 'http://你的IP:8000/api') 覆盖即可。
 * 路径需带 /api，因为请求封装为 base + opts.url（如 /auth/login）。
 */
export const PROD_DEFAULT_URL: string =
  'https://marketing-agent-295298-11-1466398119.sh.run.tcloudbase.com/api'

/**
 * 开发环境默认 API 地址。
 * 默认直连云端 CloudRun（开箱即用，无需本地起后端，已验证可达且 0.5s 内响应）；
 * 如需本地联调，用 Console 执行：
 *   wx.setStorageSync('md:dev_api_base', 'http://本机IP:8000/api')
 * 即可覆盖本默认值（resolveDevBaseUrl 优先读 Storage）。
 *
 * 注：原先的「自动探测局域网 IP」方案会命中一个没有后端的 IP，导致
 * /auth/login 出现 502 / 超时、登录永远失败、界面卡在启动，故弃用。
 */
export const DEV_DEFAULT_URL = PROD_DEFAULT_URL

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