<p align="center">
  <br>
  <img
    src="https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=AI%20Marketing%20Strategy%20Agent%20-%20modern%20minimalist%20logo%20with%20brain%20circuit%20and%20rocket%20icon%2C%20blue%20gradient%20background%2C%20clean%20corporate%20style&image_size=square_hd"
    width="128"
    height="128"
    alt="AI Marketing Strategy Agent"
  />
  <h1 align="center">AI Marketing Strategy Agent · 营销战略执行智能体</h1>
  <p align="center">
    <em>企业营销诊断 → 12周季度路线图 → 每日任务执行 → AI智能复盘 · 全闭环微信小程序 + FastAPI 后端</em>
  </p>
  <p align="center">
    <a href="#-快速开始">🚀 Quick Start</a>
    &nbsp;·&nbsp;
    <a href="#-功能总览">✨ Features</a>
    &nbsp;·&nbsp;
    <a href="#-生产加密方案">🔐 Encryption</a>
    &nbsp;·&nbsp;
    <a href="#-版权与商用授权">📄 License</a>
  </p>
  <p align="center">
    <a href="https://github.com/mstermoon007/Marketing-Director/actions"><img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat-square" alt="Build" /></a>
    <a href=""><img src="https://img.shields.io/badge/miniprogram-%E5%BE%AE%E4%BF%A1%E5%B0%8F%E7%A8%8B%E5%BA%8F-07C160?logo=wechat&logoColor=white&style=flat-square" alt="WeChat MiniProgram" /></a>
    <a href=""><img src="https://img.shields.io/badge/frontend-TypeScript%205.9-blue?logo=typescript&logoColor=white&style=flat-square" alt="TypeScript 5.9" /></a>
    <a href=""><img src="https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white&style=flat-square" alt="FastAPI" /></a>
    <a href=""><img src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python 3.9+" /></a>
    <a href=""><img src="https://img.shields.io/badge/style-EditorConfig%20%2B%20Prettier%20%2B%20Ruff%20%2B%20Black-black?style=flat-square" alt="Code Style" /></a>
    <a href="#-版权与商用授权"><img src="https://img.shields.io/badge/license-Research%20Only-critical?style=flat-square" alt="License: Research Only" /></a>
    <a href="https://github.com/mstermoon007/Marketing-Director/pulls"><img src="https://img.shields.io/badge/PRs-welcome-ff69b4?style=flat-square" alt="PRs Welcome" /></a>
  </p>
  <br>
</p>

---

> ⚠️  **版权声明（读前必看）**：本项目**仅用于学术研究、技术讨论与学习交流**。任何形式的商业用途（含但不限于二次打包商用、SaaS 化部署、品牌加盟、嵌入付费产品、政府/企业内部生产使用）**均需获得版权方书面授权**。详见 [📄 版权与商用授权](#-版权与商用授权)。

---

## ✨ 功能总览

| 诊断可视化 | 12周季度路线图 | 每日任务执行 | AI 复盘闭环 |
| :---: | :---: | :---: | :---: |
| **5 维度营销健康度雷达图 + 总分**，一眼看清企业短板 | **三阶段作战计划**（攻→守→升），每阶段 4 周，进度条可视化 | 精确到「小时粒度」的执行清单，**打卡追踪**，逾期自动提醒 | 上传图片/文字/文件 → AI 自动解析 → 校准下阶段任务 |
| ![diagnosis-placeholder](https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=5-dimension%20radar%20chart%20showing%20marketing%20health%20score%2C%20clean%20dashboard%20UI%2C%20dark%20blue%20theme&image_size=square) | ![roadmap-placeholder](https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=12-week%20quarterly%20roadmap%20timeline%20with%203%20phases%20and%20progress%20bars%2C%20mobile%20UI&image_size=square) | ![tasks-placeholder](https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=daily%20task%20checklist%20with%20hourly%20timeline%20on%20mobile%20screen%2C%20modern%20app%20UI&image_size=square) | ![review-placeholder](https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=AI%20review%20report%20dashboard%20with%20charts%20and%20insights%2C%20mobile%20UI%20dark%20blue&image_size=square) |

### 🎯 4 大核心价值

> 面向中小企业老板 / 营销负责人 / 个体创业者，**每天 5 分钟**，执行不迷茫。

1. 🩺 **诊断可视化** —— 产品力 / 获客力 / 转化力 / 复购力 / 执行力，5 维度雷达评分
2. 🗺️ **路线图跟踪** —— 12 周季度作战计划，三阶段进度条，随时知道「现在该干嘛」
3. ✅ **任务可执行** —— 每周 7 天，每天精确到小时的任务清单，手机打卡追踪
4. 🔄 **复盘闭环** —— 周 / 月 / 季复盘上传，AI 智能校准下阶段任务策略

---

## 🏗️ 技术架构

```
                        ┌──────────────────────────────────────────────────┐
                        │              微信小程序（纯原生 + TS）              │
                        │  ┌─────────┐ ┌────────────┐ ┌──────────────────┐  │
                        │  │  Pages  │ │ Components │ │  Utils / API     │  │
                        │  │  10屏   │ │ 10个可复用 │ │  request(加密)   │  │
                        │  └────┬────┘ └─────┬──────┘ └────────┬─────────┘  │
                        │       │            │                 │            │
                        │  ┌────┴────────────┴─────────────────┴───────┐    │
                        │  │     globalData 状态 + wx.setStorageSync     │    │
                        │  │   Token / 当前周次 / GITHUB_SEED 注入       │    │
                        │  └─────────────────────┬──────────────────────┘    │
                        └────────────────────────┼ HTTPS (wx.request) ──────┘
                                                 ▼
                        ┌──────────────────────────────────────────────────┐
                        │         后端服务（Python 3.9+ / FastAPI）          │
                        │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
                        │  │ 诊断Agent │ │ 执行Agent │ │   复盘 Agent     │  │
                        │  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
                        │       │            │                 │            │
                        │  ┌────┴────────────┴─────────────────┴───────┐    │
                        │  │   Pipeline / LLM 服务 / 规则引擎 / 行业技能  │    │
                        │  │   行业知识库：房产/美业/教育/餐饮/装修/代理  │    │
                        │  └─────────────────────┬──────────────────────┘    │
                        │                        ▼                           │
                        │         SQLite / PostgreSQL（持久化层）            │
                        └──────────────────────────────────────────────────┘
```

### 🧰 技术栈一览

| 层级 | 选型 | 版本 | 说明 |
| :--- | :--- | :--- | :--- |
| **小程序框架** | 原生微信小程序 | — | 不做跨端（性能最优，老板级用户大字体适配） |
| **前端语言** | TypeScript | `^5.9.3` | 严格模式 `strict: true` |
| **后端框架** | FastAPI | `>=0.110` | 异步高性能，原生 OpenAPI 文档 |
| **后端语言** | Python | `>=3.9` | `dataclass` / `pydantic v2` 全量类型 |
| **AI LLM** | DeepSeek / 通义千问 | REST API | 仅后端调用，小程序侧零直连 |
| **代码风格** | EditorConfig + Prettier + Ruff + Black | — | 前端 2-space / 后端 4-space，GitHub 开源标准 |
| **生产加密** | KDF (SHA-256) + 三级加密 (Base64→XOR→Base64 URL-safe) | 自研 | 生产 BaseURL **绝不以明文入库** |

---

## 📁 目录结构（精简版）

```
Marketing-Director/
├── miniapp/                     # 📱 微信小程序前端（TypeScript 5）
│   ├── api/                     #    request.ts — 统一请求封装（含生产加密解密）
│   ├── components/              #    10 个可复用组件 (progress-bar, task-card, radar-chart …)
│   ├── pages/                   #    10 个业务页面 (home/diagnosis/roadmap/plan/review/profile…)
│   ├── utils/
│   │   ├── env.ts               #    ⭐ 核心：KDF + 三级加密 + 指纹校验
│   │   ├── auth.ts / storage.ts #    Token 清态跳转 + 本地缓存
│   │   └── constants.ts         #    API_CODE / BUSINESS_PHASES
│   ├── behaviors/               #    user-info.ts 共享行为
│   ├── skills/                  #    小程序侧营销技能（诊断问题映射）
│   ├── static/                  #    tabBar 图标
│   ├── app.ts / app.json        #    全局入口 & 路由配置 (5 tabBar)
│   └── tsconfig.json            #    strict: true + DOM lib 兼容
│
├── src/                         # 🐍 FastAPI 后端（Python 3.9+）
│   ├── agents/                  #    diagnosis / executor / reviewer — 三大核心 Agent
│   ├── api/                     #    main.py: FastAPI 路由入口 (/api/auth /api/diagnosis …)
│   ├── services/                #    pipeline / llm / rule_based_diagnosis
│   ├── skills/                  #    行业知识库 (industry_skills/*.md + 房产专项)
│   ├── prompts/                 #    Agent Prompt 模板 (可热更新)
│   ├── models/                  #    Pydantic v2 业务模型
│   ├── config/                  #    settings.py
│   ├── db/                      #    models.py（SQLAlchemy）
│   └── utils/                   #    document_parser.py
│
├── tests/                       # 🧪 Pytest 测试套件（8+ 测试文件）
│   ├── conftest.py              #    pythonpath 注入
│   ├── test_*_agent.py          #    Agent 单元测试
│   ├── snapshots/               #    Prompt 快照测试（防止意外退化）
│   └── 测试报告.md
│
├── scripts/
│   └── encrypt-prod-url.js      # 🔐 运维脚本：真实生产URL一键三级加密
│
├── pyproject.toml               # Ruff / Black / MyPy / Pytest 配置
├── .editorconfig / .prettierrc  # 代码风格（GitHub 开源标准）
├── project.config.json          # 微信小程序项目配置（urlCheck=false 兼容 localhost）
├── AI营销智能体-微信小程序开发文档.md
└── 开发思路文档.md
```

---

## 🚀 快速开始

### 0. 前置条件

| 环境 | 最低版本 | 安装方式 |
| :--- | :--- | :--- |
| **微信开发者工具** | Stable 1.06+ | [mp.weixin.qq.com](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) |
| **Node.js** | 18+ | LTS 即可（仅用于 TS 编译 & 加密脚本） |
| **Python** | 3.9+ | 建议 pyenv / miniconda 管理 |
| **AppID** | 个人/企业 | 在 `project.config.json` 中替换 `appid` 字段 |

---

### 1️⃣ 后端服务本地启动（5 分钟）

```bash
cd "Marketing-Director"

# 1. 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate           # macOS / Linux
# .venv\Scripts\activate            # Windows PowerShell

# 2. 安装依赖
pip install -r requirements.txt
# 或（推荐，开发模式含 lint/test）：
pip install -e ".[dev]"

# 3. 启动后端（默认 http://localhost:8000/api）
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# ✅ 启动后访问 Swagger 文档：
#    http://localhost:8000/docs
#    http://localhost:8000/redoc
```

**后端自测**：`pytest -q` 一键跑 8 大测试套件。

---

### 2️⃣ 小程序前端导入 & 运行（3 分钟）

```bash
cd "Marketing-Director/miniapp"

# 仅首次安装 TypeScript 编译器
npm install

# （可选）本地编译 TS → JS（微信开发者工具也能自动编译）
npx tsc -p tsconfig.json --watch
```

**步骤**：
0. **替换 AppID（必须！）**：打开项目根目录 `project.config.json`，把第 26 行的占位符
   ```json
   "appid": "wxREPLACE_WITH_YOUR_APPID_HERE"
   ```
   改成你自己的小程序真实 AppID（在 [微信公众平台 → 开发设置](https://mp.weixin.qq.com/) 获取）。
   > 临时调试可直接改成 `touristappid`（游客模式，功能有一定限制）。
1. 打开 **微信开发者工具** → 导入项目 → 目录选择 `Marketing-Director` 仓库根目录
2. AppID：确认就是上一步填入的那个（或测试阶段选「测试号」）
3. 打开 `详情 → 本地设置` → 勾选 ✅ **不校验合法域名**（项目 `urlCheck=false` 已默认开启，但真机仍建议勾选以防万一）
4. 点击「编译」→ 真机扫码调试

> 💡  开发环境默认直接走 `http://localhost:8000/api`，不用任何解密。生产 release 版才会触发 Seed 注入 + 三级解密。

---

### 3️⃣ 发布到生产：URL 加密 + Seed 注入（核心）

本项目遵循 **「生产敏感配置零明文」** 原则，真实服务器域名绝不直接写在代码里。

#### Step ①：把真实生产域名三级加密成密文

```bash
cd "Marketing-Director"

# ⚠️  Seed (ghp_xxx) 仅在此处临时通过环境变量注入，永远不要写进文件！
GH_SEED="ghp_your_brand_new_github_pat_min_privilege"   \
PLAIN_URL="https://ai-marketing.your-company.com/api"   \
node scripts/encrypt-prod-url.js
```

输出示例：
```
✅ EXPECTED_KEY_FINGERPRINT = "xxxxxxxxxxxxxxxx"
✅ PROD_BASE_URL_CIPHER    = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
🔍 反向解密自检：✅ 解密还原成功，100% 匹配
```

#### Step ②：把这两行覆盖到 [miniapp/utils/env.ts:L30-L34](file:///Users/zhanggaozhang/TRAE-CN/Marketing%20Director/miniapp/utils/env.ts#L30-L34)

```typescript
export const EXPECTED_KEY_FINGERPRINT = "xxxxxxxxxxxxxxxx"
export const PROD_BASE_URL_CIPHER    = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
```

#### Step ③：小程序 release 运行时注入 Seed（三选一）

| 方式 | 代码片段（放 `app.ts` onLaunch 开头） | 适用场景 |
| :--- | :--- | :--- |
| **A. globalData（推荐）** | `getApp().globalData.GITHUB_SEED = 'ghp_xxx'` | 体验版 / 正式版发版前由运维构建时替换 |
| **B. wx.setStorageSync** | `wx.setStorageSync('GITHUB_SEED', 'ghp_xxx')` | 开发者真机调试（临时注入） |
| **C. 构建工具注入** | `define: { 'process.env.GITHUB_SEED': 'ghp_xxx' }` | Vite / Webpack / CI 流水线 |

#### Step ④：微信公众平台配置合法域名

路径：**小程序管理后台 → 开发 → 开发管理 → 开发设置 → 服务器域名**

必须同时添加到 3 个白名单：
- ✅ `request合法域名`   — `https://ai-marketing.your-company.com`
- ✅ `uploadFile合法域名`  — 同上（复盘图片上传）
- ✅ `downloadFile合法域名`— 同上（报告下载）

---

## 🔐 生产加密方案详解（KDF + 三级加密）

> 本项目的特色设计：**生产环境 BaseURL 在代码库里只存密文，明文凭据 0 下落**。

### 算法原理

```
┌───────────────────────────────────────────────────────────────────────┐
│  Plain URL   (真实域名，仅内存中短暂出现)                                │
│   https://ai-marketing.your-company.com/api                           │
└──────────────────────────────────┬────────────────────────────────────┘
                                   ▼  L1: UTF-8 → Standard Base64
┌───────────────────────────────────────────────────────────────────────┐
│  L1  aHR0cHM6Ly9haS1tYXJrZXRpbmcueW91ci1jb21wYW55LmNvbS9hcGk=        │
└──────────────────────────────────┬────────────────────────────────────┘
                                   ▼  L2: XOR 32B 派生密钥 (循环)
┌───────────────────────────────────────────────────────────────────────┐
│  L2  [ 104 bytes XOR cipher stream — 不可直接阅读 ]                    │
└──────────────────────────────────┬────────────────────────────────────┘
                                   ▼  L3: Base64 → URL-safe char map
┌───────────────────────────────────────────────────────────────────────┐
│  L3  gsjQ5YrkZag1o6yqZZULH1YsvOVs9509PvysKcvdyri62MCl    ← 入库密文    │
└───────────────────────────────────────────────────────────────────────┘
```

**密钥派生（KDF）**（两端算法必须完全一致，盐值是公开的但**绝对不能改**）：
```
key32 = SHA-256("MD::env::v3::" + GITHUB_SEED + "::AI-Marketing-Strategy-Agent::KDF")
```

### Fail-Fast 安全拦截（request.ts 的杀手锏）

真实环境里如果忘了配 Seed / Seed 是错的 / 域名还是 example.com，
代码会**立刻阻断首个请求并弹 Modal 提示**，而不是静默失败打到占位域名：

```
wx.showModal({
  title: '请先配置生产环境',
  content:
    '生产环境 BaseURL 解密失败\n' +
    '请在全局配置里注入 GITHUB_SEED\n' +
    '方法：getApp().globalData.GITHUB_SEED = "ghp_xxx"',
  showCancel: false,
})
throw new Error('[config] 生产环境URL未正确配置（占位符example.com未替换）')
```

---

## 🛡️ 安全最佳实践清单（生产发版前必核）

- [ ] **GitHub PAT 权限最小化**：Seed 只需要能派生密钥就行，给 `read:user` 即可，**绝对不要给 repo / delete 等大权限**
- [ ] **演示用旧 Seed 立即撤销**：**任何在 README / Issue / Slack 群里出现过的 `ghp_` 开头的字符串**（含本项目之前用于加密演示时临时引用的 Token）**务必立即 Revoke**
  > 撤销路径：GitHub 个人主页右上角头像 → Settings → 左侧 Developer settings → Personal access tokens → 找到对应 Token → Delete / Revoke
- [ ] **不要把 Seed 提交到 git**：`.gitignore` 已覆盖常见模式，发前再 `grep -r 'ghp_'` 扫一遍
- [ ] **小程序后台合法域名**：`request` / `uploadFile` / `downloadFile` 三项都要加
- [ ] **TLS 必须 1.2+**：后端配 HTTPS（Let's Encrypt 免费签），不要裸 HTTP
- [ ] **生产环境日志脱敏**：不要把 `Authorization` header、`GITHUB_SEED`、用户手机号打进可检索日志

---

## 📝 开发规范（GitHub 开源风格）

本项目全仓统一规范，提交 PR 前请确保本地跑过：

### 前端（小程序）

```bash
cd miniapp
npx tsc -p tsconfig.json --noEmit      # TS 严格类型检查
```

### 后端（Python）

```bash
# 代码风格（一键修复 99%）
ruff check src tests --fix
black src tests

# 类型检查
mypy src

# 全量测试（含 Prompt 快照防退化）
pytest -q
```

### Git Commit 规范（Conventional Commits）

```
<type>(<scope>): <subject>

feat(roadmap): 新增 12 周三阶段进度计算
fix(request): 修复 getBase 同步改异步后 upload 未 await 的 bug
docs(readme): 补充生产加密方案文档
refactor(env): KDF 盐值固定为 v3 版本
style(*): Prettier / Ruff 全仓格式化
```

---

## 📄 版权与商用授权

### 🇨🇳 中文版权声明

```
版权所有 © 2026 Marketing Director 项目团队（以下简称「版权方」）
版权所有，保留一切权利。

一、授权范围（仅限「非商业用途」）
    版权方在此授予任何获得本项目副本的个人或组织一份免费的、不可转让的、
    非独占的许可，允许其仅用于以下「研究讨论类目的」：
        ✅ 学术研究、技术学习、课程作业、个人实验
        ✅ 在技术博客 / 开源峰会 / 学术论文中引用（需注明出处）
        ✅ 非营利性组织内部无偿使用（年营收 ≤ 0 元）
    除此之外的任何用途，均需获得版权方的**书面授权**。

二、严格禁止（以下行为构成侵权，版权方保留追诉权利）
    ❌ 直接商用：打包作为 SaaS 产品、付费工具、付费咨询交付物
    ❌ 二次销售：转售、出租、分许可、加盟授权链
    ❌ 企业生产：任何以营利为目的的组织的内部核心业务使用
    ❌ 政府项目：嵌入 / 对接 / 依赖本项目的任何政府采购项目
    ❌ 去除 / 修改本版权声明或声称修改后作品原作出自自己

三、免责声明（AS IS）
    本项目按「原样」提供，版权方不对以下任何情况承担责任：
      · 任何直接、间接、附带、特殊、衍生性损害（含但不限于业务损失、
        利润中断、信息丢失）
      · 与任何真实企业、真实营销方案、真实商业结果的适配性
      · AI 大模型生成内容的事实准确性、法律合规性、道德正当性
      · 微信 / 浏览器 / 操作系统升级导致的兼容性问题

四、商用授权咨询
    若您需要在任何商业场景中使用本项目（含但不限于：独立部署、
    二次开发集成、品牌营销 SaaS、行业解决方案交付、政企客户项目），
    请通过以下方式联系版权方获取书面授权许可：

        📧 Email  :  license@ai-marketing-strategy.example
        💬 WeChat :  本项目 GitHub Issues 置顶帖内商务联系方式
        💰 授权费 :  按企业规模 / 用途 / 地域一企一议

五、法律适用
    本声明受中华人民共和国法律管辖并按其解释。
    因本声明或使用本项目引起的任何争议，各方同意提交版权方所在地
    有管辖权的人民法院诉讼解决。
```

### 🇺🇸 English Copyright Notice

```
Copyright © 2026 Marketing Director Project Team ("The Copyright Holder").
All Rights Reserved.

1.  SCOPE OF LICENSE (NON-COMMERCIAL USE ONLY)
    Permission is hereby granted, free of charge, to any person or organization
    obtaining a copy of this software and associated documentation files, to deal
    in the Software for NON-COMMERCIAL PURPOSES ONLY, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    to permit persons to whom the Software is furnished to do so, subject ONLY to
    research, academic study, personal experimentation and non-commercial teaching.

    ANY COMMERCIAL USE — including but not limited to SaaS deployment, charging
    end users, embedding in paid deliverables, internal for-profit production
    usage, government procurement projects — REQUIRES A SEPARATE WRITTEN LICENSE
    from The Copyright Holder. Contact address is listed in the Chinese notice.

2.  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE.
```

---

## 🤝 贡献指南（PRs Welcome 💕）

1. Fork 本仓库 → 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
2. 完成改动 → 本地通过 `tsc` / `ruff` / `black` / `pytest` 全量检查
3. 提交 Commit (`git commit -m 'feat(xxx): add amazing feature'`)
4. Push 到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request → 填写模板里要求的 3 项：What / Why / How tested

> 新手友好：Issues 里打 `good first issue` 标签的是适合入门的低门槛任务。

---

## 📮 联系 & 反馈

| 渠道 | 地址 |
| :--- | :--- |
| 💬 **GitHub Issues** | [github.com/mstermoon007/Marketing-Director/issues](https://github.com/mstermoon007/Marketing-Director/issues) |
| 📄 **Swagger 文档** | 本地后端启动后：`http://localhost:8000/docs` |
| 📘 **完整开发文档** | 仓库根目录 `AI营销智能体-微信小程序开发文档.md` |
| 💰 **商用授权咨询** | 见上方 [📄 版权与商用授权](#-版权与商用授权) 第四节 |

---

<p align="center">
  <img src="https://img.shields.io/badge/%E2%9D%A4%EF%B8%8F-Made%20with%20AI%20%2B%20Human%20Intelligence-ff69b4?style=for-the-badge" alt="Made with AI + Human Intelligence" />
  <br>
  <strong>本项目仅用于研究讨论 · 商用需书面授权 · All Rights Reserved.</strong>
</p>
