#!/usr/bin/env node
/*
 * ============================================================
 * scripts/encrypt-prod-url.js
 * ============================================================
 * 运维脚本：把「真实生产域名」加密成可直接粘贴进 miniapp/utils/env.ts 的密文
 *
 * ⚠️  用法：
 *   cd <project>
 *   GH_SEED="ghp_xxx"   \
 *   PLAIN_URL="https://your-real-server.example.com/api" \
 *   node scripts/encrypt-prod-url.js
 *
 *   ✅ 脚本会同时输出
 *      EXPECTED_KEY_FINGERPRINT 和 PROD_BASE_URL_CIPHER
 *   ✅ 把它们复制粘贴到 miniapp/utils/env.ts 的对应两个 const 即可
 *   ✅ 解密逻辑与 miniapp/utils/env.ts 算法 100% 一致，不可修改 KDF 盐值或加顺序
 *   ✅ Seed 永远不会写进代码库里（只能注入到环境变量里）
 * ============================================================
 */
const crypto = require('crypto');

const SEED = process.env.GH_SEED || process.env.GITHUB_SEED || process.env.GITHUB_PAT;
const PLAIN = process.env.PLAIN_URL || process.env.PROD_URL;

if (!SEED) {
  console.error('❌ 请先设置 Seed 环境变量：');
  console.error('   export GH_SEED="ghp_your_github_pat"');
  console.error('   export PLAIN_URL="https://real-server.your-domain.com/api"');
  process.exit(2);
}

if (!PLAIN || PLAIN.length < 12) {
  console.error('❌ PLAIN_URL 看起来是空的或太短了');
  console.error('   export PLAIN_URL="https://real-server.your-domain.com/api"');
  process.exit(2);
}

if (PLAIN.includes('example.com')) {
  console.warn('⚠️  警告：PLAIN_URL 里仍然是占位符 example.com，加密后小程序 release 版仍会被 request.ts 判定为无效');
  console.warn('    请替换成真实生产域名后再运行本脚本');
}

if (!/^https:\/\/[a-z0-9.-]+(:\d+)?(\/.*)?$/i.test(PLAIN)) {
  console.warn('⚠️  PLAIN_URL 不是标准 HTTPS URL（不是以 https:// 开头）');
  console.warn('    发布后会被 request.ts 校验拦截，请检查');
}

/* ============ 和 miniapp/utils/env.ts 保持 100% 同算法（绝对不要改，改了解出来就解不回去了 ============ */
const KDF_SALT_PREFIX = 'MD::env::v3::';
const KDF_SALT_SUFFIX = '::AI-Marketing-Strategy-Agent::KDF';

const salted = KDF_SALT_PREFIX + SEED + KDF_SALT_SUFFIX;
const key32 = crypto.createHash('sha256').update(salted, 'utf8').digest();
const fingerprint = key32.slice(0, 8).toString('hex');

// L1: UTF-8 plaintext → standard Base64
const l1 = Buffer.from(PLAIN, 'utf8').toString('base64');

// L2: L1 bytes XOR key32 (wrap
const l1Bytes = Buffer.from(l1, 'utf8');
const l2 = Buffer.allocUnsafe(l1Bytes.length);
for (let i = 0; i < l1Bytes.length; i++) {
  l2[i] = l1Bytes[i] ^ key32[i % 32];
}

// L3: L2 bytes → Base64 → URL-safe (去掉尾部=）
const l3 = l2
  .toString('base64')
  .replace(/\+/g, '-')
  .replace(/\//g, '_')
  .replace(/=+$/, '');

/* ============ 自检解密 double-check ============ */
const l3Restored = l3.replace(/-/g, '+').replace(/_/g, '/');
const pad = (4 - (l3Restored.length % 4)) % 4;
const l3Buf = Buffer.from(l3Restored + '='.repeat(pad), 'base64');
const l2Dec = Buffer.alloc(l3Buf.length);
for (let i = 0; i < l3Buf.length; i++) l2Dec[i] = l3Buf[i] ^ key32[i % 32];
const l1Dec = l2Dec.toString('utf8');
const plainDec = Buffer.from(l1Dec, 'base64').toString('utf8');
const match = plainDec === PLAIN;

console.log('');
console.log('================== 📦  生产地址加密完成  ==================');
console.log('Seed (仅本机环境变量，绝不下落磁盘)：', SEED.slice(0, 6) + '****' + SEED.slice(-4));
console.log('真实生产URL (加密前)：           ', PLAIN);
console.log('');
console.log('✅ EXPECTED_KEY_FINGERPRINT = "' + fingerprint + '"');
console.log('✅ PROD_BASE_URL_CIPHER    = "' + l3 + '"');
console.log('');
console.log('🔍 反向解密自检：' + (match ? '✅ 解密还原成功，100% 匹配' : '❌ 加解密不匹配！请立即停止并检查'));

if (!match) process.exit(3);

console.log('');
console.log('👉 下一步：把上面两行值覆盖到 miniapp/utils/env.ts 的两个 export const 即可。');
console.log('👉 发版前在小程序后台（release）注入 Seed：');
console.log('      方式A: 全局 globalData.GITHUB_SEED = "ghp_xxx"');
console.log('      方式B: wx.setStorageSync("GITHUB_SEED", "ghp_xxx")');
console.log('      方式C: 打包环境里注入 process.env.GITHUB_SEED');
console.log('');
