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
    <a href="#-版权与商用授权"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License: MIT License" /></a>
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
                        │          微信小程序（纯原生 + TS · Agent 原生）      │
                        │  ┌──────────────┐ ┌────────────┐ ┌──────────────┐  │
                        │  │  对话主界面   │ │ 辅助页面    │ │  公共组件     │  │
                        │  │  chat 流式    │ │看板/日程/   │ │bubble/markdown│  │
                        │  │  Markdown 渲染│ │计划详情/登录│ │think/task/radar│  │
                        │  └──────┬───────┘ └─────┬──────┘ └──────┬───────┘  │
                        │         │               │               │          │
                        │  ┌──────┴───────────────┴───────────────┴──────┐   │
                        │  │   自研轻量响应式 Store + wx.storage 缓存     │   │
                        │  │  (对话摘要/日程/设置 · 启动秒开)             │   │
                        │  └──────────────────────┬──────────────────────┘   │
                        │  ┌──────────────────────┴──────────────────────┐   │
                        │  │  网络层 api/：JSON + SSE 流式(wx.request chunked)│  │
                        │  │  JWT 自动附加 + 错误分级                       │   │
                        │  └──────────────────────┬──────────────────────┘   │
                        └────────────────────────┼ HTTPS (wx.request) ──────┘
                                                 ▼
                        ┌──────────────────────────────────────────────────┐
                        │         后端服务（Python 3.9+ / FastAPI）          │
                        │  ┌────────────────────────────────────────────┐  │
                        │  │   Agent Core（LangGraph 状态图 · 后端大脑）  │  │
                        │  │  MainController → 意图分类 → 路由子 Agent    │  │
                        │  │  ┌─────────┐┌─────────┐┌─────────┐┌──────┐ │  │
                        │  │  │ 诊断子A  ││ 计划子A  ││ 日程子A  ││复盘子A│ │  │
                        │  │  └────┬────┘└────┬────┘└────┬────┘└──┬───┘ │  │
                        │  │  Tool 层：diagnose/generate_plan/         │  │
                        │  │  schedule/calculate_kpi/upload/rag       │  │
                        │  └───────────────┬──────────────────────────┘  │
                        │  ┌───────────────┴──────────────────────────┐  │
                        │  │  ChromaDB 记忆 & 知识库（向量持久化）      │  │
                        │  │   user_profile / conversation_history /    │  │
                        │  │   metric_snapshots + 营销知识库(547 卡片)   │  │
                        │  └───────────────┬──────────────────────────┘  │
                        │  ┌───────────────┴──────────────────────────┐  │
                        │  │   Pipeline / LLM 服务 / 规则引擎 / 行业技能  │  │
                        │  │   行业知识库：房产/美业/教育/餐饮/装修/代理  │  │
                        │  └─────────────────────┬──────────────────────┘  │
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
| **Agent 编排** | LangGraph | `>=1.0` | `StateGraph` 状态图：意图分类→子 Agent 路由 |
| **向量数据库** | ChromaDB | `>=1.5` | 记忆库（画像/历史/指标）+ 营销知识库 RAG |
| **向量化** | 本地哈希向量（离线）/ OpenAI `text-embedding-3-small` | 384 维 / 1536 维 | 无 Key/无网环境可用，可热插拔 |
| **AI LLM** | DeepSeek（文本主模型）· OpenAI `gpt-4o`（多模态 / 截图解析） | `deepseek-chat` / `gpt-4o` | 仅后端调用，小程序侧零直连；无 Key 自动降级规则引擎；模型名可经 `LLM_TEXT_MODEL` / `LLM_VISION_MODEL` 环境变量覆盖 |
| **代码风格** | EditorConfig + Prettier + Ruff + Black | — | 前端 2-space / 后端 4-space，GitHub 开源标准 |
| **生产加密** | KDF (SHA-256) + 三级加密 (Base64→XOR→Base64 URL-safe) | 自研 | 生产 BaseURL **绝不以明文入库** |

---

## 📁 目录结构（精简版）

```
Marketing-Director/
├── miniapp/                     # 📱 微信小程序前端（TypeScript 5 · Agent 原生交互）
│   ├── api/                     #    request.ts 统一网络层（JSON + SSE 流式 + JWT 自动附加 + 错误分级）
│   │                           #    agent.ts — streamChat → /agent/chat/stream（SSE）
│   │                           #    loops.ts — 阶段四闭环接口（确认/打卡/上传/复盘/反馈）
│   ├── store/                   #    ⭐ 自研轻量响应式 Store（发布订阅 + bindStore + wx.storage 持久化）
│   ├── components/              #    7 个可复用组件（markdown-view / message-bubble / progress-bar /
│   │                           #                   quick-action-bar / task-card / radar-chart / thinking-indicator）
│   ├── pages/                   #    Agent 原生页面（对话为核心 · 共 7 个页面：4 主包 + 3 分包详情页）
│   │   ├── chat/               #      对话主界面（流式 Markdown / 文本·图片·文件输入 / 上下文快捷 / 思考指示）
│   │   ├── dashboard/          #      数据看板（5 维雷达图 + 季度进度 + 数据上传入口）
│   │   ├── schedule/           #      每周日程（周历条 / 打卡 checkin / 周末复盘 CTA）
│   │   ├── plan-detail/        #      计划详情（可微调 / 确认并排期）
│   │   ├── diagnosis-detail/   #      诊断详情（5维雷达 + Top问题 + 季度路线图 · 保存/分享）
│   │   ├── review-detail/      #      复盘详情（指标达成 + 建议 · 采纳→自动排期）
│   │   └── onboarding/         #      登录（JWT 获取）
│   ├── utils/
│   │   ├── env.ts               #    ⭐ 核心：KDF + 三级加密 + 指纹校验（生产 BaseURL 零明文）
│   │   ├── auth.ts / storage.ts #    ensureLogin(401→reLaunch) + 本地缓存策略
│   │   ├── date.ts / markdown.ts #    日期友好格式化 + Markdown→HTML（供 rich-text 渲染）
│   │   └── constants.ts         #    AGENT_INTENTS / AgentStreamEvent / ERROR_LEVEL
│   ├── types/                   #    全局 TS 类型（ChatMessage / Todo / AgentEvent …）
│   ├── app.ts / app.json        #    全局入口 & 路由配置（3 tabBar 纯文字：对话/看板/日程）
│   └── tsconfig.json            #    strict: true + DOM lib 兼容
│
├── src/                         # 🐍 FastAPI 后端（Python 3.9+）
│   ├── agent_core/              #    ⭐ 阶段二：Agent 核心框架（后端大脑）
│   │   ├── graph.py             #       LangGraph 状态图：分类→诊断/计划/日程/复盘/闲聊
│   │   ├── controller.py        #       MainController 主控（意图调度 + 多轮上下文）
│   │   ├── sub_agents/          #       诊断/计划/日程/复盘/闲聊 子 Agent 内部流程
│   │   ├── tools.py             #       6 个标准 Tool（diagnose/plan/schedule/…）
│   │   ├── knowledge.py         #       营销知识库 RAG（547 卡片向量化检索）
│   │   ├── memory.py            #       ChromaDB 记忆库（画像/历史/指标快照）
│   │   ├── embeddings.py        #       本地哈希向量 + OpenAI 向量（可插拔）
│   │   ├── intent.py            #       规则意图分类（离线、零依赖）
│   │   └── state.py / config.py / sessions.py / common.py / _chroma.py
│   ├── agents/                  #    diagnosis / executor / reviewer — 三大核心 Agent
│   ├── api/                     #    main.py + agent.py: FastAPI 路由 (/api/agent/chat …)
│   ├── services/                #    pipeline / llm / rule_based_diagnosis
│   ├── skills/                  #    行业知识库 (industry_skills/*.md + 房产专项)
│   ├── prompts/                 #    Agent Prompt 模板 (可热更新)
│   ├── models/                  #    Pydantic v2 业务模型
│   ├── config/                  #    settings.py
│   ├── db/                      #    models.py（SQLAlchemy）
│   └── utils/                   #    document_parser.py
│
├── data/                        # 📦 数据与向量库
│   ├── marketing_knowledge_cards.jsonl  # 547 张营销方法卡片（RAG 语料）
│   ├── openapi.json             #    📘 OpenAPI 规范文件（自动生成，CI 漂移检查用）
│   └── chroma_db/               #    ChromaDB 持久化目录（记忆 + 知识库）
│
├── tests/                       # 🧪 Pytest 测试套件（10+ 测试文件，166 用例）
│   ├── conftest.py              #    pythonpath 注入
│   ├── test_agent_core.py       #    Agent 框架端到端（意图/RAG/记忆/多轮）
│   ├── test_*_agent.py          #    诊断/执行/复盘 Agent 单元测试
│   ├── snapshots/               #    Prompt 快照测试（防止意外退化）
│   └── 测试报告.md
│
├── scripts/
│   ├── build_knowledge_cards.py # 🧠 由模板×行业×渠道展开生成 547 张知识卡片
│   ├── check_dependency_drift.py # 🔍 依赖漂移检查（pyproject vs import AST 全量扫描）
│   ├── check_drift.sh            # 🛡️ 提交前漂移检查（5 维度：依赖/页面/类型/密钥/配置）
│   ├── extract_routes.py        # 📋 API 端点清单提取 + OpenAPI JSON 导出
│   ├── generate_docs.sh         # 📝 文档自动生成（从 OpenAPI/app.json 刷新 README）
│   ├── verify_security.py       # 🛡️ 安全验证（含 Agent 端点 JWT 401 + 多轮）
│   └── (生产配置由后端登录下发，无本地加密脚本)
│
├── pyproject.toml               # Ruff / Black / MyPy / Pytest 配置
├── .editorconfig / .prettierrc  # 代码风格（GitHub 开源标准）
├── project.config.json          # 微信小程序项目配置（urlCheck=false 兼容 localhost）
├── AI营销智能体-微信小程序开发文档.md
└── 开发思路文档.md
```

### 📱 小程序页面清单

> 以下列表由 `scripts/generate_docs.sh` 从 `miniapp/app.json` 自动生成，勿手动编辑。

| 类型 | 页面路径 | 说明 |
|:---|:---|:---|
<!-- AUTO-GEN-PAGES-START -->
| 主包 | pages/chat/index | - |
| 主包 | pages/dashboard/index | - |
| 主包 | pages/schedule/index | - |
| 主包 | pages/onboarding/index | - |
| 分包 | pages/detail/diagnosis-detail/index | - |
| 分包 | pages/detail/review-detail/index | - |
| 分包 | pages/detail/plan-detail/index | - |
<!-- AUTO-GEN-PAGES-END -->

---

## 🧠 Agent 核心框架（阶段二 · 后端大脑）

> 阶段二把后端从「被动线性 API」升级为「可推理、可记忆、可调度工具的多 Agent 协作层」。
> 用户用自然语言即可驱动完整的营销闭环：**诊断 → 计划 → 日程 → 复盘**。

### 架构总览

```
用户自然语言 ──▶ MainController（chat）
                    │
                    ▼
             意图分类（规则，离线）
        ┌───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼
    诊断 Diagnosis  计划 Planner  日程 Scheduler  复盘 Reviewer  （+ 闲聊 Chat）
        │           │           │           │
        └───────────┴─────┬─────┴───────────┘
                          ▼
            标准 Tool 层（被任意子 Agent 调用）
   ┌────────────┬────────────┬───────────┬─────────────┬──────────────┐
   │diagnose_   │generate_   │schedule_  │upload_and_   │calculate_kpi │search_
   │business    │plan        │task       │parse_data    │              │marketing_
   │            │            │           │              │              │knowledge
   └────────────┴────────────┴───────────┴─────────────┴──────────────┘
                          ▼
        ChromaDB：记忆库（画像/历史/指标） + 营销知识库（RAG）
```

### 核心能力

| 能力 | 说明 |
| :--- | :--- |
| **意图路由** | 规则分类器（复盘 > 诊断 > 日程 > 计划 > 闲聊），零依赖、可离线，支持 pending_intent 追问回流 |
| **子 Agent 内部流程** | 诊断（框架追问+数据+RAG→归因）、计划（拆解+模板填充→日程）、日程（按天分配+每日 09:00 提醒）、复盘（计划vs实际+归因→调整建议） |
| **标准 Tool** | `diagnose_business` / `generate_plan` / `schedule_task` / `upload_and_parse_data` / `calculate_kpi` / `search_marketing_knowledge`，均为 LangChain `@tool` 封装，可被 LLM 直接调用 |
| **记忆库** | 三集合：`user_profile`（用户画像）、`conversation_history`（多轮对话）、`metric_snapshots`（指标变化）；跨轮自动携带业务上下文 |
| **营销知识库（RAG）** | 547 张方法卡片向量化（内容运营/获客引流/转化成交/私域运营/活动策划/客户管理…），按 `category` / `industry` 多条件检索，召回分数 `score = 1 - distance` |
| **离线可用** | 本地哈希向量（384 维，signed hashing + TF 加权 + L2 归一化）零网络依赖；无 `DEEPSEEK_API_KEY` 时诊断/计划自动降级规则引擎，全流程仍可跑通 |
| **主动智能** | 后端不再只是接口——能按自然语言主动诊断、规划、排期与复盘 |

### HTTP 接口

> 完整 API 文档由 FastAPI 自动生成，见下方 [📘 API 文档](#-api-文档)。以下仅列出 Agent 核心对话接口：

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| `POST` | `/api/agent/chat` | 一轮对话（需 JWT）。`message` / `session_id` / `business_id` / `files`；返回 `response` / `intent` / `needs_clarification` |
| `POST` | `/api/agent/chat/stream` | **SSE 流式对话**（需 JWT）。`enableChunked` 分段回传，事件序列：`intent` → `thinking*`（0~N）→ `done`。`Content-Type: text/event-stream`，每帧 `data: {json}\n\n` |
| `GET`  | `/api/agent/history` | 读取某会话历史（上下文保持），需 JWT |

### 构建 / 重建知识库

```bash
# 首次或语料变更后，强制重建 ChromaDB 中的 547 张知识卡片
AGENT_REBUILD_KNOWLEDGE=true python -m pytest tests/test_agent_core.py -q

# 或单独生成语料 JSONL（模板 × 行业 × 渠道展开）
python scripts/build_knowledge_cards.py
```

### 端到端验证

```bash
# 安全 + Agent 端点验证（13 项：含 Agent JWT 401、诊断意图识别、多轮上下文）
python scripts/verify_security.py
```

---

## 🖥️ 小程序前端重构（阶段三 · Agent 原生交互）

> 阶段三把前端从「多页表单式业务应用」彻底重构为「以对话为核心、辅助看板与日程」的 Agent 原生小程序。
> 删除了全部旧代码，基于原生框架 + TypeScript 严格模式从零重建，让中小企业老板**用自然语言驱动整个营销闭环**。

### 设计原则

| 原则 | 落地方式 |
| :--- | :--- |
| **对话优先** | 首页即 tabBar「对话」页；所有业务动作（诊断 / 计划 / 排期 / 复盘）都从一句话开始，结果以结构化卡片回链到辅助页 |
| **流式体验** | SSE 流式输出，逐字渲染 Markdown；`thinking-indicator` 实时展示 Agent 思考进度 |
| **轻量状态** | 自研响应式 Store（发布订阅 + `bindStore` 桥接 `setData`），不引第三方状态库 |
| **启动秒开** | `wx.storage` 缓存对话摘要 / 日程 / 设置，`onLaunch` 同步恢复，无首屏网络等待 |
| **安全复用** | 沿用阶段一生产加密（KDF + 三级加密 / JWT 自动注入 / 环境检测），不删除 |

### 前端架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Pages（tabBar 纯文字）                    │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐               │
│  │  对话 chat │   │  看板 dash │   │  日程 sched │   + plan-detail / onboarding │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘               │
│        └───────────────┴───────────────┘                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  自研 Store（store/index.ts）                           │   │
│  │  · 全局状态：messages / todos / profile / settings      │   │
│  │  · bindStore(page, selector) → 订阅切片自动 setData      │   │
│  │  · 持久化：wx.storage（对话摘要/日程/设置）启动秒开       │   │
│  └──────────────────────────────┬───────────────────────┘   │
│  ┌──────────────────────────────┴───────────────────────┐   │
│  │  网络层 api/（request.ts + agent.ts）                   │   │
│  │  · get/post/put/del/upload — JSON                      │   │
│  │  · stream — wx.request({enableChunked:true}) + SSE 解析 │   │
│  │  · JWT 自动附加 + 错误分级（ERROR_LEVEL）               │   │
│  └──────────────────────────────┬───────────────────────┘   │
│  ┌──────────────────────────────┴───────────────────────┐   │
│  │  公共组件 components/                                   │   │
│  │  message-bubble / markdown-view / thinking-indicator   │   │
│  │  quick-action-bar / task-card / radar-chart / progress-bar   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 对话主界面（chat）

- **流式 Markdown 渲染**：`markdown-view` 组件把 Markdown → HTML，交给 `<rich-text>` 渲染，支持标题/列表/加粗/代码块/表格
- **多模态输入**：文本、图片（`wx.chooseMedia`）、文件（复盘材料）三种输入入口
- **上下文快捷操作**（`quick-action-bar`）：诊断 / 排周计划 / 看日程 / 复盘 一键发送，降低输入门槛
- **Agent 思考指示**（`thinking-indicator`）：流式 `thinking` 事件驱动，展示「正在分析…」动画
- **结果卡片联动**：诊断 / 复盘结果卡片可点击 → 跳看板；日程卡片 → 跳日程；计划卡片 → 跳计划详情

### SSE 流式协议（前端 ↔ 后端）

| 事件 | 字段 | 说明 |
| :--- | :--- | :--- |
| `intent` | `intent: diagnose\|plan\|schedule\|review\|chat` | 首帧，意图分类结果 |
| `thinking` | `content` | 0~N 帧，Agent 推理过程，驱动思考指示 |
| `done` | `content` / `card?` | 末帧，最终回复 + 可选结构化结果卡片 |

前端解析（`request.ts` 的 `stream`）：`task.onChunkReceived` 累积 `data: {...}\n\n` 帧，逐帧回调并通过 Store 增量更新消息的 `streaming` 标记直到 `done`。

### 缓存策略（启动秒开）

| 缓存键 | 内容 | 恢复时机 |
| :--- | :--- | :--- |
| `CHAT_SUMMARY` | 最近对话摘要列表 | `onLaunch` 同步恢复，首屏可见历史 |
| `SCHEDULE_CACHE` | 本周日程（按天分组） | 日程页 `onLoad` 直接渲染，无网络等待 |
| `USER_SETTINGS` | 用户设置 / 周次 / 阶段 | 全局配置秒级读取 |
| `PROFILE_SUMMARY` | 用户画像摘要 | 看板页直接展示 |

> 缓存仅存摘要与轻量数据，完整数据仍由后端实时拉取；`store.clearAll()` 在登出时清空全部本地状态。

---

## 🔗 功能闭环实现与联通（阶段四）

> 阶段四把阶段二（后端大脑）与阶段三（Agent 原生前端）真正咬合：一条用户输入即可触发完整的
> **发现问题 → 制定方案 → 执行跟踪 → 复盘优化** 循环，无需手动穿梭于多个独立功能。

### 闭环全景

```
一句自然语言（对话页）
   │
   ▼  SSE 流式 · normalize_payload() 统一结构化结果
   ├─ 诊断 diagnose  ──────────────▶ 看板雷达 + 诊断详情（保存/分享）
   ├─ 计划 plan     ──▶ 计划详情 ──▶ 微调 / 确认并排期 ──▶ 日程（todos 落库）
   ├─ 日程 schedule ──────────────▶ 周历视图 + 任务打卡（checkinTodo）
   └─ 复盘 review   ──▶ 复盘详情 ──▶ 采纳建议 → 自动生成下周计划 + 排期
                                              │
   数据闭环：看板「上传数据」→ uploadMetrics → KPI ──┘（供周末复盘燃料）
   持续学习：每次 👍/👎/微调 → submitFeedback → strategy_scores（越用越懂你）
```

### 六大闭环能力

| 闭环 | 前端入口 | 后端接口 | 落点 |
| :--- | :--- | :--- | :--- |
| **诊断闭环** | 对话卡片 → 诊断详情 | `POST /api/agent/chat/stream`（intent=diagnose） | store.diagnosis 持久化 + onShareAppMessage |
| **计划闭环** | 计划详情（微调/确认） | `POST /api/plan/{plan_id}/confirm` / `edit` / `regenerate` | 确认即 `schedule_task` 落库 todos |
| **日程闭环** | 日程页打卡 | `PUT /api/schedule/checkin` / `POST /api/schedule/sync` / `GET /api/schedule` | 真实执行情况写回，供复盘读取 |
| **数据闭环** | 看板「上传数据」 | `POST /api/metrics/upload`（安全文件名） | CSV/截图安全解析 → KPI 回显 |
| **复盘闭环** | 周末 CTA / 对话「复盘」 | `POST /api/review/trigger` / `POST /api/review/{review_id}/apply` | 采纳即重排下周计划 → 跳日程 |
| **持续学习** | 消息卡片 👍/👎、计划微调 | `POST /api/agent/feedback` | 更新 `strategy_scores` → RAG 排序优化 |

### 关键实现

- **统一结果契约 `normalize_payload()`（controller.py）**：各子 Agent 的 `tool_results` 键名各异
  （`diagnose` / `plan`+`schedule` / `review_parse`+`kpi`），`normalize_payload` 归一化为稳定的
  `{ diagnosis, plan, schedule, review, kpi, business_id }` 前端契约，前端 `parseCard` / `syncFromResult`
  只消费一份结构，彻底消除解析碎片化。
- **对话页编排（chat/index.ts）**：`startStream(message)` → 收到 `done` 事件 → `syncFromResult`
  按意图把结果写入 store（diagnosis→看板、plan→计划详情、schedule→todos+`syncSchedule`、
  review→复盘详情）；附件先经 `stageFiles()` 暂存到 `/files/upload` 再随消息上传（解决小程序本地路径服务端不可读）。
- **自研 Store 持久化**：`setDiagnosis/setPlan/setReview/setTodosFromBackend` 均写入 `wx.storage`，
  启动 `loadCache()` 秒开恢复，退出 `clearAll()` 清空。
- **看板增强**：新增「季度进度」（`calculateQuarterProgress` + `weekToPhase`）与「业务数据上传」入口，
  上传后回显 KPI（`kpi.rows` / `merged_numbers`）。
- **日程增强**：顶部 7 天周历条（`generateWeekDates`）+ 每日完成度圆点；勾选任务本地翻转并 `checkinTodo`
  落库；周六/周日自动浮现「本周复盘」横幅 → `triggerReview` 直达复盘详情。

### 验证

```bash
# 前端：类型检查 + 重新编译 TS→JS（微信开发者工具读取产物）
cd miniapp && npm run rebuild        # 等价于 clean + tsc

# 后端：全量测试（含 Agent 框架 / SSE / 闭环接口）
pytest -q
```

### 一键体验路径

1. 对话页：「帮我诊断下我的烘焙店」→ 看板出现 5 维雷达 + 诊断详情
2. 对话页：「给我出这周的执行计划」→ 计划详情（可微调）→「确认并排期」→ 日程页出现每日任务
3. 日程页：勾选已完成任务（自动打卡）→ 周六点「本周复盘」→ 复盘详情
4. 复盘详情：「采纳建议并生成下周计划」→ 自动排期并跳日程，完成「复盘 → 提升」闭环
5. 看板：「上传数据」上传本周 CSV/截图 → 自动解析为 KPI，喂给下一次复盘

---

## 🛡️ 稳定性与性能打磨（阶段五）

> 阶段五让小程序在**弱网、前后台频繁切换、高并发**下依旧稳定：通过请求序号 + 状态锁消除
> 生命周期竞态，通过可取消的流式句柄避免消息交错，通过分包 + 懒加载把首屏压到秒开，并用
> 端到端自动化测试锁定「诊断 → 计划 → 日程」核心链路。

### 目标与验收指标

| 场景 | 改造前风险 | 阶段五保障 | 验收目标 |
| :--- | :--- | :--- | :--- |
| 弱网 / 频繁切前后台 | 旧回调覆盖新状态、消息错乱、白屏 | 请求序号 + 状态锁 + 流取消 | 不出现消息错乱 / 白屏 / 导航失败 |
| 快速连续发送 | 多条流交错、气泡错位 | 新流中止旧流 + 清理卡死气泡 | 流式逐字呈现、体验接近原生聊天 |
| 首屏加载 | 主包过大、详情页拖累 | 分包 + `requiredComponents` 懒加载 | 首屏加载 < 1.5 秒，对话页秒开 |
| 迭代回归 | 手动验证链路易遗漏 | 端到端自动化测试 | 核心链路可一键回归、零回归崩 |

### 1. 生命周期竞态防护（请求序号 + 状态锁）

- **单调请求序号 `_reqSeq` / `_currentSeq`（`pages/chat/index.ts`）**：每次 `startStream` 自增
  `++this._reqSeq` 并把 `_currentSeq` 设为该值，回调闭包内携带 `mySeq`。只有
  `mySeq === this._currentSeq` 的回调才允许改写 store，旧流转为「沉默」——彻底杜绝旧网络
  响应覆盖新对话状态。
- **状态锁 `_locked` + 防重 `_inflightText`**：`send()` 在请求进行中锁住输入；若用户重复发送
  **完全相同的文本**（`text === this._inflightText`）则直接去重返回，避免同一条消息被发两次。
- **`_release(mySeq)` 安全解锁**：仅当 `mySeq === _currentSeq` 时才释放锁，保证被中止的旧流不会
  误释放新流的锁。
- **`store.cleanupStreamingAgent()`（`store/index.ts`）**：新流接管前，清理上一条「卡死」的
  streaming agent 气泡——空气泡直接删除，半成品气泡标记为 `streaming:false` 收尾，杜绝残留
  半句消息导致界面错乱。

### 2. 流式输出优化（请求取消机制）

- **可中止的流句柄 `StreamHandle`（`api/request.ts`）**：`stream()` 返回 `{ promise, abort }`，
  内部包裹 `wx.request({ enableChunked:true })` 的 task。`abort()` 调用 `task.abort()` 并以带
  `isAbort` 标记的错误 reject；调用方据此**静默吞掉**被取代的流，不弹错误、不写状态。
- **`chat/index.ts` 全链路消费**：`startStream` 在发起新流前先 `_abortStream()` 中止旧句柄；
  `handle.promise.catch` 识别 `isAbort` 与过期 `mySeq` 后静默忽略，其余异常才提示并 `_release`。
- **`onUnload` 兜底**：页面销毁时调用 `_abortStream()`，避免已离开页面仍收到 `onChunkReceived`
  回调写入已不存在的 store（典型切后台 / 跳转导致的竞态来源）。

### 3. 分包加载 + 懒加载（首屏秒开）

- **`app.json` 分包配置**：把三个详情页移入独立分包 `pages/detail`，主包仅保留
  `chat / dashboard / schedule / onboarding` —— 详情页（诊断 / 计划 / 复盘）改为按需下载。
- **`lazyCodeLoading: "requiredComponents"`**：组件按需注入，未用到的自定义组件不随页面初始化加载。
- **分包内路径修正**：详情页 `import` 前缀由 `../../` 提升至 `../../../`，组件引用统一走
  绝对路径 `/components/...`，确保分包深度下仍能解析 store / utils / api。
- **效果**：首屏包体显著缩小，配合 `wx.storage` 缓存恢复，对话页进入即可见历史，达成秒开。

### 4. 端到端自动化测试（诊断 → 计划 → 日程）

- **`tests/test_e2e_closed_loop.py`**：用 `FastAPI TestClient` + `create_access_token` 跑通
  **完整业务闭环**，无需 mock LLM（后端工具在无密钥时自动降级本地规则引擎）。
- **覆盖断言**：
  - `POST /api/agent/chat/stream` 诊断 → 计划两轮对话，断言**意图路由**（`diagnose` / `plan`）、
    `business_id` 透传、`plan` 含 `id` 与 `days`；
  - `POST /api/plan/{plan_id}/confirm` 确认排期 → `GET /api/schedule?business_id=` 断言
    `todos` 数量与排期一致、状态合法、`plan_id` 关联、`plan_titles ⊆ todo_titles`（**数据一致性**）；
  - `confirm` 未知 plan 返回 `ok=False`（**不 500**、异常安全）。
- **节点切换一致性**：测试直接验证 Agent 在不同意图节点间切换时，结构化结果（diagnosis → plan →
  schedule）逐层正确落库，回归时一键运行即可发现链路断裂。

### 验证

```bash
# 前端：清理并重编译 TS→JS（校验分包移动、竞态改造类型无误）
cd miniapp && npm run rebuild        # clean + tsc，0 error

# 后端：全量回归（含阶段五端到端闭链测试）
pytest -q                            # 173 用例全绿，0 回归
```

### 一键回归路径

1. `pytest -q` → 端到端测试自动走完「诊断 → 计划 → 确认排期 → 日程」并断言数据一致。
2. `npm run rebuild` → 类型检查 + 分包重编译，确认竞态 / 取消 / 分包改造无编译错误。
3. 真机弱网模拟：连续快速发送多条消息 + 频繁切前后台，确认无消息错乱、无白屏、首屏秒开。

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

**后端自测**：`pytest -q` 一键跑 10+ 测试套件（173 用例，含阶段五「诊断→计划→日程」端到端闭链 + SSE 流式端点验证）。

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

> 💡  开发环境默认直接走 `http://localhost:8000/api`，不用任何配置。生产 release 版通过登录后后端下发生产地址。

---

### 3️⃣ 发布到生产：后端下发配置（核心）

本项目遵循「生产敏感配置不下发到客户端代码」原则：小程序**不再在代码里硬编码或加密任何生产地址/密钥**。生产环境基址由**后端在登录成功后下发并持久化**到本地存储（`md:api_base_url`），前端从此处读取——无本地硬编码、无加密逻辑、无 Seed。

#### 链路

```
登录成功（wx.login → POST /api/auth/login）
   └─ 后端返回 data.api_base_url（来自环境变量 PUBLIC_API_BASE_URL）
        └─ 前端持久化到 Storage(md:api_base_url)
             └─ 后续请求 getBase() 直接读取该地址
```

- 首次启动若本地尚无缓存地址，回退到 `miniapp/config.ts` 的 `PROD_DEFAULT_URL`（留空则需后端已配置 `PUBLIC_API_BASE_URL`）。
- 后端未配置且前端也无引导地址时，`getBase()` 会立刻弹窗阻断首个请求并抛出明确错误，而不是静默打到无效域名。

#### 部署步骤

1. 后端设置环境变量 `PUBLIC_API_BASE_URL`（公开生产域名，如 `https://api.your-company.com/api`），重启服务。
2. 前端 `miniapp/config.ts` 的 `PROD_DEFAULT_URL` 如需首启即连通，可填入同样的公开生产域名（**仅明文公开域名，绝非密钥**）；否则留空，依赖登录下发。
3. 微信公众平台 → 开发设置 → 服务器域名，将生产域名加入 `request` / `uploadFile` / `downloadFile` 三个白名单。

---

## 🔐 生产配置方案说明（无本地密钥）

> 历史上本项目曾在 `miniapp/utils/env.ts` 用 KDF + 三级加密把生产地址存为密文、靠注入 Seed 解密。
> 该方案本质只是「防误提交」的混淆层（且 SHA-256 / FNV-1a 两条派生路径不一致会导致旧端解密失败），
> 已重构为「后端登录下发」：客户端零密钥、零加密逻辑，生产地址完全由后端权威下发。

### Fail-Fast 安全拦截（request.ts）

如果后端未下发 `api_base_url`、前端也无 `PROD_DEFAULT_URL` 引导地址，
代码会**立刻阻断首个请求并弹 Modal 提示**，而不是静默失败打到无效域名：

```
wx.showModal({
  title: '请先配置生产环境',
  content:
    '生产环境 BaseURL 未配置\n' +
    '后端配置环境变量 PUBLIC_API_BASE_URL（公开生产域名）\n' +
    '或前端 miniapp/config.ts 的 PROD_DEFAULT_URL 填入公开生产域名',
  showCancel: false,
})
throw new Error('[config] 生产环境URL未配置（后端未下发 api_base_url，且无 PROD_DEFAULT_URL 引导地址）')
```
```

---

## 🛡️ 安全最佳实践清单（生产发版前必核）

- [ ] **生产配置走后端下发**：小程序不再硬编码/加密任何生产地址或密钥；`PUBLIC_API_BASE_URL` 由后端环境变量提供。
- [ ] **密钥只在服务端**：`JWT_SECRET_KEY`、`DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 等仅存在于后端环境变量，绝不下发前端、绝提交仓库（`.env` 已被 `.gitignore` 忽略）。
- [ ] **不要提交任何敏感文件**：`.gitignore` 已覆盖 `.env` / `*.key` / `*.pem` / `credentials.json` 等，发前再 `grep -r 'your-' . --include='*.env*'` 扫一遍确认无明文值。
- [ ] **小程序后台合法域名**：`request` / `uploadFile` / `downloadFile` 三项都要加。
- [ ] **TLS 必须 1.2+**：后端配 HTTPS（Let's Encrypt 免费签），不要裸 HTTP。
- [ ] **生产环境日志脱敏**：不要把 `Authorization` header、用户手机号打进可检索日志。

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

## 📘 API 文档

本项目 API 文档已**全量自动化**，不再手写维护（消除人工漂移）：

| 文档类型 | 访问方式 | 说明 |
| :--- | :--- | :--- |
| **Swagger UI** | `http://localhost:8000/docs` | 交互式 API 浏览器，可直接在网页中调用接口 |
| **ReDoc** | `http://localhost:8000/redoc` | 精美静态文档，适合对外分发 |
| **OpenAPI JSON** | `http://localhost:8000/openapi.json` | 机器可读规范文件（已导出至 `data/openapi.json`） |

**当前端点总数与分组**（由 `scripts/generate_docs.sh` 从 FastAPI OpenAPI 自动生成）：

<!-- AUTO-GEN-API-START -->
| 标签 | 接口数 | 说明 |
| :--- | :--- | :--- |
| Agent 对话 | 3 | 对话、流式、历史 |
| 认证 | 2 | 登录、Token 验证 |
| 企业信息 | 4 | 创建、查询 |
| 诊断 | 4 | 启动诊断、查询结果 |
| 执行计划 | 2 | 生成计划、查询计划 |
| 路线图 | 1 | 当前路线图 |
| 周计划 | 1 | 周计划查询 |
| 任务 | 3 | 任务详情、打卡、上传 |
| 工作台 | 1 | 看板数据汇总 |
| 复盘 | 6 | 上传材料、生成报告、查询 |
| 闭环业务 | 11 | 确认/编辑/重新生成计划、日程打卡/同步、文件/指标上传、复盘触发/采纳、反馈 |
| 未分类 | 2 | - |

> **接口总数：40 个**（含 2 个公开端点 + 38 个 JWT 鉴权端点）
<!-- AUTO-GEN-API-END -->

**更新 OpenAPI 文档**（代码变更后重新导出）：

```bash
python scripts/extract_routes.py --save-openapi data/openapi.json
```

> 此 OpenAPI 文件可用于 CI 流水线中的自动漂移检查：比对当前路由与上次提交的 `data/openapi.json`，发现差异即告警。

---

## 🛡️ 防漂移机制

项目内置三层自动化防漂移机制，确保代码、配置、文档三者始终同步：

### 机制 1：基线上下文注入

每次 AI 编程任务前，在 prompt 中注入三块基线上下文（模板见 `.workbuddy/PROMPT_TEMPLATE.md`）：
- 设计诉求摘要（功能定义 + 架构设计）
- 当前基准事实（页面清单 / 依赖声明 / API 路由 / 环境变量）
- 上一次一致性报告结论

### 机制 2：提交前自动漂移检查

```bash
bash scripts/check_drift.sh    # 5 维度检查，非零退出即阻断
```

| # | 检查维度 | 校验内容 |
|:---|:---|:---|
| 1 | 依赖漂移 | `pyproject.toml` vs `src/` 实际 import（AST 扫描） |
| 2 | 页面漂移 | `app.json` 声明 vs `pages/` 下 `.wxml` 文件数 |
| 3 | 类型漂移 | TypeScript 中 `@deprecated` 残留 |
| 4 | 安全漂移 | 硬编码密钥模式（`ghp_`/`sk-` 等） |
| 5 | 配置漂移 | `.env.example` vs `os.getenv()` 引用（AST 提取） |

已集成到 Git pre-commit hook（`.git/hooks/pre-commit`），`git commit` 时自动触发。漂移存在时返回非零，阻塞提交。

### 机制 3：文档自动生成

```bash
bash scripts/generate_docs.sh  # 从代码源自动刷新 README
```

从 `miniapp/app.json` 自动提取页面清单，从 `data/openapi.json` 自动生成 API 端点分组表，写入 README 的对应 `<!-- AUTO-GEN-* -->` 标记位。可在 CI 中集成，确保每次合并前文档已刷新。

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
