/**
 * 微信小程序代码有效性检测脚本 v2
 * 检测维度:
 *   1. app.json 页面引用完整性
 *   2. 组件引用一致性 (相对路径解析)
 *   3. tabBar 图片资源有效性
 *   4. 未使用文件识别
 *   5. TS/JS 编译产物一致性
 *   6. import 引用有效性
 *   7. 根目录干扰文件检查
 *   8. WXML 图片引用
 * 运行: node check.js [--clean-js]
 */

const fs = require('fs')
const path = require('path')

const ROOT = __dirname
let errors = []
let warnings = []
let infos = []
let redundantFiles = []

function logResult() {
  // no-op, we use console inline
}

const fileExists = (relPath) => fs.existsSync(path.join(ROOT, relPath))
const readFile = (relPath) => {
  const full = path.join(ROOT, relPath)
  try { return fs.readFileSync(full, 'utf-8') } catch { return null }
}

// 递归收集文件
function getAllFiles(dir, files = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (!['node_modules', '.git', '__MACOSX'].includes(entry.name)) {
        getAllFiles(fullPath, files)
      }
    } else {
      files.push(path.relative(ROOT, fullPath))
    }
  }
  return files
}

// 将组件路径解析为相对 ROOT 的路径
// 微信小程序组件路径:
//   - /components/card/index  (从项目根开始的绝对路径)
//   - ../../components/card/index (相对于 json 文件的路径)
function resolveCompPath(jsonFile, compPath) {
  if (compPath.startsWith('/')) {
    return compPath.slice(1)
  }
  const base = path.dirname(path.join(ROOT, jsonFile))
  const resolved = path.resolve(base, compPath)
  return path.relative(ROOT, resolved)
}

const allFiles = getAllFiles(ROOT)

console.log('\n' + '='.repeat(50))
console.log('  微信小程序代码有效性检测 v2')
console.log('='.repeat(50))

// ======= 1. app.json 基础 =======
console.log('\n【1】app.json 基础检查')
if (!fileExists('app.json')) {
  console.log('  ❌ app.json 不存在！')
  errors.push('app.json 不存在')
  process.exit(1)
}

let appCfg
try {
  appCfg = JSON.parse(readFile('app.json'))
  console.log('  ✅ app.json 解析成功')
} catch (e) {
  console.log('  ❌ app.json JSON 格式错误:', e.message)
  errors.push(`app.json JSON 格式错误: ${e.message}`)
  process.exit(1)
}

// ======= 2. 页面引用完整性 =======
console.log('\n【2】页面引用完整性检测')
const pages = appCfg.pages || []
console.log(`  注册页面: ${pages.length} 个`)

const pageFilesToCheck = ['.ts', '.js', '.wxml', '.wxss', '.json']
const allPagesUsed = new Set()

for (const pagePath of pages) {
  allPagesUsed.add(pagePath)
  const missing = []
  for (const ext of pageFilesToCheck) {
    const file = pagePath + ext
    if (!fileExists(file)) missing.push(ext)
  }
  if (missing.length > 0) {
    errors.push(`页面 ${pagePath} 缺少: ${missing.join(', ')}`)
    console.log(`  ❌ ${pagePath} 缺少: ${missing.join(', ')}`)
  } else {
    console.log(`  ✅ ${pagePath}`)
  }
}

// ======= 3. TabBar 一致性 =======
console.log('\n【3】TabBar 一致性检测')
if (appCfg.tabBar && appCfg.tabBar.list) {
  for (const tab of appCfg.tabBar.list) {
    const issues = []

    if (!allPagesUsed.has(tab.pagePath)) {
      issues.push('pagePath 未在 pages 中注册')
      errors.push(`TabBar "${tab.text}" 的 ${tab.pagePath} 未在 pages 中注册`)
    }

    if (tab.iconPath && !fileExists(tab.iconPath)) {
      issues.push(`图标 ${tab.iconPath} 不存在`)
      errors.push(`TabBar "${tab.text}" 图标 ${tab.iconPath} 不存在`)
    }
    if (tab.selectedIconPath && !fileExists(tab.selectedIconPath)) {
      issues.push(`选中图标 ${tab.selectedIconPath} 不存在`)
      errors.push(`TabBar "${tab.text}" 选中图标 ${tab.selectedIconPath} 不存在`)
    }

    if (issues.length > 0) {
      console.log(`  ❌ TabBar "${tab.text}": ${issues.join('; ')}`)
    } else {
      console.log(`  ✅ TabBar "${tab.text}" → ${tab.pagePath}`)
    }
  }
}

// ======= 4. 组件引用一致性 =======
console.log('\n【4】组件引用一致性检测')

// 全局组件
if (appCfg.usingComponents) {
  for (const [name, compPath] of Object.entries(appCfg.usingComponents)) {
    const hasTs = fileExists(compPath + '.ts')
    const hasJs = fileExists(compPath + '.js')
    const hasJson = fileExists(compPath + '.json')
    const hasWxml = fileExists(compPath + '.wxml')

    const issues = []
    if (!hasTs && !hasJs) {
      issues.push('缺少 .ts/.js')
      errors.push(`全局组件 ${name} (${compPath}) 缺少 .ts/.js`)
    }
    if (!hasJson) { issues.push('缺少 .json'); warnings.push(`全局组件 ${name} 缺少 .json`) }
    if (!hasWxml) { issues.push('缺少 .wxml'); warnings.push(`全局组件 ${name} 缺少 .wxml`) }

    if (issues.length > 0) {
      console.log(`  ${hasTs || hasJs ? '✅' : '❌'} 全局组件 ${name}: ${compPath} — ${issues.join(', ')}`)
    } else {
      console.log(`  ✅ 全局组件 ${name}: ${compPath}`)
    }
  }
}

// 页面局部组件
const jsonFiles = allFiles.filter((f) => f.endsWith('.json') && !f.includes('project.config'))
let pageCompIssues = 0
for (const jf of jsonFiles) {
  const content = readFile(jf)
  if (!content) continue
  try {
    const cfg = JSON.parse(content)
    if (cfg.usingComponents) {
      for (const [name, compPath] of Object.entries(cfg.usingComponents)) {
        const resolvedPath = resolveCompPath(jf, compPath)
        const hasSource = fileExists(resolvedPath + '.ts') || fileExists(resolvedPath + '.js')
        if (!hasSource) {
          warnings.push(`${jf} 引用的组件 ${name} (${resolvedPath}) 不存在`)
          pageCompIssues++
        }
      }
    }
  } catch {}
}
console.log(`  页面局部组件引用问题: ${pageCompIssues} 处`)

// ======= 5. TS/JS 编译产物一致性 =======
console.log('\n【5】TS/JS 编译产物一致性检测')
const tsFiles = allFiles.filter((f) => f.endsWith('.ts'))
const jsFiles = allFiles.filter((f) => f.endsWith('.js') && !f.includes('node_modules'))

let tsOnly = 0, jsOnly = 0, both = 0
const jsOnlyFiles = []

for (const tsf of tsFiles) {
  if (tsf.endsWith('.d.ts')) continue
  const jsf = tsf.replace('.ts', '.js')
  if (fileExists(jsf)) {
    both++
  } else {
    tsOnly++
    warnings.push(`${tsf} 无对应 .js 编译产物`)
  }
}

for (const jsf of jsFiles) {
  const tsf = jsf.replace('.js', '.ts')
  if (!fileExists(tsf)) {
    jsOnly++
    jsOnlyFiles.push(jsf)
  }
}

console.log(`  匹配: ${both}, 仅 TS: ${tsOnly}, 仅 JS: ${jsOnly}`)
if (jsOnlyFiles.length > 0) {
  console.log(`  ⚠️ 仅有 JS 无 TS 源文件: ${jsOnlyFiles.join(', ')}`)
}

// ======= 6. 未使用文件检测 =======
console.log('\n【6】未使用/冗余文件检测')

// 构建引用集合
const referencedFiles = new Set()
for (const p of pages) {
  for (const ext of ['.ts', '.js', '.wxml', '.wxss', '.json']) {
    referencedFiles.add(p + ext)
  }
}
if (appCfg.usingComponents) {
  for (const cp of Object.values(appCfg.usingComponents)) {
    for (const ext of ['.ts', '.js', '.wxml', '.json']) {
      referencedFiles.add(cp + ext)
    }
  }
}
referencedFiles.add('app.js')
referencedFiles.add('app.ts')
referencedFiles.add('app.wxss')
referencedFiles.add('app.json')
referencedFiles.add('sitemap.json')
referencedFiles.add('check.js')
referencedFiles.add('check-report.json')
referencedFiles.add('project.config.json')
referencedFiles.add('tsconfig.json')
referencedFiles.add('package.json')
referencedFiles.add('package-lock.json')

// 检查静态资源
const staticFiles = allFiles.filter((f) => f.startsWith('static/'))
const tabIconRefs = new Set()
if (appCfg.tabBar && appCfg.tabBar.list) {
  for (const tab of appCfg.tabBar.list) {
    if (tab.iconPath) tabIconRefs.add(tab.iconPath)
    if (tab.selectedIconPath) tabIconRefs.add(tab.selectedIconPath)
  }
}

// 检查 wxml/wxss 中的图片引用
const wxmlFiles = allFiles.filter((f) => f.endsWith('.wxml'))
const wxssFiles = allFiles.filter((f) => f.endsWith('.wxss'))
const referencedImages = new Set()

for (const wf of [...wxmlFiles, ...wxssFiles]) {
  const content = readFile(wf) || ''
  // src="..." or url(...)
  const regex = /(?:src=|url\()\s*["']?([^"')\s]+)["']?/g
  let m
  while ((m = regex.exec(content)) !== null) {
    const ref = m[1]
    if (ref.startsWith('/static/')) {
      referencedImages.add(ref.slice(1)) // remove leading /
    } else if (ref.startsWith('static/')) {
      referencedImages.add(ref)
    }
  }
}

let unusedStatic = 0
for (const sf of staticFiles) {
  if (!tabIconRefs.has(sf) && !referencedImages.has(sf)) {
    unusedStatic++
    console.log(`  ⚠️ 未使用资源: ${sf}`)
    warnings.push(`未使用的静态资源: ${sf}`)
  }
}
if (unusedStatic === 0) console.log('  ✅ 所有静态资源均被引用')

// ======= 7. import/require 引用有效性 =======
console.log('\n【7】import/require 引用有效性检测')
const tsJsFiles = allFiles.filter((f) => (f.endsWith('.ts') || f.endsWith('.js')) && !f.includes('node_modules'))
let importIssues = 0

for (const f of tsJsFiles) {
  const content = readFile(f) || ''
  const importRegex = /(?:import|require)\s*\(?\s*['"]([^'"]+)['"]/g
  let match
  while ((match = importRegex.exec(content)) !== null) {
    const importPath = match[1]
    if (importPath.startsWith('.') || importPath.startsWith('/')) {
      const sourceDir = path.dirname(path.join(ROOT, f))
      const resolved = path.resolve(sourceDir, importPath)
      const relative = path.relative(ROOT, resolved)

      const candidates = [
        relative + '.ts',
        relative + '.js',
        path.join(relative, 'index.ts'),
        path.join(relative, 'index.js'),
      ]

      const exists = candidates.some((c) => fileExists(c))
      if (!exists) {
        importIssues++
        errors.push(`${f} 引用 ${importPath} → ${relative} (不存在)`)
        console.log(`  ❌ ${f} 引用 ${importPath} (不存在)`)
      }
    }
  }
}
if (importIssues === 0) console.log('  ✅ 所有 import/require 引用有效')

// ======= 8. WXML 图片引用 =======
console.log('\n【8】WXML 图片引用检测')
let imgOk = 0, imgTotal = 0
for (const wf of wxmlFiles) {
  const content = readFile(wf) || ''
  const regex = /src=["']([^"']+)["']/g
  let m
  while ((m = regex.exec(content)) !== null) {
    const val = m[1]
    if (val.includes('{{') || val.startsWith('data:')) continue
    imgTotal++
    let src = val
    if (src.startsWith('/')) src = src.slice(1)
    if (fileExists(src)) {
      imgOk++
    } else {
      warnings.push(`${wf} 引用图片 ${val} 不存在`)
      console.log(`  ⚠️ ${wf} 引用 ${val} 不存在`)
    }
  }
}
console.log(`  有效图片引用: ${imgOk}/${imgTotal}`)

// ======= 9. 根目录干扰检查 =======
console.log('\n【9】根目录干扰文件检查')
const rootEntries = fs.readdirSync(ROOT, { withFileTypes: true })
const expectedRoot = new Set([
  'app.json', 'app.ts', 'app.js', 'app.wxss',
  'sitemap.json', 'project.config.json', 'tsconfig.json',
  'package.json', 'package-lock.json',
  'check.js', 'check-report.json',
  'components', 'pages', 'api', 'types', 'typings', 'utils', 'static', 'skills',
  'node_modules', '.git'
])

let rootIssues = 0
for (const entry of rootEntries) {
  if (!expectedRoot.has(entry.name) && !entry.name.startsWith('.')) {
    rootIssues++
    warnings.push(`根目录异常文件: ${entry.name}`)
    console.log(`  ⚠️ 根目录异常: ${entry.name}`)
  }
}
if (rootIssues === 0) console.log('  ✅ 根目录干净')

// ======= 汇总 =======
console.log('\n' + '='.repeat(50))
console.log('  检测报告')
console.log('='.repeat(50))

console.log(`\n  ❌ 错误: ${errors.length}`)
console.log(`  ⚠️ 警告: ${warnings.length}`)
console.log(`  ℹ️ 信息: ${infos.length}`)

if (errors.length > 0) {
  console.log('\n  — 错误详情 —')
  errors.forEach((e, i) => console.log(`    ${i + 1}. ${e}`))
}
if (warnings.length > 0) {
  console.log('\n  — 警告详情 —')
  warnings.forEach((w, i) => console.log(`    ${i + 1}. ${w}`))
}

// 建议删除
const deletableFiles = []
for (const jsf of jsFiles) {
  const tsf = jsf.replace('.js', '.ts')
  if (fileExists(tsf) && !tsf.endsWith('.d.ts')) {
    deletableFiles.push({ file: jsf, reason: 'TS 编译产物' })
  }
}

if (deletableFiles.length > 0) {
  console.log('\n  — 可删除的编译产物 (共 ' + deletableFiles.length + ' 个) —')
  deletableFiles.forEach((d, i) => console.log(`    ${i + 1}. ${d.file}`))
}

// 统计
console.log('\n  — 文件统计 —')
console.log(`    页面: ${pages.length}`)
console.log(`    TS 文件: ${tsFiles.length}`)
console.log(`    JS 文件: ${jsFiles.length}`)
console.log(`    WXML: ${wxmlFiles.length}`)
console.log(`    WXSS: ${wxssFiles.length}`)
console.log(`    JSON: ${jsonFiles.length}`)
console.log(`    图片: ${staticFiles.length}`)
console.log(`    总计: ${allFiles.length}`)

// 最终判定
console.log('\n' + '='.repeat(50))
if (errors.length === 0) {
  console.log('  ✅ 代码有效性检测通过，无错误')
} else {
  console.log(`  ❌ 检测到 ${errors.length} 个错误，需要修复`)
}
console.log('='.repeat(50))

// 写报告
const report = {
  summary: { errors: errors.length, warnings: warnings.length, infos: infos.length },
  errors,
  warnings,
  deletableFiles,
  stats: {
    pages: pages.length,
    tsFiles: tsFiles.length,
    jsFiles: jsFiles.length,
    wxmlFiles: wxmlFiles.length,
    wxssFiles: wxssFiles.length,
    jsonFiles: jsonFiles.length,
    imageFiles: staticFiles.length,
    totalFiles: allFiles.length,
  },
}
fs.writeFileSync(path.join(ROOT, 'check-report.json'), JSON.stringify(report, null, 2))
console.log('\n📄 报告已保存: check-report.json')

// 清理模式
if (process.argv.includes('--clean-js')) {
  console.log('\n🔧 清理 TS 编译产物 (.js) 并重新编译 ...')
  let deleted = 0
  for (const jsf of jsFiles) {
    const tsf = jsf.replace('.js', '.ts')
    if (fileExists(tsf)) {
      fs.unlinkSync(path.join(ROOT, jsf))
      deleted++
    }
  }
  console.log(`  已删除 ${deleted} 个 .js 文件`)
  try {
    const { execSync } = require('child_process')
    execSync('npx tsc', { cwd: ROOT, stdio: 'inherit' })
    console.log('  ✅ TypeScript 重新编译完成')
  } catch (e) {
    console.log('  ❌ 编译失败:', e.message)
  }
}
