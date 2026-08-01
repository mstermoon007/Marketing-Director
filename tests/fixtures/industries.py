"""
5个行业测试用例 — 企业信息 + Mock LLM 响应

行业覆盖：家装、餐饮、教培、美容、房产中介
每个用例包含：
  - profile_data:    BusinessProfile 输入
  - diagnosis_resp:  诊断 Agent 的 Mock JSON 响应
  - executor_resp:   执行引擎 Agent 的 Mock JSON 响应（7天清单）
  - review_resp:     复盘 Agent 的 Mock JSON 响应
  - csv_content:     模拟 CSV 上传内容
"""

# ──────────────────────────────────────────────
# 行业1：家装公司
# ──────────────────────────────────────────────
JIAZHUANG = {
    "profile_data": {
        "business_name": "鼎安装饰",
        "industry": "家装",
        "city": "杭州",
        "product_desc": "中高端全案装修，半包全包都做，主打环保材料",
        "price_range": "800-1500元/平米",
        "target_customers": "30-45岁改善型家庭，预算20万以上",
        "competitors": "圣都装饰、中博装饰、本地小装修队",
        "current_channels": "主要靠老客户转介绍，偶尔发朋友圈",
        "monthly_revenue": "30-50万",
        "team_size": "8人",
        "biggest_pain": "新客户越来越少，不知道怎么在网上获客",
    },
    "diagnosis_resp": {
        "overall_score": 48,
        "score_summary": "获客渠道严重单一，线上几乎零布局，但老客户口碑是隐性资产",
        "score_breakdown": {
            "定位": 65,
            "产品": 70,
            "渠道": 25,
            "内容": 20,
            "转化": 55,
        },
        "top3_problems": [
            {
                "severity": "critical",
                "category": "渠道",
                "description": "获客100%依赖老客户转介绍，没有线上获客渠道",
                "quick_fix": "本周内注册抖音企业号，发布第一条装修案例视频",
            },
            {
                "severity": "major",
                "category": "内容",
                "description": "朋友圈内容全是硬广，没有展示专业能力和案例",
                "quick_fix": "整理3个已完工案例，拍对比照片存手机里备用",
            },
            {
                "severity": "minor",
                "category": "定位",
                "description": "目标客户描述太宽泛，没有区分改善型和刚需",
                "quick_fix": "把目标锁定为30-45岁改善型家庭，预算20万以上",
            },
        ],
        "strategy_summary": "聚焦30-45岁改善型家庭，用抖音短视频展示装修案例获取咨询，配合老客户转介绍建立信任，本周重点启动短视频获客渠道",
        "this_week_focus": "注册抖音企业号并发布第一条装修案例视频",
    },
    "executor_resp": {
        "theme": "启动短视频获客，激活老客户转介绍",
        "goals": [
            "发布3条装修案例短视频",
            "获得5条有效咨询",
            "联系8个老客户做转介绍铺垫",
        ],
        "key_metrics": {
            "新增客户": 5,
            "咨询量": 8,
            "成交量": 0,
        },
        "days": [
            {
                "day_label": "周一",
                "focus": "准备日：注册账号、研究同行、定选题",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "注册完善抖音企业号",
                        "how_to": "下载抖音，注册企业号，设置头像为公司Logo，简介写'杭州环保装修专家'，留联系方式",
                        "checklist": ["下载抖音APP", "切换企业号", "设置头像和简介", "绑定联系电话"],
                        "done_criteria": "主页信息完整，头像和封面已设置",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "上午",
                        "title": "研究5个本地同行账号",
                        "how_to": "搜索'杭州装修'，看哪些账号粉丝多、互动好，记录他们的选题和标题",
                        "checklist": ["搜索关键词", "记录5个账号", "记录爆款选题方向"],
                        "done_criteria": "记录5个爆款选题方向和标题",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "下午",
                        "title": "确定本周3条视频选题",
                        "how_to": "结合同行爆款和自己的案例，挑3个选题：改造前后对比、装修避坑指南、价格透明化",
                        "checklist": ["列出自己3个最好案例", "匹配选题方向", "每选题写一句话描述"],
                        "done_criteria": "3个选题已定，各一句话描述",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周二",
                "focus": "第一条视频：写脚本+拍摄+发布",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第1条视频脚本",
                        "how_to": "选题选'装修前后对比'，写好开头钩子（3秒抓人），展示改造过程，给出干货，引导私信",
                        "checklist": ["写开头钩子", "列展示要点", "写结尾引导语"],
                        "done_criteria": "脚本完成，能照着拍",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "拍摄并发布第1条视频",
                        "how_to": "手机横屏拍改造前后对比，用剪映加字幕和音乐，早上8点前发布",
                        "checklist": ["拍摄素材", "用剪映剪辑", "加字幕", "发布"],
                        "done_criteria": "视频已发布到抖音",
                        "estimated_minutes": 30,
                    },
                ],
            },
            {
                "day_label": "周三",
                "focus": "第二条视频+回复评论",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第2条视频脚本并拍摄",
                        "how_to": "选题'装修避坑指南'，列出3个常见坑，每个坑配解决方案",
                        "checklist": ["列3个避坑点", "写解决方案", "拍摄"],
                        "done_criteria": "脚本和素材就绪",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "发布第2条视频并回复第1条评论",
                        "how_to": "剪辑发布第2条，然后检查第1条视频的评论，全部回复",
                        "checklist": ["剪辑发布", "检查评论", "逐一回复"],
                        "done_criteria": "第2条已发布，第1条评论全部回复",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周四",
                "focus": "第三条视频+老客户名单整理",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "拍摄并发布第3条视频",
                        "how_to": "选题'价格透明化'，展示半包和全包的区别，标明价格区间",
                        "checklist": ["拍摄素材", "剪辑", "发布"],
                        "done_criteria": "第3条视频已发布",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "整理老客户名单",
                        "how_to": "筛选过去半年成交的满意客户，按关系亲疏排序，选出8个人",
                        "checklist": ["翻聊天记录", "筛选满意客户", "排序"],
                        "done_criteria": "8人名单整理完毕",
                        "estimated_minutes": 15,
                    },
                    {
                        "time_slot": "下午",
                        "title": "写转介绍话术",
                        "how_to": "感谢+请推荐+给好处（推荐成功送保洁一次）",
                        "checklist": ["写感谢语", "写推荐请求", "写奖励方案"],
                        "done_criteria": "一段话术已写好",
                        "estimated_minutes": 10,
                    },
                ],
            },
            {
                "day_label": "周五",
                "focus": "联系老客户+回复评论",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "联系5个老客户",
                        "how_to": "微信发转介绍话术，语气真诚不推销，先问候再提推荐",
                        "checklist": ["发话术给5人", "记录回应", "标记意向"],
                        "done_criteria": "5个客户已联系，记录回应情况",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "下午",
                        "title": "回复本周所有视频评论",
                        "how_to": "检查3条视频的所有评论和私信，全部回复",
                        "checklist": ["检查评论", "检查私信", "逐一回复"],
                        "done_criteria": "所有评论和私信已回复",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周六",
                "focus": "本周数据汇总",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "记录本周数据并截图",
                        "how_to": "截图抖音后台（播放/点赞/评论/私信数），记录咨询和成交数",
                        "checklist": ["截图抖音后台", "记录咨询数", "记录成交数"],
                        "done_criteria": "数据已截图记录，准备上传复盘",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周日",
                "focus": "休息或补漏",
                "tasks": [],
            },
        ],
    },
    "review_resp": {
        "summary": "短视频渠道成功启动，3条视频获得12条咨询，但老客户转介绍响应率偏低",
        "vs_target": [
            {"metric_name": "新增客户", "target": 5, "actual": 7, "achieved": True},
            {"metric_name": "咨询量", "target": 8, "actual": 12, "achieved": True},
            {"metric_name": "成交量", "target": 0, "actual": 1, "achieved": True},
        ],
        "what_worked": [
            "短视频播放量超出预期，第1条突破5000播放",
            "评论区有人主动询问报价",
            "3条视频选题差异化，避坑指南最受欢迎",
        ],
        "what_didnt": [
            "8个老客户只有2人回复，转介绍话术需要优化",
            "私信回复不够及时，有几个咨询流失",
            "周日没有安排内容维护，数据有下滑",
        ],
        "suggestions": [
            "下周保持日更1条视频，重点做避坑类选题",
            "优化转介绍话术，先送价值再提推荐，降低客户心理门槛",
            "设置私信自动回复，确保咨询不流失",
        ],
    },
    "csv_content": "指标,数值\n新增客户,7\n咨询量,12\n成交量,1\n视频播放量,12500\n点赞数,320\n评论数,45\n私信咨询,18\n",
}

# ──────────────────────────────────────────────
# 行业2：餐饮店
# ──────────────────────────────────────────────
CANYIN = {
    "profile_data": {
        "business_name": "老街口私房菜",
        "industry": "餐饮",
        "city": "成都",
        "product_desc": "川菜私房菜馆，主打特色江湖菜和家常小炒，堂食+外卖",
        "price_range": "人均60-90元",
        "target_customers": "附近上班族和家庭聚餐，25-45岁",
        "competitors": "周边3家川菜馆、2家火锅店、美团外卖同类商家",
        "current_channels": "美团外卖+大众点评，基本没做其他推广",
        "monthly_revenue": "15-20万",
        "team_size": "5人",
        "biggest_pain": "堂食客流下降，外卖利润薄，想拉新但不知道怎么搞",
    },
    "diagnosis_resp": {
        "overall_score": 55,
        "score_summary": "产品口碑基础不错但营销几乎空白，过度依赖平台流量，没有自己的客户池",
        "score_breakdown": {
            "定位": 60,
            "产品": 75,
            "渠道": 40,
            "内容": 25,
            "转化": 50,
        },
        "top3_problems": [
            {
                "severity": "critical",
                "category": "渠道",
                "description": "100%依赖美团和大众点评，平台抽成高且流量不可控",
                "quick_fix": "本周建立微信客户群，把堂食客人加到私域",
            },
            {
                "severity": "major",
                "category": "内容",
                "description": "大众点评图片老旧，没有突出招牌菜特色",
                "quick_fix": "用手机拍3张招牌菜特写，更新点评头图",
            },
            {
                "severity": "minor",
                "category": "转化",
                "description": "没有复购引导机制，客人吃完就走",
                "quick_fix": "设计一张桌贴：扫码进群送酸梅汤",
            },
        ],
        "strategy_summary": "用桌贴+扫码把堂食客户沉淀到微信群，配合朋友圈每日菜品推送拉动复购，本周重点建群并裂变到100人",
        "this_week_focus": "设计桌贴二维码，把堂食客人加到微信群",
    },
    "executor_resp": {
        "theme": "建私域客户群，启动朋友圈菜品营销",
        "goals": [
            "微信群加到100人",
            "朋友圈每天发1条菜品内容",
            "推出1个群内专属优惠",
        ],
        "key_metrics": {
            "新增客户": 50,
            "咨询量": 20,
            "成交量": 15,
        },
        "days": [
            {
                "day_label": "周一",
                "focus": "准备日：设计桌贴、准备微信群",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "设计桌贴二维码",
                        "how_to": "用 Canva 或手写，内容：扫码进群送酸梅汤一杯，加上群二维码和店名",
                        "checklist": ["写文案", "生成群二维码", "排版打印"],
                        "done_criteria": "桌贴已打印，每桌一张",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "下午",
                        "title": "创建微信群并设置欢迎语",
                        "how_to": "建群，设置自动欢迎语：欢迎光临老街口私房菜，群内每周三有专属优惠，每日推送今日菜品",
                        "checklist": ["建群", "设群名", "设欢迎语"],
                        "done_criteria": "群已创建，欢迎语已设置",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周二",
                "focus": "贴桌贴开始拉群+拍菜品照",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "贴桌贴并引导客人扫码",
                        "how_to": "每桌贴好二维码，客人结账时主动说'扫码进群送酸梅汤'",
                        "checklist": ["贴桌贴", "培训话术", "结账时引导"],
                        "done_criteria": "所有桌位已贴，当天至少20人进群",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "下午",
                        "title": "拍3道招牌菜特写照片",
                        "how_to": "选3道招牌菜，用手机在自然光下拍特写，注意色彩和摆盘",
                        "checklist": ["选3道菜", "找好光线", "拍特写"],
                        "done_criteria": "3张高质量菜品照存手机",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周三",
                "focus": "群内首个优惠活动+朋友圈推送",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "在群内发布首个专属优惠",
                        "how_to": "发消息：今日群内专属，水煮鱼半价限量10份，先到先得",
                        "checklist": ["定优惠菜品", "定数量", "群内发布"],
                        "done_criteria": "优惠已发布，有人下单",
                        "estimated_minutes": 10,
                    },
                    {
                        "time_slot": "下午",
                        "title": "朋友圈发今日菜品推送",
                        "how_to": "用昨天拍的招牌菜照片，配文'今日推荐：老街口水煮鱼，鲜辣过瘾'，发朋友圈",
                        "checklist": ["选照片", "写文案", "发布"],
                        "done_criteria": "朋友圈已发布",
                        "estimated_minutes": 10,
                    },
                ],
            },
            {
                "day_label": "周四",
                "focus": "持续拉群+朋友圈第二推",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "继续引导堂食客人进群",
                        "how_to": "结账时主动邀请，目标是当天新增20人",
                        "checklist": ["引导话术", "记录进群数"],
                        "done_criteria": "当天至少20人进群",
                        "estimated_minutes": 15,
                    },
                    {
                        "time_slot": "下午",
                        "title": "朋友圈发第二道招牌菜",
                        "how_to": "发另一道招牌菜照片，配文突出做法和食材",
                        "checklist": ["选照片", "写文案", "发布"],
                        "done_criteria": "朋友圈已发布",
                        "estimated_minutes": 10,
                    },
                ],
            },
            {
                "day_label": "周五",
                "focus": "周末预热+群内互动",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "群内发周末预订优惠",
                        "how_to": "发消息：周末家庭聚餐提前预订送水果拼盘，限前5桌",
                        "checklist": ["定优惠", "群内发布", "记录预订"],
                        "done_criteria": "消息已发，至少3桌预订",
                        "estimated_minutes": 10,
                    },
                    {
                        "time_slot": "下午",
                        "title": "朋友圈发周末热闹氛围",
                        "how_to": "拍一张餐厅热闹的照片或视频，配文'周末烟火气，老街口等你'",
                        "checklist": ["拍素材", "写文案", "发布"],
                        "done_criteria": "朋友圈已发布",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周六",
                "focus": "本周数据汇总",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "记录本周数据并截图",
                        "how_to": "截图微信群人数、朋友圈点赞评论数、记录本周堂食和外卖数据",
                        "checklist": ["截图群人数", "截图朋友圈", "记录营业额"],
                        "done_criteria": "数据已记录，准备上传复盘",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周日",
                "focus": "休息或备菜",
                "tasks": [],
            },
        ],
    },
    "review_resp": {
        "summary": "私域建群策略见效明显，5天拉到87人，群内优惠转化率超预期",
        "vs_target": [
            {"metric_name": "新增客户", "target": 50, "actual": 87, "achieved": True},
            {"metric_name": "咨询量", "target": 20, "actual": 25, "achieved": True},
            {"metric_name": "成交量", "target": 15, "actual": 12, "achieved": False},
        ],
        "what_worked": [
            "桌贴+送饮品的策略拉群效率很高",
            "群内限时优惠制造紧迫感，下单积极",
            "朋友圈菜品照片互动率不错",
        ],
        "what_didnt": [
            "周三优惠菜品备货不足，有客人没吃到",
            "外卖部分没有引导进群，漏了线上客人",
            "周五预订优惠力度不够，只来了3桌",
        ],
        "suggestions": [
            "下周在外卖包装里加群二维码卡片",
            "优惠菜品提前备足，设限同时保证供应",
            "增加群内每日互动，如'猜菜名送菜'小游戏",
        ],
    },
    "csv_content": "指标,数值\n新增客户,87\n咨询量,25\n成交量,12\n微信群人数,87\n朋友圈点赞,156\n朋友圈评论,43\n",
}

# ──────────────────────────────────────────────
# 行业3：教培机构
# ──────────────────────────────────────────────
JIAOPEI = {
    "profile_data": {
        "business_name": "启航少儿编程",
        "industry": "教培",
        "city": "深圳",
        "product_desc": "6-12岁少儿编程培训，Scratch入门到Python进阶，小班教学",
        "price_range": "200-350元/课时",
        "target_customers": "6-12岁孩子家长，重视素质教育，中产家庭",
        "competitors": "编程猫、小码王、本地3家培训机构",
        "current_channels": "地推发传单+家长群口碑，效果越来越差",
        "monthly_revenue": "8-12万",
        "team_size": "3人",
        "biggest_pain": "传单没人接了，招生困难，不知道怎么在网上找家长",
    },
    "diagnosis_resp": {
        "overall_score": 42,
        "score_summary": "教学品质不错但获客方式严重过时，家长触达渠道几乎为零",
        "score_breakdown": {
            "定位": 55,
            "产品": 68,
            "渠道": 20,
            "内容": 30,
            "转化": 40,
        },
        "top3_problems": [
            {
                "severity": "critical",
                "category": "渠道",
                "description": "地推传单转化率已降至0.3%，且家长反感",
                "quick_fix": "本周在小红书发布第一篇编程教育笔记",
            },
            {
                "severity": "major",
                "category": "内容",
                "description": "没有展示教学成果和家长好评的内容",
                "quick_fix": "收集3个学员作品截图和2条家长好评",
            },
            {
                "severity": "major",
                "category": "定位",
                "description": "定位模糊，没说清楚为什么要学编程",
                "quick_fix": "把卖点改为'培养逻辑思维，不是培养程序员'",
            },
        ],
        "strategy_summary": "在小红书发布编程教育干货笔记吸引家长关注，用免费体验课做转化钩子，本周重点发3篇笔记并收集10个咨询",
        "this_week_focus": "注册小红书企业号并发布第一篇笔记",
    },
    "executor_resp": {
        "theme": "小红书获客启动，免费体验课转化",
        "goals": [
            "小红书发布3篇笔记",
            "获得10个家长咨询",
            "安排5个免费体验课",
        ],
        "key_metrics": {
            "新增客户": 10,
            "咨询量": 10,
            "成交量": 2,
        },
        "days": [
            {
                "day_label": "周一",
                "focus": "准备日：注册账号、定选题、收集素材",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "注册小红书企业号",
                        "how_to": "下载小红书，注册企业号，设置头像为Logo，简介写'6-12岁少儿编程｜培养逻辑思维'",
                        "checklist": ["下载APP", "注册企业号", "设头像简介"],
                        "done_criteria": "账号已创建，信息完整",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "上午",
                        "title": "研究5个同行业爆款笔记",
                        "how_to": "搜索'少儿编程'，找点赞超500的笔记，记录标题和选题角度",
                        "checklist": ["搜索关键词", "筛选爆款", "记录选题"],
                        "done_criteria": "记录5个爆款选题方向",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "下午",
                        "title": "收集学员作品和家长好评素材",
                        "how_to": "找3个优秀学员的Scratch作品截图，找2条家长微信群好评截图",
                        "checklist": ["找3个作品", "找2条好评", "整理存档"],
                        "done_criteria": "5张素材图已准备",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周二",
                "focus": "第一篇笔记：干货类",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第一篇笔记：为什么让孩子学编程",
                        "how_to": "选题'6岁学编程太早吗？3个理由告诉你'，配学员作品图，结尾引导私信咨询体验课",
                        "checklist": ["写标题", "写正文300字", "选配图", "加话题标签"],
                        "done_criteria": "笔记已发布",
                        "estimated_minutes": 30,
                    },
                ],
            },
            {
                "day_label": "周三",
                "focus": "第二篇笔记+回复评论",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第二篇笔记：学员作品展示",
                        "how_to": "选题'8岁小朋友用Scratch做了个打地鼠游戏'，展示作品截图，讲学习过程",
                        "checklist": ["写标题", "配作品图", "写过程描述"],
                        "done_criteria": "笔记已发布",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "回复第一篇笔记评论",
                        "how_to": "检查评论，逐一回复，有人问价格就引导私信",
                        "checklist": ["检查评论", "逐一回复", "引导私信"],
                        "done_criteria": "所有评论已回复",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周四",
                "focus": "第三篇笔记+体验课邀约",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第三篇笔记：家长好评展示",
                        "how_to": "选题'家长说：孩子学编程后数学成绩提高了'，展示好评截图，附体验课邀请",
                        "checklist": ["写标题", "配好评图", "写体验课邀请"],
                        "done_criteria": "笔记已发布",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "私信回复咨询家长",
                        "how_to": "逐一回复私信，介绍课程，邀约免费体验课",
                        "checklist": ["回复私信", "介绍课程", "约体验课时间"],
                        "done_criteria": "所有私信已回复，至少约到3个体验课",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周五",
                "focus": "体验课执行+持续互动",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "执行体验课",
                        "how_to": "按计划上体验课，课后主动和家长沟通反馈",
                        "checklist": ["准备课件", "上课", "课后沟通"],
                        "done_criteria": "体验课顺利完成，家长获得反馈",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "下午",
                        "title": "回复本周所有评论和私信",
                        "how_to": "检查3篇笔记的评论，回复所有私信",
                        "checklist": ["检查评论", "检查私信", "逐一回复"],
                        "done_criteria": "所有互动已回复",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周六",
                "focus": "本周数据汇总",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "记录本周数据并截图",
                        "how_to": "截图小红书后台（阅读/点赞/收藏/评论数），记录咨询和体验课数",
                        "checklist": ["截图后台", "记录咨询数", "记录体验课数"],
                        "done_criteria": "数据已记录，准备上传复盘",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周日",
                "focus": "休息或备课",
                "tasks": [],
            },
        ],
    },
    "review_resp": {
        "summary": "小红书笔记获客效果显著，3篇笔记带来15个咨询，但体验课转化率偏低",
        "vs_target": [
            {"metric_name": "新增客户", "target": 10, "actual": 15, "achieved": True},
            {"metric_name": "咨询量", "target": 10, "actual": 15, "achieved": True},
            {"metric_name": "成交量", "target": 2, "actual": 1, "achieved": False},
        ],
        "what_worked": [
            "第一篇干货笔记阅读量超2000，远超预期",
            "学员作品展示笔记收藏率最高",
            "评论区有家长主动询问课程详情",
        ],
        "what_didnt": [
            "体验课到课率只有60%，约了5个来了3个",
            "体验课后没有跟进话术，1个报名的还是在催促下决定的",
            "第三篇好评笔记效果一般，可能需要更多真实案例",
        ],
        "suggestions": [
            "下周增加体验课到课确认话术，提前一天电话提醒",
            "设计体验课后3天跟进流程，每天发一条有价值内容",
            "增加视频类笔记，展示上课实况",
        ],
    },
    "csv_content": "指标,数值\n新增客户,15\n咨询量,15\n成交量,1\n笔记阅读量,4800\n点赞数,280\n收藏数,156\n评论数,38\n体验课到课,3\n",
}

# ──────────────────────────────────────────────
# 行业4：美容院
# ──────────────────────────────────────────────
MEIRONG = {
    "profile_data": {
        "business_name": "悦己美肤工作室",
        "industry": "美容",
        "city": "武汉",
        "product_desc": "面部护理和问题肌修复，主打祛痘和敏感肌修复，预约制",
        "price_range": "单次298-698元，套餐1980-5980元",
        "target_customers": "25-40岁女性，有皮肤问题困扰，月收入8000+",
        "competitors": "周边2家连锁美容院、1家皮肤管理中心",
        "current_channels": "老客户介绍+美团团购，没有线上内容",
        "monthly_revenue": "6-10万",
        "team_size": "2人",
        "biggest_pain": "新客进店少，团购客户留存差，想做内容不会做",
    },
    "diagnosis_resp": {
        "overall_score": 52,
        "score_summary": "专业能力不错但完全没有线上内容资产，新客获取靠运气",
        "score_breakdown": {
            "定位": 62,
            "产品": 72,
            "渠道": 35,
            "内容": 15,
            "转化": 58,
        },
        "top3_problems": [
            {
                "severity": "critical",
                "category": "内容",
                "description": "线上零内容，小红书抖音都没有，新客搜不到你",
                "quick_fix": "本周在小红书发布第一篇祛痘案例对比笔记",
            },
            {
                "severity": "major",
                "category": "渠道",
                "description": "美团团购客户留存率低于20%，只图便宜不来二次",
                "quick_fix": "设计团购客户到店后的转化话术和首购套餐",
            },
            {
                "severity": "minor",
                "category": "定位",
                "description": "定位不够聚焦，什么项目都做但没特色",
                "quick_fix": "把宣传重点聚焦到'问题肌修复'一个点上",
            },
        ],
        "strategy_summary": "在小红书发布祛痘修复案例对比笔记获取精准客户，配合美团团购引流到店后用体验套餐转化留存，本周重点发3篇案例笔记",
        "this_week_focus": "拍第一组祛痘前后对比照并发布小红书笔记",
    },
    "executor_resp": {
        "theme": "小红书案例营销启动，团购客户留存优化",
        "goals": [
            "小红书发布3篇祛痘案例笔记",
            "获得8个精准咨询",
            "设计1套团购客户转化套餐",
        ],
        "key_metrics": {
            "新增客户": 8,
            "咨询量": 8,
            "成交量": 3,
        },
        "days": [
            {
                "day_label": "周一",
                "focus": "准备日：注册账号、收集案例素材",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "注册小红书企业号",
                        "how_to": "注册企业号，头像用工作室Logo，简介'专注问题肌修复｜祛痘/敏感肌'，留预约方式",
                        "checklist": ["注册账号", "设头像简介", "留联系方式"],
                        "done_criteria": "账号信息完整",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "上午",
                        "title": "整理3个祛痘修复案例的前后对比照",
                        "how_to": "从客户档案中找3个效果最好的案例，整理前后对比照，注意保护客户隐私",
                        "checklist": ["选3个案例", "整理对比照", "脱敏处理"],
                        "done_criteria": "3组对比照已准备",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "下午",
                        "title": "设计团购客户转化套餐",
                        "how_to": "设计一个团购客户到店后的专属套餐：首购198元3次深层清洁+修复，原价598",
                        "checklist": ["定套餐内容", "定价格", "写话术"],
                        "done_criteria": "套餐方案和话术已定",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周二",
                "focus": "第一篇笔记：案例对比",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第一篇笔记：祛痘前后对比",
                        "how_to": "选题'28天祛痘全过程，烂脸到好皮肤'，配对比照，写护理过程，结尾引导私信咨询",
                        "checklist": ["写标题", "配对比照", "写过程", "加引导语"],
                        "done_criteria": "笔记已发布",
                        "estimated_minutes": 30,
                    },
                ],
            },
            {
                "day_label": "周三",
                "focus": "第二篇笔记+回复评论",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第二篇笔记：护肤误区科普",
                        "how_to": "选题'长痘千万别做这3件事'，用专业角度科普，展示工作室专业度",
                        "checklist": ["写标题", "写3个误区", "配图"],
                        "done_criteria": "笔记已发布",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "回复第一篇笔记评论",
                        "how_to": "检查评论，逐一专业回复，引导私信咨询",
                        "checklist": ["检查评论", "专业回复", "引导私信"],
                        "done_criteria": "所有评论已回复",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周四",
                "focus": "第三篇笔记+团购转化执行",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "写第三篇笔记：客户好评+预约引导",
                        "how_to": "选题'客户说：终于敢素颜出门了'，配客户好评截图和对比照",
                        "checklist": ["写标题", "配好评图", "写引导语"],
                        "done_criteria": "笔记已发布",
                        "estimated_minutes": 25,
                    },
                    {
                        "time_slot": "下午",
                        "title": "对到店团购客户执行转化话术",
                        "how_to": "服务结束后介绍专属套餐，用话术引导首购",
                        "checklist": ["服务结束介绍", "用转化话术", "记录反馈"],
                        "done_criteria": "当天所有团购客户都介绍了套餐",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周五",
                "focus": "回复私信+预约安排",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "回复所有笔记评论和私信",
                        "how_to": "检查3篇笔记互动，逐一回复，私信咨询引导预约",
                        "checklist": ["检查评论", "检查私信", "引导预约"],
                        "done_criteria": "所有互动已回复",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "下午",
                        "title": "整理本周预约名单",
                        "how_to": "汇总本周通过小红书来的预约，安排下周时间",
                        "checklist": ["汇总预约", "排时间表", "发确认信息"],
                        "done_criteria": "预约名单已整理，确认信息已发",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周六",
                "focus": "本周数据汇总",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "记录本周数据并截图",
                        "how_to": "截图小红书后台数据，记录咨询数和到店数，截图美团团购数据",
                        "checklist": ["截图小红书", "记录咨询到店", "截图美团"],
                        "done_criteria": "数据已记录，准备上传复盘",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周日",
                "focus": "休息或设备维护",
                "tasks": [],
            },
        ],
    },
    "review_resp": {
        "summary": "小红书案例笔记获客精准度高，但团购客户转化套餐效果不理想",
        "vs_target": [
            {"metric_name": "新增客户", "target": 8, "actual": 9, "achieved": True},
            {"metric_name": "咨询量", "target": 8, "actual": 11, "achieved": True},
            {"metric_name": "成交量", "target": 3, "actual": 2, "achieved": False},
        ],
        "what_worked": [
            "案例对比笔记互动量最高，收藏超200",
            "通过小红书来的客户精准度很高，到店即咨询",
            "护肤误区科普笔记建立了专业形象",
        ],
        "what_didnt": [
            "团购客户对转化套餐兴趣不大，觉得还是贵",
            "私信回复不够及时，有2个咨询流失",
            "第三篇好评笔记互动一般，内容需要更真实",
        ],
        "suggestions": [
            "下周调整团购转化套餐，降低门槛到98元体验1次",
            "设置小红书私信自动回复，确保咨询不流失",
            "增加视频类内容，展示护理过程和手法",
        ],
    },
    "csv_content": "指标,数值\n新增客户,9\n咨询量,11\n成交量,2\n笔记阅读量,3200\n点赞数,210\n收藏数,230\n评论数,28\n私信咨询,15\n",
}

# ──────────────────────────────────────────────
# 行业5：房产中介
# ──────────────────────────────────────────────
FANGCHAN = {
    "profile_data": {
        "business_name": "安家地产（城东店）",
        "industry": "中介",
        "city": "南京",
        "product_desc": "二手房买卖和租赁，主做城东片区，刚需和改善型住宅",
        "price_range": "佣金1-2%，租赁一个月租金",
        "target_customers": "25-45岁买房/租房人群，城东片区优先",
        "competitors": "链家、我爱我家、周边5家小中介",
        "current_channels": "门店自然客流+老客户介绍，偶尔发房源朋友圈",
        "monthly_revenue": "10-18万",
        "team_size": "4人",
        "biggest_pain": "链家品牌太强抢走很多客户，小店不知道怎么在网上竞争",
    },
    "diagnosis_resp": {
        "overall_score": 50,
        "score_summary": "片区资源是优势但线上完全没有差异化内容，客户被大品牌截流",
        "score_breakdown": {
            "房源获取": 45,
            "带看转化": 60,
            "社区渗透": 35,
            "线上获客": 30,
            "专业形象": 62,
            "数据运营": 68,
        },
        "top3_problems": [
            {
                "severity": "critical",
                "category": "线上获客",
                "description": "没有差异化定位，客户觉得'中介都一样'",
                "quick_fix": "把定位改为'城东片区最懂房的本地中介'，打片区专家牌",
            },
            {
                "severity": "major",
                "category": "房源获取",
                "description": "线上只在贝壳/链家平台发房源，没有自有渠道",
                "quick_fix": "本周注册抖音号，发第一条城东片区踩盘视频",
            },
            {
                "severity": "minor",
                "category": "专业形象",
                "description": "朋友圈只发房源信息，没有片区分析和买房干货",
                "quick_fix": "写一篇城东片区买房攻略，发朋友圈和小红书",
            },
        ],
        "strategy_summary": "用抖音短视频做城东片区踩盘和买房干货内容建立本地专家形象，配合朋友圈片区分析内容，本周重点发3条踩盘视频",
        "this_week_focus": "拍第一条城东小区踩盘视频并发布抖音",
    },
    "executor_resp": {
        "theme": "抖音踩盘内容启动，打造城东片区专家",
        "goals": [
            "发布3条城东小区踩盘视频",
            "获得8个买房/租房咨询",
            "写1篇城东买房攻略发朋友圈",
        ],
        "key_metrics": {
            "新增客户": 8,
            "咨询量": 8,
            "成交量": 0,
        },
        "days": [
            {
                "day_label": "周一",
                "focus": "准备日：注册账号、选踩盘小区",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "注册抖音企业号",
                        "how_to": "注册企业号，头像用门店照片，简介写'城东片区最懂房的本地中介｜买房租房避坑指南'",
                        "checklist": ["注册账号", "设头像简介", "认证门店"],
                        "done_criteria": "账号信息完整",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "上午",
                        "title": "选3个本周踩盘的小区",
                        "how_to": "选3个性价比高、关注度高的城东小区，准备踩盘路线",
                        "checklist": ["选3个小区", "查小区信息", "定踩盘路线"],
                        "done_criteria": "3个小区已选定",
                        "estimated_minutes": 15,
                    },
                    {
                        "time_slot": "下午",
                        "title": "研究5个同行抖音号",
                        "how_to": "搜索'南京买房'或'房产中介'，看数据好的账号，记录选题和拍摄方式",
                        "checklist": ["搜索关键词", "找5个号", "记录选题"],
                        "done_criteria": "记录5个可借鉴的选题方向",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周二",
                "focus": "第一条踩盘视频",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "踩盘第一个小区并拍摄",
                        "how_to": "到小区实地拍摄：小区门口、绿化环境、楼道、户型，边走边解说",
                        "checklist": ["到小区", "拍环境", "拍户型", "录解说"],
                        "done_criteria": "素材拍摄完成",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "下午",
                        "title": "剪辑并发布第一条踩盘视频",
                        "how_to": "用剪映剪辑，加字幕，配文字'城东XX小区实踩，均价2.3万，值不值？'，发布",
                        "checklist": ["剪辑视频", "加字幕", "写标题", "发布"],
                        "done_criteria": "视频已发布",
                        "estimated_minutes": 25,
                    },
                ],
            },
            {
                "day_label": "周三",
                "focus": "第二条踩盘视频+回复评论",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "踩盘第二个小区并拍摄",
                        "how_to": "选一个刚需盘，重点拍户型和周边配套，解说性价比",
                        "checklist": ["到小区", "拍环境配套", "拍户型", "录解说"],
                        "done_criteria": "素材拍摄完成",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "下午",
                        "title": "剪辑发布+回复第一条评论",
                        "how_to": "剪辑发布第二条，检查第一条评论，全部专业回复",
                        "checklist": ["剪辑发布", "检查评论", "专业回复"],
                        "done_criteria": "第二条已发布，第一条评论已回复",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周四",
                "focus": "第三条踩盘+买房攻略",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "踩盘第三个小区并拍摄",
                        "how_to": "选一个改善盘，重点拍小区品质和户型亮点",
                        "checklist": ["到小区", "拍品质细节", "拍户型", "录解说"],
                        "done_criteria": "素材拍摄完成",
                        "estimated_minutes": 30,
                    },
                    {
                        "time_slot": "下午",
                        "title": "写城东买房攻略发朋友圈",
                        "how_to": "写300字攻略：城东3个预算段推荐哪些小区，各有什么优缺点",
                        "checklist": ["列3个预算段", "推荐小区", "写优缺点", "发朋友圈"],
                        "done_criteria": "攻略已发朋友圈",
                        "estimated_minutes": 20,
                    },
                ],
            },
            {
                "day_label": "周五",
                "focus": "剪辑发布第三条+回复互动",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "剪辑发布第三条踩盘视频",
                        "how_to": "剪辑第三条，配文字'城东改善首选？XX小区实踩，品质在线'",
                        "checklist": ["剪辑视频", "写标题", "发布"],
                        "done_criteria": "视频已发布",
                        "estimated_minutes": 20,
                    },
                    {
                        "time_slot": "下午",
                        "title": "回复所有评论和私信",
                        "how_to": "检查3条视频的评论和私信，专业回复，引导到店咨询",
                        "checklist": ["检查评论", "检查私信", "引导咨询"],
                        "done_criteria": "所有互动已回复",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周六",
                "focus": "本周数据汇总",
                "tasks": [
                    {
                        "time_slot": "上午",
                        "title": "记录本周数据并截图",
                        "how_to": "截图抖音后台数据，记录咨询数和到店数",
                        "checklist": ["截图抖音", "记录咨询", "记录到店"],
                        "done_criteria": "数据已记录，准备上传复盘",
                        "estimated_minutes": 15,
                    },
                ],
            },
            {
                "day_label": "周日",
                "focus": "休息或带看",
                "tasks": [],
            },
        ],
    },
    "review_resp": {
        "summary": "踩盘视频内容获客效果好于预期，3条视频带来10个咨询，但到店转化率为零",
        "vs_target": [
            {"metric_name": "新增客户", "target": 8, "actual": 10, "achieved": True},
            {"metric_name": "咨询量", "target": 8, "actual": 10, "achieved": True},
            {"metric_name": "成交量", "target": 0, "actual": 0, "achieved": True},
        ],
        "what_worked": [
            "踩盘视频播放量不错，第一条突破3000",
            "评论区有人主动问价格和户型",
            "朋友圈买房攻略获得5个点赞和2个咨询",
        ],
        "what_didnt": [
            "10个咨询只有2个到店，到店转化率低",
            "视频拍摄质量一般，画面晃动明显",
            "没有在视频结尾给出明确的到店邀请",
        ],
        "suggestions": [
            "下周在视频结尾加固定引导语：到店免费看房咨询",
            "买一个手机稳定器提升拍摄质量",
            "设计一个到店专属福利（如免费学区评估）提高到店率",
        ],
    },
    "csv_content": "指标,数值\n新增客户,10\n咨询量,10\n成交量,0\n视频播放量,8500\n点赞数,180\n评论数,32\n私信咨询,14\n到店数,2\n",
}

# ──────────────────────────────────────────────
# 汇总
# ──────────────────────────────────────────────
ALL_INDUSTRIES = {
    "家装": JIAZHUANG,
    "餐饮": CANYIN,
    "教培": JIAOPEI,
    "美容": MEIRONG,
    "中介": FANGCHAN,
}
