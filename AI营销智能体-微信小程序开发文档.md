# AI企业营销战略执行智能体 — 微信小程序开发文档

**版本**：V3.0（正式版）
**更新日期**：2026年7月31日
**文档状态**：已定稿，进入开发实施阶段

---

## 文档修订记录

| 版本 | 日期 | 修订内容 | 作者 |
| :--- | :--- | :--- | :--- |
| V1.0 | 2026-07-15 | 初始版本，搭建小程序基础框架 | - |
| V2.0 | 2026-07-22 | 补充数据模型与API接口定义 | - |
| V3.0 | 2026-07-31 | 完整版：含页面设计、组件规范、状态管理、MVP计划 | - |

---

## 目录

- [一、项目概述](#一项目概述)
- [二、技术架构](#二技术架构)
- [三、项目结构](#三项目结构)
- [四、页面设计](#四页面设计)
- [五、组件设计](#五组件设计)
- [六、API接口设计](#六api接口设计)
- [七、数据管理与状态流转](#七数据管理与状态流转)
- [八、核心业务流程](#八核心业务流程)
- [九、开发规范](#九开发规范)
- [十、MVP开发计划](#十mvp开发计划)
- [十一、附录](#十一附录)

---

## 一、项目概述

### 1.1 产品定位

本小程序是"AI企业营销战略执行智能体"的前端应用，面向中小企业老板/营销负责人，提供从营销诊断、季度路线图生成、每周任务执行到月度复盘的全链路工具。

### 1.2 核心价值

- **诊断可视化**：5维度营销健康度评分，一目了然
- **路线图跟踪**：12周季度作战计划，三阶段进度可视
- **任务可执行**：每周7天精确到小时的任务清单，打卡追踪
- **复盘闭环**：周/月/季复盘上传，AI智能校准

### 1.3 目标用户

| 维度 | 描述 |
| :--- | :--- |
| 用户角色 | 中小企业老板、营销负责人、个体创业者 |
| 技术水平 | 无需技术背景，会用微信即可 |
| 使用场景 | 每日5-10分钟查看/完成任务，每周一次复盘 |
| 核心诉求 | 知道"做什么"和"怎么做"，且能追踪执行进度 |

### 1.4 设计原则

1. **极简优先**：每屏只解决一件事，信息密度适中
2. **行动导向**：所有页面最终指向"完成任务"这一动作
3. **进度可见**：关键页面上方始终展示阶段进度条
4. **老板友好**：禁止行业黑话，语言通俗直白

---

## 二、技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────┐
│              微信小程序（前端）                │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐  │
│  │  Pages  │ │Components│ │   Utils/API   │  │
│  └────┬────┘ └────┬────┘ └───────┬───────┘  │
│       │           │              │           │
│  ┌────┴───────────┴──────────────┴───────┐  │
│  │         全局状态管理 (globalData)       │  │
│  │     + 本地缓存 (wx.setStorageSync)      │  │
│  └───────────────────┬───────────────────┘  │
└──────────────────────┼──────────────────────┘
                       │ HTTPS (wx.request)
                       ▼
┌─────────────────────────────────────────────┐
│            后端服务 (Python/FastAPI)          │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ 诊断Agent │ │ 执行Agent │ │  复盘Agent   │  │
│  └──────────┘ └──────────┘ └─────────────┘  │
│  ┌──────────────────────────────────────┐   │
│  │     数据库 (PostgreSQL/SQLite)        │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层级 | 技术 | 说明 |
| :--- | :--- | :--- |
| **框架** | 原生微信小程序 | 无需跨端，原生性能最优 |
| **UI组件库** | Vant Weapp | 成熟稳定，适配老板级用户的大字体需求 |
| **图表** | ec-canvas (ECharts) | 雷达图、进度条、柱状图 |
| **状态管理** | globalData + Behavior | 轻量方案，避免引入MobX等增加复杂度 |
| **本地存储** | wx.setStorageSync | 缓存用户信息、当前周期数据 |
| **网络请求** | wx.request 封装 | 统一拦截、Token管理、错误处理 |
| **后端** | Python + FastAPI | 异步高性能，与AI Agent无缝对接 |
| **AI模型** | DeepSeek/通义千问 API | 通过后端调用，小程序不直连 |

### 2.3 环境配置

```json
// project.config.json 关键配置
{
  "miniprogramRoot": "miniprogram/",
  "compileType": "miniprogram",
  "appid": "wxXXXXXXXXXXXX",
  "projectname": "ai-marketing-agent",
  "setting": {
    "es6": true,
    "enhance": true,
    "postcss": true,
    "minified": true,
    "urlCheck": true
  }
}
```

**环境区分**：

| 环境 | 请求域名 | 用途 |
| :--- | :--- | :--- |
| 开发 | `http://localhost:8000` | 本地开发调试 |
| 测试 | `https://test-api.example.com` | 灰度测试 |
| 生产 | `https://api.example.com` | 正式上线 |

---

## 三、项目结构

### 3.1 目录结构

```
ai-marketing-agent/
├── miniprogram/
│   ├── app.js                          # 小程序入口
│   ├── app.json                        # 全局配置
│   ├── app.wxss                        # 全局样式
│   │
│   ├── pages/                          # 页面
│   │   ├── index/                      # 首页（工作台）
│   │   │   ├── index.js
│   │   │   ├── index.json
│   │   │   ├── index.wxml
│   │   │   └── index.wxss
│   │   ├── diagnosis/                  # 营销诊断页
│   │   │   ├── diagnosis.js
│   │   │   ├── diagnosis.json
│   │   │   ├── diagnosis.wxml
│   │   │   └── diagnosis.wxss
│   │   ├── roadmap/                    # 季度路线图页
│   │   │   ├── roadmap.js
│   │   │   ├── roadmap.json
│   │   │   ├── roadmap.wxml
│   │   │   └── roadmap.wxss
│   │   ├── weekly-plan/               # 本周任务页
│   │   │   ├── weekly-plan.js
│   │   │   ├── weekly-plan.json
│   │   │   ├── weekly-plan.wxml
│   │   │   └── weekly-plan.wxss
│   │   ├── task-detail/               # 任务详情页
│   │   │   ├── task-detail.js
│   │   │   ├── task-detail.json
│   │   │   ├── task-detail.wxml
│   │   │   └── task-detail.wxss
│   │   ├── review/                    # 复盘页
│   │   │   ├── review.js
│   │   │   ├── review.json
│   │   │   ├── review.wxml
│   │   │   └── review.wxss
│   │   ├── profile/                   # 企业信息页
│   │   │   ├── profile.js
│   │   │   ├── profile.json
│   │   │   ├── profile.wxml
│   │   │   └── profile.wxss
│   │   └── onboarding/               # 首次启动引导页
│   │       ├── onboarding.js
│   │       ├── onboarding.json
│   │       ├── onboarding.wxml
│   │       └── onboarding.wxss
│   │
│   ├── components/                    # 自定义组件
│   │   ├── progress-bar/             # 阶段进度条
│   │   ├── task-card/                # 任务卡片
│   │   ├── radar-chart/              # 雷达图
│   │   ├── phase-timeline/           # 阶段时间线
│   │   ├── health-score/            # 健康度评分卡
│   │   └── empty-state/             # 空状态占位
│   │
│   ├── utils/                        # 工具函数
│   │   ├── request.js                # 网络请求封装
│   │   ├── auth.js                   # 登录鉴权
│   │   ├── storage.js                # 本地缓存管理
│   │   ├── date.js                   # 日期处理
│   │   └── constants.js              # 常量定义
│   │
│   ├── behaviors/                    # Behavior 复用
│   │   └── user-info.js              # 用户信息共享行为
│   │
│   ├── assets/                       # 静态资源
│   │   ├── icons/
│   │   └── images/
│   │
│   └── ec-canvas/                    # ECharts 图表组件
│
├── server/                           # 后端服务（独立仓库或子目录）
│   ├── src/
│   │   ├── agents/                   # AI智能体
│   │   ├── models/                   # 数据模型
│   │   ├── services/                 # 业务逻辑
│   │   └── api/                      # API路由
│   ├── prompts/                      # Prompt模板文件
│   ├── config/                       # 配置文件
│   └── tests/                        # 测试
│
└── project.config.json               # 项目配置
```

### 3.2 app.json 全局配置

```json
{
  "pages": [
    "pages/index/index",
    "pages/onboarding/onboarding",
    "pages/diagnosis/diagnosis",
    "pages/roadmap/roadmap",
    "pages/weekly-plan/weekly-plan",
    "pages/task-detail/task-detail",
    "pages/review/review",
    "pages/profile/profile"
  ],
  "window": {
    "navigationBarTitleText": "AI营销战略助手",
    "navigationBarBackgroundColor": "#1989fa",
    "navigationBarTextStyle": "white",
    "backgroundColor": "#f7f8fa",
    "enablePullDownRefresh": false
  },
  "tabBar": {
    "color": "#7d7e80",
    "selectedColor": "#1989fa",
    "backgroundColor": "#ffffff",
    "borderStyle": "white",
    "list": [
      {
        "pagePath": "pages/index/index",
        "text": "工作台",
        "iconPath": "assets/icons/home.png",
        "selectedIconPath": "assets/icons/home-active.png"
      },
      {
        "pagePath": "pages/roadmap/roadmap",
        "text": "路线图",
        "iconPath": "assets/icons/roadmap.png",
        "selectedIconPath": "assets/icons/roadmap-active.png"
      },
      {
        "pagePath": "pages/profile/profile",
        "text": "我的",
        "iconPath": "assets/icons/profile.png",
        "selectedIconPath": "assets/icons/profile-active.png"
      }
    ]
  },
  "networkTimeout": {
    "request": 30000,
    "uploadFile": 60000
  },
  "permission": {
    "scope.userInfo": { "desc": "用于个性化营销建议" }
  }
}
```

---

## 四、页面设计

### 4.1 页面总览

| 页面 | 路径 | 功能 | TabBar | 核心组件 |
| :--- | :--- | :--- | :--- | :--- |
| 首次引导 | `/pages/onboarding` | 企业信息采集，启动诊断 | 否 | 表单、步骤条 |
| 工作台 | `/pages/index` | 今日任务概览 + 阶段进度 | 是 | 进度条、任务卡片 |
| 营销诊断 | `/pages/diagnosis` | 5维度健康度评分展示 | 否 | 雷达图、评分卡 |
| 季度路线图 | `/pages/roadmap` | 12周三阶段作战计划 | 是 | 时间线、阶段卡 |
| 本周任务 | `/pages/weekly-plan` | 7天任务清单 + 打卡 | 否 | 任务卡片、日历 |
| 任务详情 | `/pages/task-detail` | 单任务详情 + 执行步骤 | 否 | 步骤列表、打卡 |
| 复盘 | `/pages/review` | 周/月复盘表单上传 | 否 | 表单、图片上传 |
| 企业信息 | `/pages/profile` | 企业资料 + 使用统计 | 是 | 信息展示、统计 |

### 4.2 首次引导页 (Onboarding)

**触发条件**：首次打开小程序 / 未完成企业信息填写

**页面结构**：

```
┌─────────────────────────────┐
│        [Logo + 标题]          │
│   AI营销战略执行智能体         │
│   让每个老板都有自己的营销军师   │
├─────────────────────────────┤
│  步骤 1/4 → 企业基本信息       │
│  ┌───────────────────────┐  │
│  │ 企业名称：[          ]  │  │
│  │ 所属行业：[请选择 ▼  ]  │  │
│  │ 所在城市：[请选择 ▼  ]  │  │
│  │ 团队规模：[请选择 ▼  ]  │  │
│  └───────────────────────┘  │
├─────────────────────────────┤
│  步骤 2/4 → 产品与目标客户     │
│  ┌───────────────────────┐  │
│  │ 主营产品：[          ]  │  │
│  │ 客单价范围：[请选择▼ ]  │  │
│  │ 目标客户画像：[多行  ]  │  │
│  └───────────────────────┘  │
├─────────────────────────────┤
│  步骤 3/4 → 当前营销现状       │
│  ┌───────────────────────┐  │
│  │ 现有渠道：[多选标签  ]  │  │
│  │ 月营销预算：[请选择▼ ]  │  │
│  │ 最大痛点：[多行输入  ]  │  │
│  └───────────────────────┘  │
├─────────────────────────────┤
│  步骤 4/4 → 确认并启动诊断     │
│  ┌───────────────────────┐  │
│  │  [信息汇总预览]        │  │
│  │  ✅ 企业信息已填写     │  │
│  │  ✅ 产品信息已填写     │  │
│  │  ✅ 营销现状已填写     │  │
│  └───────────────────────┘  │
│      [开始AI诊断 →]          │
└─────────────────────────────┘
```

**关键逻辑**：

```javascript
// pages/onboarding/onboarding.js
Page({
  data: {
    currentStep: 0,
    formData: {
      company_name: '',
      industry: '',
      city: '',
      team_size: '',
      main_product: '',
      price_range: '',
      target_customer: '',
      current_channels: [],
      monthly_budget: '',
      biggest_pain: ''
    },
    industries: ['餐饮', '零售', '教育', '美容', '服务', '制造', '其他'],
    teamSizes: ['1-5人', '6-20人', '21-50人', '51-200人', '200人以上']
  },

  onNextStep() {
    const { currentStep, formData } = this.data;
    if (currentStep < 3) {
      this.setData({ currentStep: currentStep + 1 });
    }
  },

  async onSubmit() {
    const { formData } = this.data;
    // 1. 保存企业信息到后端
    const res = await request.post('/api/business/create', formData);
    // 2. 触发AI诊断
    const diagnosis = await request.post('/api/diagnosis/start', {
      business_id: res.data.business_id
    });
    // 3. 缓存诊断结果
    wx.setStorageSync('diagnosis_result', diagnosis.data);
    // 4. 跳转诊断结果页
    wx.redirectTo({ url: '/pages/diagnosis/diagnosis' });
  }
});
```

### 4.3 工作台首页 (Index)

**定位**：用户每天打开小程序的第一眼，看到"今天该做什么"

**页面结构**：

```
┌─────────────────────────────────┐
│  顶部导航栏：AI营销战略助手        │
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │
│  │  季度进度条                │  │
│  │  Phase 1 · 启动期 · 第3周  │  │
│  │  ████████░░░░░░░░░░ 25%  │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  今日聚焦                        │
│  ┌───────────────────────────┐  │
│  │  📋 完成竞品小红书账号分析   │  │
│  │  09:00-09:30 │ 未开始       │  │
│  │  [查看详情 →]  [✅ 打卡]    │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  📝 撰写第一条种草笔记      │  │
│  │  14:00-15:00 │ 未开始       │  │
│  │  [查看详情 →]  [✅ 打卡]    │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  本周完成率                      │
│  ┌───────────────────────────┐  │
│  │  周一 ▓▓▓▓░  3/5          │  │
│  │  周二 ▓▓░░░  2/5          │  │
│  │  周三 ▓▓▓▓▓  5/5  ✅      │  │
│  │  周四 ▓▓▓░░  3/5          │  │
│  │  周五 ░░░░░  0/3          │  │
│  │  周六 ░░░░░  0/2          │  │
│  │  周日 — 休息 —             │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  快捷入口                        │
│  [路线图] [诊断] [复盘] [我的]    │
└─────────────────────────────────┘
```

**关键逻辑**：

```javascript
// pages/index/index.js
const app = getApp();

Page({
  data: {
    phaseInfo: null,        // 当前阶段信息
    weeklyProgress: 0,       // 季度进度百分比
    todayTasks: [],          // 今日任务列表
    weekCompletion: [],      // 本周每天完成率
    currentWeek: 0           // 当前第几周
  },

  onLoad() {
    this.loadDashboard();
  },

  onShow() {
    // 每次显示页面时刷新数据
    this.loadDashboard();
  },

  async loadDashboard() {
    try {
      wx.showLoading({ title: '加载中...' });
      const res = await request.get('/api/dashboard');
      this.setData({
        phaseInfo: res.data.phase_info,
        weeklyProgress: res.data.weekly_progress,
        todayTasks: res.data.today_tasks,
        weekCompletion: res.data.week_completion,
        currentWeek: res.data.current_week
      });
    } catch (err) {
      this.showError(err);
    } finally {
      wx.hideLoading();
    }
  },

  async onCheckIn(e) {
    const { taskId } = e.currentTarget.dataset;
    try {
      await request.post('/api/task/checkin', { task_id: taskId });
      wx.showToast({ title: '打卡成功！', icon: 'success' });
      this.loadDashboard(); // 刷新数据
    } catch (err) {
      this.showError(err);
    }
  },

  onPullDownRefresh() {
    this.loadDashboard().then(() => {
      wx.stopPullDownRefresh();
    });
  }
});
```

### 4.4 营销诊断页 (Diagnosis)

**页面结构**：

```
┌─────────────────────────────────┐
│  ← 返回    营销诊断报告            │
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │
│  │      综合健康度             │  │
│  │       ╭───────╮           │  │
│  │      │   72    │          │  │
│  │      │  /100   │          │  │
│  │       ╰───────╯           │  │
│  │  营销基础尚可，执行力度不足   │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  五维诊断雷达图                   │
│  ┌───────────────────────────┐  │
│  │        定位                 │  │
│  │       ╱  85  ╲             │  │
│  │  产品 ╱       ╲ 渠道        │  │
│  │   70 ║   ★    ║ 55        │  │
│  │       ╲       ╱            │  │
│  │        ╲  60  ╱            │  │
│  │       内容   转化            │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  Top 3 核心问题                  │
│  ┌───────────────────────────┐  │
│  │  🔴 渠道单一，过度依赖线下   │  │
│  │  → 建议：开通小红书+抖音    │  │
│  ├───────────────────────────┤  │
│  │  🟡 内容产出不规律           │  │
│  │  → 建议：建立周更内容日历    │  │
│  ├───────────────────────────┤  │
│  │  🟢 转化路径不清晰           │  │
│  │  → 建议：设计标准化成交话术  │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│       [查看季度路线图 →]         │
└─────────────────────────────────┘
```

**雷达图组件集成**：

```javascript
// pages/diagnosis/diagnosis.js
import * as echarts from '../../ec-canvas/echarts';

function initRadarChart(canvas, width, height, dpr) {
  const chart = echarts.init(canvas, null, { width, height, dpr });
  canvas.setChart(chart);

  const option = {
    radar: {
      indicator: [
        { name: '定位', max: 100 },
        { name: '产品', max: 100 },
        { name: '渠道', max: 100 },
        { name: '内容', max: 100 },
        { name: '转化', max: 100 }
      ],
      shape: 'polygon',
      splitNumber: 4
    },
    series: [{
      type: 'radar',
      data: [{
        value: [85, 70, 55, 60, 65],
        areaStyle: { color: 'rgba(25, 137, 250, 0.3)' },
        lineStyle: { color: '#1989fa', width: 2 }
      }]
    }]
  };
  chart.setOption(option);
  return chart;
}

Page({
  data: {
    ec: { onInit: initRadarChart },
    diagnosis: null
  },

  onLoad() {
    const cached = wx.getStorageSync('diagnosis_result');
    if (cached) {
      this.setData({ diagnosis: cached });
    } else {
      this.loadDiagnosis();
    }
  },

  async loadDiagnosis() {
    const res = await request.get('/api/diagnosis/latest');
    this.setData({ diagnosis: res.data });
    wx.setStorageSync('diagnosis_result', res.data);
  }
});
```

### 4.5 季度路线图页 (Roadmap)

**页面结构**：

```
┌─────────────────────────────────┐
│  ← 返回   季度作战路线图           │
├─────────────────────────────────┤
│  季度目标：建立线上获客体系        │
│  周期：第1周 / 共12周             │
├─────────────────────────────────┤
│                                 │
│  ●━━━ Phase 1：启动期 ━━━━━     │
│  │   第1-4周                     │
│  │  ┌─────────────────────┐     │
│  │  │ ✅ 账号基建           │     │
│  │  │ ✅ 竞品调研           │     │
│  │  │ 🔄 核心素材库建立     │     │
│  │  │ ⬜ 话术体系建立       │     │
│  │  └─────────────────────┘     │
│  │                               │
│  ●━━━ Phase 2：放量期 ━━━━━     │
│  │   第5-8周                     │
│  │  ┌─────────────────────┐     │
│  │  │ ⬜ 规律内容发布       │     │
│  │  │ ⬜ 获取首批咨询       │     │
│  │  │ ⬜ 启动转介绍机制     │     │
│  │  └─────────────────────┘     │
│  │                               │
│  ●━━━ Phase 3：收获+裂变期 ━━    │
│      第9-12周                    │
│     ┌─────────────────────┐     │
│     │ ⬜ 重点追单转化       │     │
│     │ ⬜ 设计裂变活动       │     │
│     │ ⬜ 复盘成功案例       │     │
│     └─────────────────────┘     │
│                                 │
└─────────────────────────────────┘
```

### 4.6 本周任务页 (Weekly Plan)

**页面结构**：

```
┌─────────────────────────────────┐
│  ← 返回   本周任务 · 第3周        │
├─────────────────────────────────┤
│  周任务完成率：60%               │
│  ████████████░░░░░░░░ 6/10     │
├─────────────────────────────────┤
│  ┌─ 周一 7/29 ─────────────┐    │
│  │  ✅ 09:00 竞品分析       │    │
│  │  ✅ 14:00 撰写种草笔记   │    │
│  │  ✅ 17:00 发布并复盘     │    │
│  └─────────────────────────┘    │
│  ┌─ 周二 7/30 ─────────────┐    │
│  │  ✅ 10:00 回复评论       │    │
│  │  ✅ 15:00 优化话术       │    │
│  │  🔄 19:00 拍摄产品视频   │    │
│  └─────────────────────────┘    │
│  ┌─ 周三 7/31 (今天) ──────┐    │
│  │  ⬜ 09:00 数据分析       │    │
│  │  ⬜ 14:00 内容选题策划   │    │
│  │  ⬜ 17:00 客户回访       │    │
│  └─────────────────────────┘    │
│  ┌─ 周四 8/1 ──────────────┐    │
│  │  ⬜ 10:00 ...            │    │
│  └─────────────────────────┘    │
│  ...                            │
│  ┌─ 周日 8/4 ──────────────┐    │
│  │  💤 休息日               │    │
│  └─────────────────────────┘    │
├─────────────────────────────────┤
│  [📋 本周复盘]                    │
└─────────────────────────────────┘
```

### 4.7 任务详情页 (Task Detail)

**页面结构**：

```
┌─────────────────────────────────┐
│  ← 返回    任务详情               │
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │
│  │  📋 竞品小红书账号分析      │  │
│  │  时间：09:00-09:30         │  │
│  │  状态：未开始               │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  怎么做                          │
│  打开小红书，搜索3个同行业对手     │
│  账号，记录他们的爆款内容规律。    │
├─────────────────────────────────┤
│  执行步骤                        │
│  ┌───────────────────────────┐  │
│  │ ① 打开小红书APP            │  │
│  │ ② 搜索行业关键词           │  │
│  │ ③ 找到3个粉丝>1万的竞品    │  │
│  │ ④ 记录近7天爆款笔记标题    │  │
│  │ ⑤ 分析发布时间和频率       │  │
│  │ ⑥ 截图保存到素材库         │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  执行记录                        │
│  ┌───────────────────────────┐  │
│  │  [📸 拍照记录]              │  │
│  │  [📝 文字记录]              │  │
│  │  已上传：2张截图            │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│        [✅ 标记完成]              │
└─────────────────────────────────┘
```

### 4.8 复盘页 (Review)

**页面结构**：

```
┌─────────────────────────────────┐
│  ← 返回    周复盘 · 第3周         │
├─────────────────────────────────┤
│  复盘类型：[周复盘 ▼]             │
├─────────────────────────────────┤
│  1. 本周完成了哪些任务？          │
│  ┌───────────────────────────┐  │
│  │  [多行文本输入]             │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  2. 哪些任务没完成？为什么？      │
│  ┌───────────────────────────┐  │
│  │  [多行文本输入]             │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  3. 本周最大的收获是什么？        │
│  ┌───────────────────────────┐  │
│  │  [多行文本输入]             │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  4. 遇到了什么困难？             │
│  ┌───────────────────────────┐  │
│  │  [多行文本输入]             │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  5. 数据截图（可选）             │
│  ┌───────────────────────────┐  │
│  │  [📷 上传截图]              │  │
│  │  [预览缩略图区域]           │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  6. AI智能分析（提交后生成）      │
│  ┌───────────────────────────┐  │
│  │  🤖 AI正在分析你的复盘...   │  │
│  │  [分析结果展示区域]         │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│        [提交复盘]                │
└─────────────────────────────────┘
```

---

## 五、组件设计

### 5.1 组件总览

| 组件名 | 路径 | 功能 | 使用页面 |
| :--- | :--- | :--- | :--- |
| progress-bar | `components/progress-bar/` | 季度阶段进度条 | 工作台、路线图 |
| task-card | `components/task-card/` | 单个任务卡片 | 工作台、本周任务 |
| radar-chart | `components/radar-chart/` | 五维诊断雷达图 | 诊断页 |
| phase-timeline | `components/phase-timeline/` | 阶段时间线 | 路线图 |
| health-score | `components/health-score/` | 健康度评分卡 | 诊断页 |
| empty-state | `components/empty-state/` | 空状态占位 | 全局 |
| week-calendar | `components/week-calendar/` | 周日历选择器 | 本周任务 |

### 5.2 进度条组件 (progress-bar)

**功能**：展示当前处于12周周期的哪个阶段、第几周

```javascript
// components/progress-bar/progress-bar.js
Component({
  properties: {
    currentWeek: { type: Number, value: 1 },
    totalWeeks: { type: Number, value: 12 },
    phaseIndex: { type: Number, value: 1 },
    phaseName: { type: String, value: '启动期' }
  },

  data: {
    progressPercent: 0,
    phaseRanges: [
      { start: 1, end: 4, name: '启动期' },
      { start: 5, end: 8, name: '放量期' },
      { start: 9, end: 12, name: '收获期' }
    ]
  },

  observers: {
    'currentWeek, totalWeeks': function(week, total) {
      const percent = Math.round((week / total) * 100);
      this.setData({ progressPercent: percent });
    }
  }
});
```

```xml
<!-- components/progress-bar/progress-bar.wxml -->
<view class="progress-bar-container">
  <view class="phase-label">
    <text class="phase-tag">Phase {{phaseIndex}}</text>
    <text class="phase-name">{{phaseName}}</text>
    <text class="week-info">第{{currentWeek}}周 / 共{{totalWeeks}}周</text>
  </view>
  <view class="progress-track">
    <view class="progress-fill" style="width: {{progressPercent}}%"></view>
    <!-- 阶段分割线 -->
    <view class="phase-divider" style="left: 33.3%"></view>
    <view class="phase-divider" style="left: 66.6%"></view>
  </view>
  <view class="phase-markers">
    <text class="marker">启动期</text>
    <text class="marker">放量期</text>
    <text class="marker">收获期</text>
  </view>
</view>
```

```css
/* components/progress-bar/progress-bar.wxss */
.progress-bar-container {
  padding: 24rpx;
  background: #fff;
  border-radius: 16rpx;
}
.phase-label {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 20rpx;
}
.phase-tag {
  background: #1989fa;
  color: #fff;
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
}
.phase-name {
  font-size: 30rpx;
  font-weight: 600;
  color: #323233;
}
.week-info {
  font-size: 24rpx;
  color: #969799;
  margin-left: auto;
}
.progress-track {
  position: relative;
  height: 16rpx;
  background: #ebedf0;
  border-radius: 8rpx;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1989fa, #07c160);
  border-radius: 8rpx;
  transition: width 0.3s ease;
}
.phase-divider {
  position: absolute;
  top: 0;
  width: 2rpx;
  height: 100%;
  background: #fff;
}
.phase-markers {
  display: flex;
  justify-content: space-between;
  margin-top: 12rpx;
}
.marker {
  font-size: 22rpx;
  color: #969799;
}
```

### 5.3 任务卡片组件 (task-card)

```javascript
// components/task-card/task-card.js
Component({
  properties: {
    task: {
      type: Object,
      value: {}
    },
    showCheckin: {
      type: Boolean,
      value: true
    }
  },

  methods: {
    onTapDetail() {
      this.triggerEvent('detail', { task: this.data.task });
    },
    onCheckin() {
      this.triggerEvent('checkin', { task: this.data.task });
    }
  }
});
```

```xml
<!-- components/task-card/task-card.wxml -->
<view class="task-card {{task.status === 'done' ? 'task-done' : ''}}">
  <view class="task-header" bindtap="onTapDetail">
    <view class="task-icon">
      <text wx:if="{{task.status === 'done'}}">✅</text>
      <text wx:elif="{{task.status === 'doing'}}">🔄</text>
      <text wx:else>⬜</text>
    </view>
    <view class="task-info">
      <text class="task-title">{{task.title}}</text>
      <view class="task-meta">
        <text class="task-time">{{task.time_slot}}</text>
        <text class="task-status status-{{task.status}}">
          {{task.status === 'done' ? '已完成' : task.status === 'doing' ? '进行中' : '未开始'}}
        </text>
      </view>
    </view>
  </view>
  <view class="task-actions" wx:if="{{showCheckin && task.status !== 'done'}}">
    <view class="btn-detail" catchtap="onTapDetail">查看详情</view>
    <view class="btn-checkin" catchtap="onCheckin">打卡</view>
  </view>
</view>
```

### 5.4 雷达图组件 (radar-chart)

```javascript
// components/radar-chart/radar-chart.js
import * as echarts from '../../ec-canvas/echarts';

Component({
  properties: {
    scores: {
      type: Object,
      value: { positioning: 0, product: 0, channel: 0, content: 0, conversion: 0 }
    }
  },

  data: {
    ecComponent: null,
    chart: null
  },

  lifetimes: {
    attached() {
      this.initChart();
    }
  },

  observers: {
    'scores': function(scores) {
      if (this.data.chart) {
        this.updateChart(scores);
      }
    }
  },

  methods: {
    initChart() {
      this.setData({
        ecComponent: this.selectComponent('#radar-chart')
      });
    },

    updateChart(scores) {
      const chart = this.data.chart;
      chart.setOption({
        series: [{
          data: [{
            value: [
              scores.positioning,
              scores.product,
              scores.channel,
              scores.content,
              scores.conversion
            ]
          }]
        }]
      });
    }
  }
});
```

---

## 六、API接口设计

### 6.1 接口规范

**统一响应格式**：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

| code | 说明 |
| :--- | :--- |
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 未登录 |
| 1003 | 权限不足 |
| 2001 | 诊断生成中 |
| 2002 | 诊断失败 |
| 5000 | 服务器内部错误 |

**请求封装**：

```javascript
// utils/request.js
const BASE_URL = {
  dev: 'http://localhost:8000',
  prod: 'https://api.example.com'
};

const config = {
  baseUrl: BASE_URL.prod,  // 根据环境切换
  timeout: 30000
};

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('auth_token');
    wx.request({
      url: config.baseUrl + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      timeout: options.timeout || config.timeout,
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      success(res) {
        if (res.statusCode === 200) {
          if (res.data.code === 0) {
            resolve(res.data);
          } else if (res.data.code === 1002) {
            // Token过期，跳转登录
            wx.removeStorageSync('auth_token');
            wx.redirectTo({ url: '/pages/onboarding/onboarding' });
            reject(res.data);
          } else {
            reject(res.data);
          }
        } else {
          reject({ code: -1, message: '网络错误' });
        }
      },
      fail(err) {
        reject({ code: -1, message: '网络请求失败', error: err });
      }
    });
  });
}

module.exports = {
  get: (url, data) => request({ url, method: 'GET', data }),
  post: (url, data) => request({ url, method: 'POST', data }),
  put: (url, data) => request({ url, method: 'PUT', data }),
  delete: (url, data) => request({ url, method: 'DELETE', data })
};
```

### 6.2 核心接口列表

| 接口 | 方法 | 路径 | 说明 |
| :--- | :--- | :--- | :--- |
| 微信登录 | POST | `/api/auth/login` | code换token |
| 创建企业 | POST | `/api/business/create` | 提交企业信息 |
| 获取企业信息 | GET | `/api/business/info` | 查询企业资料 |
| 启动诊断 | POST | `/api/diagnosis/start` | 触发AI诊断 |
| 获取诊断结果 | GET | `/api/diagnosis/latest` | 最新诊断报告 |
| 获取路线图 | GET | `/api/roadmap/current` | 当前季度路线图 |
| 获取本周计划 | GET | `/api/plan/weekly` | 7天任务清单 |
| 获取任务详情 | GET | `/api/task/detail` | 单任务详情 |
| 任务打卡 | POST | `/api/task/checkin` | 标记任务完成 |
| 上传执行记录 | POST | `/api/task/upload` | 上传截图/文字 |
| 提交复盘 | POST | `/api/review/submit` | 周月季复盘 |
| 获取复盘结果 | GET | `/api/review/latest` | AI分析结果 |
| 工作台数据 | GET | `/api/dashboard` | 首页聚合数据 |

### 6.3 关键接口详细定义

#### 6.3.1 微信登录

```javascript
// POST /api/auth/login
// Request
{ "code": "wx_login_code" }

// Response
{
  "code": 0,
  "data": {
    "token": "jwt_token_string",
    "user_id": "user_001",
    "is_new_user": true
  }
}
```

#### 6.3.2 启动诊断

```javascript
// POST /api/diagnosis/start
// Request
{
  "business_id": "biz_001",
  "company_name": "张三餐饮店",
  "industry": "餐饮",
  "city": "深圳",
  "team_size": "6-20人",
  "main_product": "社区快餐",
  "price_range": "20-50元",
  "target_customer": "周边写字楼上班族",
  "current_channels": ["线下门店", "美团外卖"],
  "monthly_budget": "5000-10000元",
  "biggest_pain": "没有线上获客渠道"
}

// Response
{
  "code": 0,
  "data": {
    "diagnosis_id": "diag_001",
    "status": "processing",
    "estimated_time": 30
  }
}
```

#### 6.3.3 获取诊断结果

```javascript
// GET /api/diagnosis/latest
// Response
{
  "code": 0,
  "data": {
    "diagnosis_id": "diag_001",
    "overall_score": 72,
    "overall_comment": "营销基础尚可，执行力度不足",
    "dimension_scores": {
      "positioning": 85,
      "product": 70,
      "channel": 55,
      "content": 60,
      "conversion": 65
    },
    "top_issues": [
      {
        "level": "high",
        "title": "渠道单一，过度依赖线下",
        "suggestion": "建议开通小红书+抖音账号"
      },
      {
        "level": "medium",
        "title": "内容产出不规律",
        "suggestion": "建议建立周更内容日历"
      },
      {
        "level": "low",
        "title": "转化路径不清晰",
        "suggestion": "建议设计标准化成交话术"
      }
    ],
    "quarterly_roadmap": {
      "overall_goal": "建立线上获客体系，月新增客户50人",
      "phases": [
        {
          "phase_index": 1,
          "phase_name": "启动期",
          "weeks_cover": "1-4",
          "key_actions": ["账号基建", "竞品调研", "素材库建立", "话术体系建立"],
          "success_criteria": "完成3个平台账号搭建，积累20条核心素材"
        },
        {
          "phase_index": 2,
          "phase_name": "放量期",
          "weeks_cover": "5-8",
          "key_actions": ["规律内容发布", "获取首批咨询", "启动转介绍"],
          "success_criteria": "每周稳定发布5条内容，获取10+有效咨询"
        },
        {
          "phase_index": 3,
          "phase_name": "收获期",
          "weeks_cover": "9-12",
          "key_actions": ["重点追单转化", "设计裂变活动", "复盘成功案例"],
          "success_criteria": "转化率提升至20%，完成1次裂变活动"
        }
      ]
    }
  }
}
```

#### 6.3.4 获取本周计划

```javascript
// GET /api/plan/weekly?week_number=3
// Response
{
  "code": 0,
  "data": {
    "week_number": 3,
    "phase_name": "启动期",
    "focus": "完成核心素材库搭建",
    "days": [
      {
        "day_index": 1,
        "day_name": "周一",
        "date": "2026-07-29",
        "focus": "准备工作",
        "tasks": [
          {
            "id": "task_001",
            "time_slot": "09:00-09:30",
            "title": "竞品小红书账号分析",
            "how_to": "打开小红书，搜索3个同行业对手账号，记录爆款内容规律",
            "checklist": [
              "打开小红书APP",
              "搜索行业关键词",
              "找到3个粉丝>1万的竞品",
              "记录近7天爆款笔记标题",
              "分析发布时间和频率",
              "截图保存到素材库"
            ],
            "status": "done"
          },
          {
            "id": "task_002",
            "time_slot": "14:00-15:00",
            "title": "撰写第一条种草笔记",
            "how_to": "参考竞品爆款结构，写一条产品种草笔记",
            "checklist": [
              "选择产品核心卖点",
              "撰写标题（15字以内）",
              "撰写正文（200字以内）",
              "配3-5张产品图",
              "发布并记录数据"
            ],
            "status": "pending"
          }
        ]
      }
      // ... 周二到周日数据
    ]
  }
}
```

#### 6.3.5 任务打卡

```javascript
// POST /api/task/checkin
// Request
{
  "task_id": "task_002",
  "notes": "已完成，笔记发布后2小时获得50+浏览",
  "images": ["upload_url_1", "upload_url_2"]
}

// Response
{
  "code": 0,
  "data": {
    "task_id": "task_002",
    "status": "done",
    "completed_at": "2026-07-31T14:35:00Z"
  }
}
```

#### 6.3.6 提交复盘

```javascript
// POST /api/review/submit
// Request
{
  "review_type": "weekly",
  "week_number": 3,
  "completed_tasks": "完成了竞品分析、笔记撰写、数据复盘",
  "incomplete_tasks": "产品视频拍摄推迟，因为设备未到位",
  "key_takeaway": "小红书种草笔记比预期效果好，单条50+浏览",
  "difficulties": "视频拍摄需要学习剪辑技能",
  "images": ["screenshot_url_1"]
}

// Response（同步返回提交确认，异步生成AI分析）
{
  "code": 0,
  "data": {
    "review_id": "review_001",
    "status": "submitted",
    "ai_analysis_status": "processing"
  }
}
```

#### 6.3.7 工作台聚合数据

```javascript
// GET /api/dashboard
// Response
{
  "code": 0,
  "data": {
    "current_week": 3,
    "total_weeks": 12,
    "phase_info": {
      "phase_index": 1,
      "phase_name": "启动期",
      "weeks_cover": "1-4"
    },
    "weekly_progress": 25,
    "today_tasks": [
      {
        "id": "task_003",
        "title": "数据分析",
        "time_slot": "09:00-09:30",
        "status": "pending"
      },
      {
        "id": "task_004",
        "title": "内容选题策划",
        "time_slot": "14:00-15:00",
        "status": "pending"
      }
    ],
    "week_completion": [
      { "day": "周一", "completed": 3, "total": 3, "rate": 100 },
      { "day": "周二", "completed": 2, "total": 3, "rate": 67 },
      { "day": "周三", "completed": 0, "total": 3, "rate": 0 },
      { "day": "周四", "completed": 0, "total": 2, "rate": 0 },
      { "day": "周五", "completed": 0, "total": 2, "rate": 0 },
      { "day": "周六", "completed": 0, "total": 2, "rate": 0 },
      { "day": "周日", "completed": 0, "total": 0, "rate": 0 }
    ]
  }
}
```

---

## 七、数据管理与状态流转

### 7.1 全局状态管理

采用 `app.globalData` + `Behavior` 的轻量方案：

```javascript
// app.js
App({
  globalData: {
    userInfo: null,
    authToken: null,
    businessInfo: null,
    currentPhase: null,
    currentWeek: null,
    diagnosisResult: null
  },

  onLaunch() {
    // 从本地缓存恢复登录状态
    const token = wx.getStorageSync('auth_token');
    if (token) {
      this.globalData.authToken = token;
      this.loadBusinessInfo();
    }
  },

  async loadBusinessInfo() {
    try {
      const res = await require('./utils/request').get('/api/business/info');
      this.globalData.businessInfo = res.data;
      this.globalData.currentPhase = res.data.current_phase;
      this.globalData.currentWeek = res.data.current_week;
    } catch (err) {
      console.error('加载企业信息失败:', err);
    }
  }
});
```

### 7.2 Behavior 复用

```javascript
// behaviors/user-info.js
module.exports = Behavior({
  data: {
    userInfo: null,
    businessInfo: null
  },

  lifetimes: {
    attached() {
      const app = getApp();
      this.setData({
        userInfo: app.globalData.userInfo,
        businessInfo: app.globalData.businessInfo
      });
    }
  }
});

// 在页面中使用
const userInfoBehavior = require('../../behaviors/user-info.js');

Page({
  behaviors: [userInfoBehavior],
  // 页面逻辑...
});
```

### 7.3 本地缓存策略

| 缓存Key | 数据 | 有效期 | 清除时机 |
| :--- | :--- | :--- | :--- |
| `auth_token` | JWT令牌 | 7天 | 退出登录/过期 |
| `user_info` | 用户基本信息 | 永久 | 退出登录 |
| `business_info` | 企业资料 | 1天 | 每次打开刷新 |
| `diagnosis_result` | 最新诊断结果 | 7天 | 重新诊断时更新 |
| `current_roadmap` | 季度路线图 | 7天 | 新季度开始时更新 |
| `weekly_plan_cache` | 本周计划 | 1天 | 每日刷新 |
| `last_checkin_time` | 最后打卡时间 | 永久 | 无需清除 |

```javascript
// utils/storage.js
const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_INFO: 'user_info',
  BUSINESS_INFO: 'business_info',
  DIAGNOSIS: 'diagnosis_result',
  ROADMAP: 'current_roadmap',
  WEEKLY_PLAN: 'weekly_plan_cache'
};

const TTL = {
  [STORAGE_KEYS.BUSINESS_INFO]: 86400000,    // 1天
  [STORAGE_KEYS.DIAGNOSIS]: 604800000,       // 7天
  [STORAGE_KEYS.ROADMAP]: 604800000,         // 7天
  [STORAGE_KEYS.WEEKLY_PLAN]: 86400000       // 1天
};

function set(key, data) {
  const payload = {
    data: data,
    timestamp: Date.now()
  };
  wx.setStorageSync(key, payload);
}

function get(key) {
  const payload = wx.getStorageSync(key);
  if (!payload) return null;

  const ttl = TTL[key];
  if (ttl && Date.now() - payload.timestamp > ttl) {
    wx.removeStorageSync(key);
    return null;
  }
  return payload.data;
}

function remove(key) {
  wx.removeStorageSync(key);
}

function clear() {
  Object.values(STORAGE_KEYS).forEach(key => {
    wx.removeStorageSync(key);
  });
}

module.exports = { set, get, remove, clear, STORAGE_KEYS };
```

### 7.4 数据模型定义

#### 企业信息 (Business)

```javascript
// models/business.js
class Business {
  constructor(data = {}) {
    this.id = data.id || '';
    this.company_name = data.company_name || '';
    this.industry = data.industry || '';
    this.city = data.city || '';
    this.team_size = data.team_size || '';
    this.main_product = data.main_product || '';
    this.price_range = data.price_range || '';
    this.target_customer = data.target_customer || '';
    this.current_channels = data.current_channels || [];
    this.monthly_budget = data.monthly_budget || '';
    this.biggest_pain = data.biggest_pain || '';
    this.created_at = data.created_at || '';
    this.current_phase = data.current_phase || 1;
    this.current_week = data.current_week || 1;
  }
}
module.exports = Business;
```

#### 季度路线图 (Roadmap)

```javascript
// models/roadmap.js
class Roadmap {
  constructor(data = {}) {
    this.id = data.id || '';
    this.business_id = data.business_id || '';
    this.overall_goal = data.overall_goal || '';
    this.start_date = data.start_date || '';
    this.total_weeks = data.total_weeks || 12;
    this.current_week = data.current_week || 1;
    this.phases = (data.phases || []).map(p => ({
      phase_index: p.phase_index,
      phase_name: p.phase_name,
      weeks_cover: p.weeks_cover,
      key_actions: p.key_actions || [],
      success_criteria: p.success_criteria || '',
      completed: p.completed || false
    }));
  }

  get currentPhase() {
    return this.phases.find(p =>
      this._weekInRange(this.current_week, p.weeks_cover)
    );
  }

  _weekInRange(week, range) {
    const [start, end] = range.split('-').map(Number);
    return week >= start && week <= end;
  }
}
module.exports = Roadmap;
```

#### 7天计划 (SevenDayPlan)

```javascript
// models/weekly-plan.js
class SevenDayPlan {
  constructor(data = {}) {
    this.id = data.id || '';
    this.business_id = data.business_id || '';
    this.week_number = data.week_number || 1;
    this.phase_name = data.phase_name || '';
    this.focus = data.focus || '';
    this.days = (data.days || []).map(d => ({
      day_index: d.day_index,
      day_name: d.day_name,
      date: d.date,
      focus: d.focus || '',
      tasks: (d.tasks || []).map(t => ({
        id: t.id,
        time_slot: t.time_slot || '',
        title: t.title || '',
        how_to: t.how_to || '',
        checklist: t.checklist || [],
        status: t.status || 'pending',
        completed_at: t.completed_at || null,
        notes: t.notes || '',
        images: t.images || []
      }))
    }));
  }

  get completionRate() {
    const allTasks = this.days.flatMap(d => d.tasks);
    if (allTasks.length === 0) return 0;
    const done = allTasks.filter(t => t.status === 'done').length;
    return Math.round((done / allTasks.length) * 100);
  }
}
module.exports = SevenDayPlan;
```

---

## 八、核心业务流程

### 8.1 核心链路全景

```
用户输入企业信息
      │
      ▼
┌──────────────┐
│  模块一：诊断  │ ──→ 输出：健康度评分 + 季度路线图
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  模块二：执行  │ ──→ 输出：本周7天详细执行清单
└──────┬───────┘
       │
       ▼
    老板执行（打卡/上传记录）
       │
       ▼
┌──────────────┐
│  模块三：复盘  │ ──→ 输出：AI分析 + 下周优化建议
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  模块四：校准  │ ──→ 输出：调整后的新一周计划
└──────────────┘
```

### 8.2 首次使用流程

```
小程序启动
    │
    ├─ 已有Token？──否──→ 微信登录 → 获取Token
    │                        │
    │                        ▼
    ├─ 已填企业信息？──否──→ 引导填写（4步表单）
    │                            │
    │                            ▼
    ├─ 已诊断？──否──→ 触发AI诊断 → 等待结果
    │                    │
    │                    ▼
    │               展示诊断报告
    │                    │
    │                    ▼
    │               生成季度路线图
    │                    │
    │                    ▼
    │               生成第一周计划
    │                    │
    └──────────────→ 跳转工作台首页
```

### 8.3 每日使用流程

```
打开小程序
    │
    ▼
工作台首页
    │
    ├─ 查看阶段进度条（了解当前处于哪个阶段/第几周）
    │
    ├─ 查看"今日聚焦"（今天该做什么任务）
    │
    ├─ 点击任务 → 任务详情页
    │       │
    │       ├─ 查看执行步骤
    │       ├─ 按步骤执行
    │       ├─ 上传执行记录（截图/文字）
    │       └─ 点击"标记完成" → 打卡
    │
    ├─ 返回首页 → 查看本周完成率更新
    │
    └─ 周末点击"本周复盘" → 复盘页
            │
            ├─ 填写复盘表单
            ├─ 提交 → 等待AI分析
            └─ 查看AI优化建议 → 下周计划自动更新
```

### 8.4 时间调度规则

系统根据用户首次诊断日期，自动创建12周（约3个月）作战周期：

| 阶段 | 周数 | 名称 | 核心任务 |
| :--- | :--- | :--- | :--- |
| Phase 1 | 第1-4周 | 启动期 | 账号基建、竞品调研、素材库建立、话术体系 |
| Phase 2 | 第5-8周 | 放量期 | 规律内容发布、获取首批咨询、启动转介绍 |
| Phase 3 | 第9-12周 | 收获期 | 重点追单转化、设计裂变活动、复盘成功案例 |

**每周排期逻辑**：

| 星期 | 任务类型 | 说明 |
| :--- | :--- | :--- |
| 周一 | 准备日 | 本周计划梳理、素材准备 |
| 周二~周五 | 执行日 | 核心营销动作（发布内容、客户沟通等） |
| 周六 | 汇总日 | 数据整理、周复盘填写 |
| 周日 | 休息日 | 无任务，系统展示激励语 |

### 8.5 执行引擎6步翻译法

将季度路线图"翻译"为7天可执行任务清单的核心算法（后端实现，小程序负责展示）：

```
Step 0: 识别当前周数 → 匹配阶段 → 提取阶段必做动作
Step 1: 将阶段必做动作拆解为具体执行子任务
Step 2: 按"周一准备、周二~周五执行、周六汇总、周日休息"排期
Step 3: 为每个任务填充"怎么做"和"执行步骤"
Step 4: 参考上周复盘结果，调整本周任务优先级
Step 5: 输出完整7天计划JSON
```

---

## 九、开发规范

### 9.1 代码规范

#### 命名规范

| 类型 | 规范 | 示例 |
| :--- | :--- | :--- |
| 页面目录 | kebab-case | `weekly-plan/` |
| 组件目录 | kebab-case | `task-card/` |
| JS变量 | camelCase | `currentWeek` |
| JS常量 | UPPER_SNAKE_CASE | `MAX_WEEKS` |
| CSS类名 | kebab-case | `.task-card-container` |
| 事件名 | kebab-case | `bind:checkin` |
| API路径 | kebab-case | `/api/weekly-plan` |

#### WXML规范

```xml
<!-- ✅ 正确：有语义的 class 名，属性对齐 -->
<view class="task-card">
  <view class="task-header">
    <text class="task-title">{{task.title}}</text>
    <text class="task-time">{{task.time_slot}}</text>
  </view>
</view>

<!-- ❌ 错误：无语义缩写 -->
<view class="tc">
  <view class="th">
    <text class="tt">{{task.title}}</text>
  </view>
</view>
```

#### JS规范

```javascript
// ✅ 使用 async/await，统一错误处理
async loadDashboard() {
  try {
    wx.showLoading({ title: '加载中...' });
    const res = await request.get('/api/dashboard');
    this.setData({ dashboard: res.data });
  } catch (err) {
    this.handleError(err);
  } finally {
    wx.hideLoading();
  }
}

// ❌ 回调地狱
loadDashboard() {
  wx.request({
    url: '...',
    success(res) {
      wx.request({
        url: '...',
        success(res2) {
          // ...
        }
      });
    }
  });
}
```

### 9.2 WXSS规范

```css
/* 全局变量定义在 app.wxss */
page {
  --color-primary: #1989fa;
  --color-success: #07c160;
  --color-warning: #ff976a;
  --color-danger: #ee0a24;
  --color-text: #323233;
  --color-text-secondary: #969799;
  --color-background: #f7f8fa;
  --color-border: #ebedf0;
  --font-size-sm: 24rpx;
  --font-size-md: 28rpx;
  --font-size-lg: 32rpx;
  --spacing-sm: 16rpx;
  --spacing-md: 24rpx;
  --spacing-lg: 32rpx;
  --radius-sm: 8rpx;
  --radius-md: 16rpx;
  --radius-lg: 24rpx;
}
```

### 9.3 测试规范

| 测试类型 | 工具 | 覆盖范围 |
| :--- | :--- | :--- |
| 单元测试 | Jest + miniprogram-simulate | 组件逻辑、工具函数 |
| 接口测试 | Postman / 自动化脚本 | 所有API接口 |
| UI测试 | 微信开发者工具自动化 | 页面跳转、交互流程 |
| 真机测试 | 微信真机预览 | 性能、兼容性 |

**关键测试场景**：

1. 首次使用全流程：登录 → 填表 → 诊断 → 查看路线图 → 查看任务 → 打卡 → 复盘
2. 12周周期切换：第4周→第5周（阶段切换）、第12周→新季度
3. 网络异常处理：断网恢复后数据同步
4. 小程序前后台切换：onShow 时数据刷新

### 9.4 性能优化

| 优化项 | 方案 | 目标 |
| :--- | :--- | :--- |
| 首屏加载 | 分包加载非首屏页面 | 首屏 < 2s |
| 图片加载 | 使用 CDN + 懒加载 | 图片 < 500ms |
| 列表渲染 | 虚拟列表 / 分页加载 | 100+条不卡顿 |
| 数据缓存 | 合理使用 Storage | 减少 50% 请求 |
| 包体积 | 分包 + 按需引入 | 主包 < 2MB |

### 9.5 安全规范

1. **Token管理**：JWT存储在StorageSync，每次请求自动携带，过期自动刷新
2. **敏感信息**：企业数据不写入日志，不通过URL传参
3. **接口鉴权**：所有API需携带有效Token，后端校验用户身份
4. **数据加密**：敏感字段（如手机号）传输时加密
5. **防重复提交**：打卡、提交复盘等操作加防重锁

---

## 十、MVP开发计划

### 10.1 阶段划分

| 阶段 | 时间 | 任务 | 交付物 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | 第1周 | 需求确认、UI设计稿、技术方案评审 | 设计稿+技术方案文档 |
| **Phase 2** | 第2周 | 后端API搭建 + AI Agent开发 | 可调用的API + Swagger文档 |
| **Phase 3** | 第3-4周 | 后端核心功能开发（诊断+执行引擎+复盘） | 后端功能完整可测试 |
| **Phase 4** | 第5-6周 | 小程序前端开发（全部页面+组件） | 完整可交互的MVP小程序 |
| **Phase 5** | 第7周 | 联调测试、Bug修复、性能优化 | 测试报告 + 修复版 |
| **Phase 6** | 第8周 | 灰度发布、种子用户测试 | 公测版上线 |

### 10.2 前端开发排期（Phase 4 详细）

| 周次 | 天 | 任务 | 负责人 |
| :--- | :--- | :--- | :--- |
| 第5周 | D1-2 | 项目初始化、app配置、请求封装、路由搭建 | 前端 |
| 第5周 | D3-4 | 引导页（4步表单）+ 企业信息页 | 前端 |
| 第5周 | D5 | 登录鉴权流程 + 本地缓存管理 | 前端 |
| 第6周 | D1-2 | 工作台首页 + 进度条组件 + 任务卡片组件 | 前端 |
| 第6周 | D3 | 诊断页 + 雷达图组件 | 前端 |
| 第6周 | D4 | 路线图页 + 时间线组件 | 前端 |
| 第6周 | D5 | 本周任务页 + 任务详情页 + 复盘页 | 前端 |

### 10.3 验收标准

| 验收项 | 标准 |
| :--- | :--- |
| 功能完整性 | 8个页面全部可交互，核心链路跑通 |
| 性能 | 首屏加载 < 2s，页面切换 < 500ms |
| 兼容性 | iOS 12+ / Android 8+ / 微信 8.0+ |
| 体验 | 无白屏、无崩溃、操作反馈及时 |
| 数据 | 诊断→路线图→任务→打卡→复盘 全链路数据正确 |

---

## 十一、附录

### 11.1 阶段定义参考

```javascript
// utils/constants.js
const PHASES = [
  {
    index: 1,
    name: '启动期',
    weeksCover: '1-4',
    keyActions: ['账号基建', '竞品调研', '核心素材库建立', '话术体系建立'],
    successCriteria: '完成3个平台账号搭建，积累20条核心素材'
  },
  {
    index: 2,
    name: '放量期',
    weeksCover: '5-8',
    keyActions: ['规律内容发布', '获取首批有效咨询', '启动转介绍'],
    successCriteria: '每周稳定发布5条内容，获取10+有效咨询'
  },
  {
    index: 3,
    name: '收获+裂变期',
    weeksCover: '9-12',
    keyActions: ['重点追单转化', '设计裂变活动', '复盘成功案例'],
    successCriteria: '转化率提升至20%，完成1次裂变活动'
  }
];

const TASK_STATUS = {
  PENDING: 'pending',
  DOING: 'doing',
  DONE: 'done'
};

const REVIEW_TYPES = {
  WEEKLY: 'weekly',
  MONTHLY: 'monthly',
  QUARTERLY: 'quarterly'
};

const INDUSTRIES = [
  '餐饮', '零售', '教育', '美容', '服务', '制造', '医疗', '其他'
];

const TEAM_SIZES = [
  '1-5人', '6-20人', '21-50人', '51-200人', '200人以上'
];

const PRICE_RANGES = [
  '0-50元', '50-200元', '200-1000元', '1000-5000元', '5000元以上'
];

const MARKETING_CHANNELS = [
  '线下门店', '美团外卖', '大众点评', '小红书', '抖音', '微信公众号',
  '朋友圈广告', '社群运营', '线下地推', '转介绍'
];

module.exports = {
  PHASES,
  TASK_STATUS,
  REVIEW_TYPES,
  INDUSTRIES,
  TEAM_SIZES,
  PRICE_RANGES,
  MARKETING_CHANNELS
};
```

### 11.2 常用工具函数

```javascript
// utils/date.js

/**
 * 获取当前周数（相对于季度开始日期）
 * @param {string} startDate - 季度开始日期 YYYY-MM-DD
 * @returns {number} 当前是第几周 (1-12)
 */
function getCurrentWeekNumber(startDate) {
  const start = new Date(startDate);
  const now = new Date();
  const diffMs = now - start;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  return Math.min(Math.floor(diffDays / 7) + 1, 12);
}

/**
 * 根据周数判断所属阶段
 * @param {number} week
 * @returns {object} { index, name, weeksCover }
 */
function getPhaseByWeek(week) {
  if (week >= 1 && week <= 4) {
    return { index: 1, name: '启动期', weeksCover: '1-4' };
  } else if (week >= 5 && week <= 8) {
    return { index: 2, name: '放量期', weeksCover: '5-8' };
  } else {
    return { index: 3, name: '收获+裂变期', weeksCover: '9-12' };
  }
}

/**
 * 格式化日期
 * @param {Date} date
 * @returns {string} YYYY-MM-DD
 */
function formatDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/**
 * 获取本周日期范围
 * @returns {Array} 7天的日期数组
 */
function getWeekDates() {
  const today = new Date();
  const day = today.getDay() || 7; // 周日=7
  const monday = new Date(today);
  monday.setDate(today.getDate() - day + 1);

  const dates = [];
  const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    dates.push({
      day_name: dayNames[i],
      date: formatDate(d),
      is_today: formatDate(d) === formatDate(today)
    });
  }
  return dates;
}

module.exports = {
  getCurrentWeekNumber,
  getPhaseByWeek,
  formatDate,
  getWeekDates
};
```

### 11.3 诊断Prompt参考（后端使用）

```
角色设定：你是一名拥有15年经验、擅长中小企业实战的营销战略顾问。

输出要求（严格遵循JSON结构）：
1. 综合健康度评分（0-100）及一句话总评。
2. 五个维度评分（定位/产品/渠道/内容/转化）。
3. Top3核心问题及针对性建议。
4. 输出 quarterly_roadmap 对象，包含：
   - overall_goal：数字化季度总目标。
   - phases：三阶段（启动期/放量期/收获期），每阶段含 key_actions 和 success_criteria。

硬约束：禁止空泛的行业黑话，确保小学文化程度的老板也能看懂。
```

### 11.4 错误处理统一方案

```javascript
// utils/error-handler.js
const ERROR_MESSAGES = {
  '-1': '网络连接失败，请检查网络',
  '1001': '信息填写有误，请检查后重试',
  '1002': '登录已过期，请重新登录',
  '1003': '暂无权限执行此操作',
  '2001': 'AI正在分析中，请稍候...',
  '2002': '分析失败，请重试',
  '5000': '服务器开小差了，请稍后重试'
};

function handleError(err, page) {
  console.error('Error:', err);
  const message = ERROR_MESSAGES[err.code] || err.message || '未知错误，请重试';

  if (err.code === '1002') {
    wx.showModal({
      title: '提示',
      content: '登录已过期，请重新登录',
      showCancel: false,
      success() {
        wx.redirectTo({ url: '/pages/onboarding/onboarding' });
      }
    });
    return;
  }

  if (err.code === '2001') {
    // AI处理中，使用loading提示
    wx.showLoading({ title: message, mask: true });
    return;
  }

  wx.showToast({ title: message, icon: 'none', duration: 3000 });
}

module.exports = { handleError };
```

---

> **文档结束**
>
> 本文档为 AI企业营销战略执行智能体微信小程序的完整开发指南。开发过程中如遇问题，请先查阅本文档对应章节，仍有疑问再协调后端确认接口细节。
