import os

# --- System Constants ---
WHALE_THRESHOLD = 10000    # $10,000 for Trade Scanner
WALL_THRESHOLD = 50000     # $50,000 for Wall Hunter

# --- Platform Configuration ---
# Polymarket
POLYMARKET_ENABLE = True
POLYMARKET_TRENDING_LIMIT = 8
POLYMARKET_DAILY_REPORT_TIME = "00:00"  # UTC (北京时间 08:00)

# Opinion
OPINION_ENABLE = False  # Disabled - only Polymarket at 08:00 Beijing time
OPINION_TRENDING_LIMIT = 8
OPINION_DAILY_REPORT_TIME = "12:00"  # UTC (北京时间 20:00)
OPINION_API_BASE_URL = "https://api.opinion.trade"  # Opinion API Base URL

# --- Filtering ---
TAGS_SKIP = ['Sports', 'Football', 'Soccer', 'Basketball', 'Tennis', 'Golf', 'MMA', 'UFC', 'Baseball', 'Hockey', 'Cricket', 'Rugby', 'Athletics', 'Cycling', 'Esports', 'Volleyball']
KEYWORDS_SKIP = [
    'nfl', 'nba', 'super bowl', 'premier league', 'champions league', 'serie a', 'la liga', 'bundesliga', 
    'song', 'album', 'grammy', 'oscar', 'box office', 
    ' vs ', ' vs.', 'over ', 'under ', 'handicap', 'goals', 'points', 'score',
    'championship', 'winning team', 'mvp', 'winner', 'cup', 'bowl', 'tournament',
    'buccaneers', 'saints', 'giants', 'eagles', 'chiefs', '49ers', 'cowboys', 'packers', 'ravens', 'lions', 'bills', 'bengals',
    'psg', 'ajax', 'madrid', 'barcelona', 'bayern', 'manchester', 'united', 'city', 'liverpool', 'arsenal', 'chelsea',
    'inter ', 'ac milan', 'juventus', 'mallorca', 'fc ', ' fc', 'sporting', 'athletic'
]

# --- Homepage-First Recommendation Engine (V72) ---
# 系统级指令：优先于所有其他提示词
SYSTEM_HOMEPAGE_FILTER = """
你是 Qwe Truth Machine 的 Homepage-First Recommendation Engine。

你的首要职责不是"分析所有市场"，
而是"只让像预测市场主页一样的重要问题出现"。

全局强制规则（不可违反）：

1. 所有市场必须先通过 Homepage Alignment 判断。
   未通过者，不允许生成正文分析。

2. 每日最多推荐 10 条市场。
   稀缺性高于覆盖率。

3. 同一现实主题（如财政收入、战争、选举、BTC 价格）
   最多保留 1 条。
   其余必须合并或丢弃。

4. 娱乐或文化事件（如 GTA VI）
   不得作为政治、战争、宏观问题的主时间锚。
   每日报告最多出现 1 次，仅限轻量叙事。

5. 概率极端（≤1% 或 ≥99%）且无异常波动的市场，
   禁止进入推荐内容。

6. 每一个被推荐的市场，必须满足：
   - 明确的现实时间窗口
   - 或明确的政策/事件节点

内容生成原则：

- 不追求"全面"
- 只追求"此刻最重要"
- 优先暴露认知冲突、错价、分歧

如果一个市场"像数据库问题而不是主页问题"，
即使它很专业，也必须被忽略。
"""

# Homepage 判断标准
HOMEPAGE_CRITERIA = {
    "max_daily_items": 10,           # 每日最多推荐条数
    "max_same_topic": 1,             # 同一主题最多条数
    "max_entertainment": 1,          # 娱乐类最多条数
    "extreme_prob_threshold": 0.01,  # 极端概率阈值 (≤1% 或 ≥99%)
}

# --- AI Prompts ---
# V63: Professional Financial News Style
PROMPT_WHALE_ANALYSIS = """
你是一名专业的财经快讯编辑。检测到一笔大额交易：
金额：${value:.0f}
标的：{title}
操作：{action} (价格 {price})

请写一段 40-60 字的**快讯简评**。
要求：
1. 风格：**正式、客观、新闻媒体感**（类似彭博社或财新快讯）。
2. 杜绝"毒舌"、"韭菜"等口语化词汇。
3. 分析重点：资金流向的信号意义、市场情绪或潜在的事件驱动因素。
4. 结尾简要判断该操作对价格的潜在影响。
"""

# V63: Wall Hunter Professional
PROMPT_WALL_ANALYSIS = """
在 {title} 的 {price} 价格处发现了 ${value:.0f} 的{type}（挂单）。请用15字以内的新闻短语描述这一盘口形态（例如："下方买盘支撑强劲" 或 "上方抛压沉重"）。保持专业。
"""

# V71: Volatility Analysis
VOLATILITY_THRESHOLD = 0.05  # 5% change
PROMPT_VOLATILITY_ANALYSIS = """
你是一名深耕预测市场的财经评论员。监测到以下市场赔率发生剧烈波动：
标的：{title}
平台：{platform}
变动：从 {old_price:.3f} 变为 {new_price:.3f} (涨跌幅 {change:.1%})

请写一段 50-80 字的**深度异动点评**。
要求：
1. ITEM_START 开头。
2. 第一行：🚨 |异动| **[中文标题]**
3. 第二行：📊 赔率：{old_price:.3f} ➔ {new_price:.3f} ({change:+.1%})
4. 后续：简明扼要地分析为何会发生如此剧烈的波动？是否关联了重大地缘政治、政策变动或突发新闻？请给出你的专业洞察。
"""

# V49.1 Preserved: Daily Report Item Rewrite
PROMPT_DAILY_REWRITE = """
你是一名资深市场分析师。重写这 5 条情报。

【格式要求】
每条消息前必须加 "ITEM_START"。

ITEM_START
[Emoji] |两字标签| **[中文标题]**
📊 [赔率] 📉 24h: [涨跌幅]%
💡 [精炼解读，20-30字。一针见血指出核心看点或概率偏差。语气专业。**禁止重复标题信息**。]

【标签】💰|金融|, 🗳️|政治|, 🌍|地缘|, 🪙|币圈|, 🧬|科技|, 💩|其他|
【禁止】禁止输出原始JSON。

数据：{data_json}
"""

# V73: Trending Top20 改写 Prompt (支持多平台) - 中文版
PROMPT_TRENDING_REWRITE_ZH = """
你是专业的预测市场分析师，擅长从赔率中解读市场情绪和隐含信息。

【输入数据】
平台：{platform}
{data_json}

【输出格式】
每条前加 "ITEM_START"。

ITEM_START
**#[排名]** [Emoji] **[中文标题]**
📊 赔率：[主要选项概率，如 Yes 65% / No 35%]
💰 24h交易量：[格式化为 $X.XM 或 $XXK，如果为 None 则显示 "N/A"]
💡 [基于赔率的专业分析，20-35字。从赔率数值解读市场共识、分歧或错价信号。例如："99%的极端赔率显示市场已形成压倒性共识"、"55/45的分歧赔率反映多空博弈激烈"。]
🔗 [url]

【Emoji】🏈体育 🗳️政治 🪙加密 💰金融 🌍地缘 🎬娱乐 🧬科技 ❓其他

【分析要点】
- 极端赔率(>95%或<5%)：强调市场已达成共识，关注是否存在黑天鹅风险
- 分歧赔率(40-60%)：分析多空分歧原因，指出关键变量
- 中等赔率(60-90%)：解读市场倾向性及潜在催化剂
- 结合24h交易量判断市场关注度和资金流向
- 平台：注意输入数据中的平台信息（Polymarket / Opinion），但不需要在输出中显式标注

【禁止】重复标题内容、输出JSON、空洞评论
"""

# V74: Trending Top20 Rewrite Prompt - English Version
PROMPT_TRENDING_REWRITE_EN = """
You are a professional prediction market analyst, skilled at interpreting market sentiment from odds.

【Input Data】
Platform: {platform}
{data_json}

【Output Format】
Prefix each item with "ITEM_START".

ITEM_START
**#[Rank]** [Emoji] **[Title in English]**
📊 Odds: [Main option probabilities, e.g. Yes 65% / No 35%]
💰 24h Volume: [Format as $X.XM or $XXK, show "N/A" if None]
💡 [Professional analysis in English, 15-25 words. Interpret market consensus, divergence or mispricing signals. E.g.: "99% extreme odds show overwhelming market consensus", "55/45 split reflects intense bull-bear battle".]
🔗 [url]

【Emoji】🏈Sports 🗳️Politics 🪙Crypto 💰Finance 🌍Geopolitics 🎬Entertainment 🧬Tech ❓Other

【Analysis Points】
- Extreme odds (>95% or <5%): Emphasize market consensus, watch for black swan risks
- Split odds (40-60%): Analyze reasons for divergence, identify key variables
- Moderate odds (60-90%): Interpret market inclination and potential catalysts
- Combine 24h volume to judge market attention and capital flow

【Forbidden】Repeating title content, outputting JSON, empty comments
"""

# Backward compatibility alias
PROMPT_TRENDING_REWRITE = PROMPT_TRENDING_REWRITE_ZH
