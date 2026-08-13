# AI 编程任务 Prompt 模板

> 在发起任何 AI 编程任务时，将以下三块内容固定附加到 prompt 中，作为基线上下文。

---

## 一、设计诉求摘要

### 项目定位
AI 营销战略执行智能体：企业营销诊断 → 12周季度路线图 → 每日任务执行 → AI智能复盘 的全闭环系统。

### 技术架构
- **前端**：微信原生小程序 + TypeScript（strict: true），7 个页面（4 主包 + 3 分包），自研响应式 Store
- **后端**：FastAPI + LangGraph Agent 编排 + ChromaDB 向量记忆库
- **数据**：SQLite（aiosqlite 异步驱动）
- **AI**：DeepSeek（文本主模型）+ OpenAI GPT-4o（多模态）

### 核心闭环
```
自然语言输入 → 诊断(5维雷达) → 12周路线图 → 每日任务打卡 → 周/月/季复盘 → 校准下阶段
```

### 关键设计原则
- 对话优先：前端以 chat 页为核心，所有业务动作通过自然语言驱动
- SSE 流式：后端 Agent 通过 text/event-stream 逐帧回复
- 安全第一：JWT 真实签名，生产配置走后端下发，无前端硬编码密钥
- 异步全链路：FastAPI async def + AsyncSession

---

## 二、当前基准事实

> **修改代码时务必参考以下事实，不得与之冲突。**

### 2.1 小程序页面清单（app.json）

| 类型 | 路径 | 说明 |
|:---|:---|:---|
| 主包 | pages/chat/index | 对话主界面（tabBar） |
| 主包 | pages/dashboard/index | 数据看板（tabBar） |
| 主包 | pages/schedule/index | 每周日程（tabBar） |
| 主包 | pages/onboarding/index | 登录页 |
| 分包 | pages/detail/diagnosis-detail/index | 诊断详情 |
| 分包 | pages/detail/review-detail/index | 复盘详情 |
| 分包 | pages/detail/plan-detail/index | 计划详情 |

### 2.2 pyproject.toml 运行时依赖

```
fastapi>=0.110, uvicorn[standard]>=0.27, pydantic>=2.0,
python-multipart>=0.0.19, httpx>=0.27,
SQLAlchemy[asyncio]>=2.0.36, aiosqlite>=0.20.0,
openai>=1.58.1, langgraph>=1.0, langchain-core>=0.3, chromadb>=1.5,
jinja2>=3.1.4, PyJWT>=2.8.0
```

### 2.3 API 路由清单（40 个端点）

| 标签 | 接口数 | 关键端点 |
|:---|:---|:---|
| Agent 对话 | 3 | POST /api/agent/chat, POST /api/agent/chat/stream, GET /api/agent/history |
| 认证 | 2 | POST /api/auth/login, GET /api/auth/verify |
| 企业信息 | 4 | POST/GET /api/business/... |
| 诊断 | 4 | POST /api/diagnosis/start, GET /api/diagnosis/{id} |
| 执行计划 | 2 | POST /api/plan/..., GET /api/plan/{id} |
| 路线图 | 1 | GET /api/roadmap |
| 周计划 | 1 | GET /api/plan/week |
| 任务 | 3 | GET /api/task/{id}, PUT /api/task/{id}/checkin |
| 工作台 | 1 | GET /api/dashboard |
| 复盘 | 6 | POST /api/review/trigger, GET /api/review/{id} |
| 闭环业务 | 11 | confirm/edit/regenerate plan, schedule sync/checkin, upload, feedback |
| 系统 | 2 | GET /, GET /api/health |

OpenAPI 规范文件：`data/openapi.json`

### 2.4 环境变量（26 项，.env.example）

LLM: LLM_TEXT_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, LLM_VISION_MODEL, OPENAI_API_KEY, OPENAI_API_BASE, LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_TIMEOUT
数据库: DATABASE_URL
鉴权: JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_DAYS
微信: WECHAT_APPID, WECHAT_SECRET
部署: PUBLIC_API_BASE_URL, CORS_ALLOWED_ORIGINS, MAX_UPLOAD_SIZE_MB
Agent: CHROMA_PERSIST_DIR, MARKETING_KNOWLEDGE_FILE, AGENT_EMBEDDING_PROVIDER, AGENT_KNOWLEDGE_TOP_K, AGENT_HISTORY_WINDOW, AGENT_REBUILD_KNOWLEDGE, AGENT_USE_LLM_INTENT
调试: DEBUG

---

## 三、上次一致性报告结论

> 详见仓库根目录 `一致性报告.md`（2026-08-10）

### 已修复（10/10 ✅）
1. pyproject.toml 依赖声明完整
2. CORS 安全配置（allow_origins 白名单 + allow_credentials=False）
3. 数据库异步引擎（create_async_engine + AsyncSessionLocal）
4. 文件上传安全（magic byte + resolve 路径边界）
5. 前端加密方案（删除 env.ts/encrypt*.js，改后端下发）
6. JWT 鉴权（真实 jwt.encode/decode，8 个 router 全部加鉴权依赖）
7. API 端点（路由顺序修复，OpenAPI 自动提取）
8. 类型定义（12 个 @deprecated 清零，前后端字段对齐）
9. 配置文件（.env.example 26/26 覆盖）
10. 一致性报告

### 已知遗留（5 项，非阻塞）
- P2: 版本号五处不一致
- P2: 任务模块仍含 mock 桩
- P2: 测试无 DB 隔离
- P2: API 路由层零测试
- P3: dashboard.py 空 if 块

---

## 四、强制约束

**每次修改代码后，必须：**

1. **列出受影响文档清单**，包括但不限于：
   - README.md（如涉及 API 变更 / 页面变更 / 架构变更）
   - 一致性报告.md（如涉及重大架构变更）
   - .env.example（如涉及环境变量）
   - app.json（如涉及页面增删）
   - pyproject.toml（如涉及依赖变更）

2. **检查以下漂移点并同步更新**：
   - [ ] pyproject.toml 依赖 vs 实际 import（`python scripts/check_dependency_drift.py`）
   - [ ] app.json 页面数 vs .wxml 文件数
   - [ ] .env.example vs 代码中 os.getenv() 引用
   - [ ] 前端类型定义 vs 后端 to_dict() 输出字段
   - [ ] README API 章节 vs data/openapi.json

3. **运行全量回归**：
   ```bash
   pytest -q                    # 后端 173 用例
   cd miniapp && npm run rebuild # 前端 TS 编译
   ```

4. **提交前运行漂移检查**：
   ```bash
   bash scripts/check_drift.sh
   ```
