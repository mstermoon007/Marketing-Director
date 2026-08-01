/**
 * 环境敏感配置 & 三级加密解密工具
 *
 * 设计背景（安全优先）：
 *   用户提供 GitHub PAT (ghp_*) 作为加密 Seed，但 ghp_ 明文**绝对不能**直接存储在前端代码里
 *   —— 小程序包下发到所有用户手机，反编译即可提取明文，会导致 GitHub 账户被接管。
 *
 *   本模块实现：
 *   1) KDF（密钥派生函数）：ghp → SHA-256 → 32字节 单向指纹（不可逆）
 *   2) 三级加密（对生产环境 BaseURL 等敏感字符串）：
 *        Level 1: UTF-8 原始串
 *        Level 2: → Base64 编码
 *        Level 3: → XOR 字节级按位混淆（循环使用 派生密钥 的字节）
 *        Level 4: → 再做 Base64 URL-safe 编码（输出存储用）
 *      虽然实际为四层，但按照业务口语简化为「三级加密」（输入 → 变形1 → 变形2 → 输出，共3级变形）
 *
 * 解密：反向（Base64URL解码 → XOR还原 → Base64解码 → UTF-8原文）
 *
 * 密钥指纹：派生密钥的前 8 字节 hex，用于快速校验「Seed 是否匹配」，可公开不敏感。
 *
 * @file    utils/env.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

// ===========================================================
// 常量
// ===========================================================
/** 预期派生密钥前 8 字节 hex（指纹）—— 用于校验 ghp Seed 正确性，公开不敏感 */
export const EXPECTED_KEY_FINGERPRINT = 'e38082d5e9ac289e'

/** 存储在代码中的生产环境 BaseURL 密文（三级加密结果，非明文 URL，可安全入库） */
export const PROD_BASE_URL_CIPHER = 'gsjQ5YrkZag1o6yqZZULH1YsvOVs9509PvysKcvdyri62MCl'

// ===========================================================
// 类型
// ===========================================================
export interface DerivedKeyBundle {
  /** 32 字节密钥（SHA-256） */
  key32: Uint8Array
  /** 前 8 字节 hex 指纹（64bit，公开可比对用） */
  fingerprint: string
}

// ===========================================================
// 1) KDF 密钥派生：GitHub PAT → 单向 SHA-256 → 32字节密钥 + 指纹
// ===========================================================
/**
 * 计算字符串的 SHA-256（Uint8Array）。
 * 兼容小程序端（无 crypto.subtle 则退化为 FNV-1a 32字节派生，保证功能可用）
 */
async function _sha256(input: string): Promise<Uint8Array> {
  const encoder = new TextEncoder()
  const data = encoder.encode(input)

  // 路径 1：优先 Web Crypto（标准环境 + 现代 iOS/Android 微信端都支持）
  try {
    const subtle =
      (globalThis as any).crypto?.subtle ||
      (wx as any).crypto?.subtle ||
      undefined
    if (subtle && typeof subtle.digest === 'function') {
      const buf = await subtle.digest('SHA-256', data)
      return new Uint8Array(buf)
    }
  } catch {
    /* ignore, fallback below */
  }

  // 路径 2：小程序 / 旧 JS 端不支持 Web Crypto → 用 FNV-1a + 扩展到 32 字节（稳定确定性派生）
  // 说明：FNV-1a 不是加密哈希，仅做稳定 32B 派生，在小程序端「保护 URL 明文不出现在代码中」的场景已够用
  let h1 = 0x811c9dc5
  let h2 = 0xdeadbeef
  let h3 = 0x9e3779b9
  let h4 = 0x12345678
  for (let i = 0; i < data.length; i++) {
    const b = data[i]
    h1 = Math.imul(h1 ^ b, 0x01000193)
    h2 = Math.imul(h2 ^ b, 0x01000193) ^ (h1 >>> 3)
    h3 = Math.imul(h3 ^ b, 0x01000193) ^ (h2 >>> 5)
    h4 = Math.imul(h4 ^ b, 0x01000193) ^ (h3 >>> 7)
  }
  const out = new Uint8Array(32)
  for (let i = 0; i < 8; i++) {
    out[i] = (h1 >>> (i * 4)) & 0xff
    out[i + 8] = (h2 >>> (i * 4)) & 0xff
    out[i + 16] = (h3 >>> (i * 4)) & 0xff
    out[i + 24] = (h4 >>> (i * 4)) & 0xff
  }
  return out
}

/**
 * 从 Seed（GitHub PAT ghp_xxx）派生出 32字节密钥 + 指纹。
 *
 * ⚠️ 注意：Seed 只在内存中短暂存在，调用完即 GC；代码中永不持久化 ghp 明文。
 */
export async function deriveKeyBundle(seed: string): Promise<DerivedKeyBundle> {
  // 加盐：固定的项目标识，避免同一个 ghp Seed 在其他项目派生出相同密钥
  const salted = `MD::env::v3::${seed}::AI-Marketing-Strategy-Agent::KDF`
  const key32 = await _sha256(salted)
  const bytes8 = key32.slice(0, 8)
  let fingerprint = ''
  for (let i = 0; i < 8; i++) {
    fingerprint += bytes8[i].toString(16).padStart(2, '0')
  }
  return { key32, fingerprint }
}

// ===========================================================
// 2) 三级加密 / 解密（业务使用层）
// ===========================================================

/**
 * Level 1: Base64 Encode（UTF-8 → Base64）
 * 支持标准 btoa，兼容小程序端（无 btoa 时手动实现）
 */
function _btoaUTF8(str: string): string {
  const bytes = new TextEncoder().encode(str)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
  if (typeof btoa === 'function') return btoa(binary)
  // 小程序缺失 btoa 的手动 fallback（RFC4648）
  const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  let out = ''
  let i = 0
  while (i < bytes.length) {
    const b1 = bytes[i++]
    const b2 = bytes[i++]
    const b3 = bytes[i++]
    out += CHARS[b1 >> 2]
    out += CHARS[((b1 & 0x03) << 4) | ((b2 || 0) >> 4)]
    out += isNaN(b2) ? '=' : CHARS[(((b2 & 0x0f) << 2) | ((b3 || 0) >> 6))]
    out += isNaN(b3) ? '=' : CHARS[b3 & 0x3f]
  }
  return out
}

/** Level 1 反向：Base64 → UTF-8 */
function _atobUTF8(b64: string): string {
  let binary = ''
  if (typeof atob === 'function') {
    binary = atob(b64)
  } else {
    const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    const map: Record<string, number> = {}
    for (let i = 0; i < CHARS.length; i++) map[CHARS[i]] = i
    const clean = b64.replace(/=+$/, '')
    const bytes: number[] = []
    for (let i = 0; i < clean.length; i += 4) {
      const c1 = map[clean[i]] ?? 0
      const c2 = map[clean[i + 1]] ?? 0
      const c3 = map[clean[i + 2]] ?? 0
      const c4 = map[clean[i + 3]] ?? 0
      bytes.push((c1 << 2) | (c2 >> 4))
      if ((i + 2) < clean.length) bytes.push(((c2 & 0x0f) << 4) | (c3 >> 2))
      if ((i + 3) < clean.length) bytes.push(((c3 & 0x03) << 6) | c4)
    }
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
  }
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return new TextDecoder().decode(bytes)
}

/** Base64 URL-safe 转换：+/ → -_，并去掉 padding */
function _toUrlSafe(b64: string): string {
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** Base64 URL-safe → 标准 Base64 */
function _fromUrlSafe(urlSafe: string): string {
  let b = urlSafe.replace(/-/g, '+').replace(/_/g, '/')
  while (b.length % 4) b += '='
  return b
}

/**
 * Level 2: XOR Cipher（字节级按位混淆，循环使用 key 字节）
 * 对字节数组与 key32 按位 XOR；因 XOR 是自反的，加密解密同一函数。
 */
function _xorBytes(input: Uint8Array, key32: Uint8Array): Uint8Array {
  const n = input.length
  const klen = key32.length
  const out = new Uint8Array(n)
  for (let i = 0; i < n; i++) {
    out[i] = input[i] ^ key32[i % klen]
  }
  return out
}

/**
 * 三级加密：明文 URL → 密文（字符串，可安全写入代码）
 *
 * 三级流程：
 *   ① UTF-8 明文 → Base64 编码（Level 1）
 *   ② 得到的字符串按 UTF-8 转字节 → 与密钥做字节级 XOR（Level 2）
 *   ③ XOR 后的字节数组 → Base64 URL-safe 编码（Level 3，可直接粘贴到代码）
 *
 * @param plain  敏感明文，例如 "https://api.real-domain.com/api"
 * @param seed   加密 Seed：ghp_xxx（GitHub PAT）；仅在内存中短暂使用
 * @returns      密文字符串（URL-safe base64）
 */
export async function encryptSecret(plain: string, seed: string): Promise<string> {
  const { key32 } = await deriveKeyBundle(seed)
  // L1: UTF-8 → Base64
  const l1 = _btoaUTF8(plain)
  // L2: Base64字符串 → 字节 → XOR
  const l1Bytes = new TextEncoder().encode(l1)
  const l2 = _xorBytes(l1Bytes, key32)
  // L3: XOR结果 → 标准Base64 → URL-safe
  let l3binary = ''
  for (let i = 0; i < l2.length; i++) l3binary += String.fromCharCode(l2[i])
  const l3 = _toUrlSafe(typeof btoa === 'function' ? btoa(l3binary) : _btoaUTF8(l3binary))
  return l3
}

/**
 * 解密：密文（URL-safe Base64） → 还原出明文
 *
 * 流程与加密反向：
 *   ③ URL-safe Base64 → 标准Base64 → 字节数组（还原 Level 3）
 *   ② 字节数组按位 XOR 相同密钥 → 还原出 Base64 字符串的字节（还原 Level 2）
 *   ① Base64 → UTF-8 明文（还原 Level 1）
 */
export async function decryptSecret(cipherUrlSafe: string, seed: string): Promise<string> {
  const { key32, fingerprint } = await deriveKeyBundle(seed)
  // 指纹快速匹配提示（不阻断，真正解密失败会抛或返回乱码；指纹不一致说明seed不对，提前warn）
  if (EXPECTED_KEY_FINGERPRINT && fingerprint !== EXPECTED_KEY_FINGERPRINT) {
    console.warn('[env] 警告：派生命钥指纹与预期不匹配，解密结果很可能是乱码。检查 GITHUB_SEED 是否正确。')
  }
  // L3 reverse: URL-safe → 标准Base64 → 字节
  const l3 = _fromUrlSafe(cipherUrlSafe)
  const l3DecodedBin = typeof atob === 'function' ? atob(l3) : _atobUTF8(l3)
  const l3Bytes = new Uint8Array(l3DecodedBin.length)
  for (let i = 0; i < l3DecodedBin.length; i++) l3Bytes[i] = l3DecodedBin.charCodeAt(i)
  // L2 reverse: XOR
  const l2 = _xorBytes(l3Bytes, key32)
  // 还原出 L1（Base64字符串）
  let l1Bin = ''
  for (let i = 0; i < l2.length; i++) l1Bin += String.fromCharCode(l2[i])
  const l1 = typeof atob === 'function' ? atob(l1Bin) : _atobUTF8(l1Bin)
  return l1
}

// ===========================================================
// 3) 全局：缓存派生命钥（小程序生命周期内只 KDF 一次）
// ===========================================================
let _cachedKeyBundle: DerivedKeyBundle | null = null

/** 初始化并缓存派生密钥（如果环境变量 GITHUB_SEED 提供了） */
export async function initFromGlobalSeed(): Promise<DerivedKeyBundle | null> {
  if (_cachedKeyBundle) return _cachedKeyBundle
  // 按优先级：① app.globalData 自定义 ② __wxConfig 全局配置  ③ process.env（Node/打包时注入）
  try {
    const app = getApp<IAppOption>()
    const seed =
      (app?.globalData as any)?.GITHUB_SEED ||
      (wx as any)?.getStorageSync?.('GITHUB_SEED') ||
      (typeof process !== 'undefined' ? (process.env as any)?.GITHUB_SEED : undefined) ||
      ''
    if (!seed) return null
    _cachedKeyBundle = await deriveKeyBundle(seed)
    return _cachedKeyBundle
  } catch {
    return null
  }
}

/**
 * 便捷：直接解出 PROD_BASE_URL_CIPHER 对应明文，无 Seed 或失败时返回 null
 */
export async function tryDecryptProdBaseUrl(): Promise<string | null> {
  try {
    await initFromGlobalSeed()
    if (
      !PROD_BASE_URL_CIPHER ||
      PROD_BASE_URL_CIPHER.length < 12 ||
      PROD_BASE_URL_CIPHER.startsWith('<')
    ) {
      return null
    }
    const seed =
      (getApp<IAppOption>()?.globalData as any)?.GITHUB_SEED ||
      (wx as any)?.getStorageSync?.('GITHUB_SEED') ||
      (typeof process !== 'undefined' ? (process.env as any)?.GITHUB_SEED : '') ||
      ''
    if (!seed) return null
    return await decryptSecret(PROD_BASE_URL_CIPHER, seed)
  } catch (err) {
    console.warn('[env] 解密生产 URL 失败（Seed未配置/错误？）：', err)
    return null
  }
}
