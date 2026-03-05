import os
import aiohttp
import json
import asyncio
from src.config import (
    PROMPT_WHALE_ANALYSIS, PROMPT_WALL_ANALYSIS, PROMPT_DAILY_REWRITE,
    PROMPT_TRENDING_REWRITE_ZH, PROMPT_TRENDING_REWRITE_EN
)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.session = None

    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        if self.session: await self.session.close()

    async def _call_deepseek(self, prompt, retries=1, timeout=30):
        if not self.api_key:
            print("⚠️ DeepSeek API key not set")
            return None
        if not self.session:
            await self.start()

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        for attempt in range(retries + 1):
            try:
                async with self.session.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content'].strip()
                    else:
                        print(f"⚠️ DeepSeek API Error: {resp.status}")
            except asyncio.TimeoutError:
                print(f"⚠️ DeepSeek timeout (attempt {attempt+1}/{retries+1})")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️ DeepSeek error: {e}")
                await asyncio.sleep(1)
        return None

    async def analyze_whale(self, trade):
        prompt = PROMPT_WHALE_ANALYSIS.format(
            value=trade['value'],
            title=trade['title'],
            action=trade['action'],
            price=trade['price']
        )
        res = await self._call_deepseek(prompt)
        return res or "资金异动。"

    async def analyze_wall(self, wall):
        prompt = PROMPT_WALL_ANALYSIS.format(
            title=wall['title'],
            price=wall['price'],
            value=wall['value'],
            type=wall['type']
        )
        res = await self._call_deepseek(prompt)
        return res or "关键点位。"

    async def rewrite_daily_report(self, items):
        prompt = PROMPT_DAILY_REWRITE.format(data_json=json.dumps(items))
        res = await self._call_deepseek(prompt, retries=2)
        if not res: return []
        
        # Parse output
        raw_segments = res.split("ITEM_START")
        clean_items = []
        for seg in raw_segments:
            seg = seg.strip()
            if len(seg) < 10: continue
            if "数据：" in seg: seg = seg.split("数据：")[0].strip()
            clean_items.append(seg)
        return clean_items

    async def analyze_volatility(self, data):
        from src.config import PROMPT_VOLATILITY_ANALYSIS
        prompt = PROMPT_VOLATILITY_ANALYSIS.format(
            title=data['title'],
            platform=data['platform'],
            old_price=data['old_price'],
            new_price=data['new_price'],
            change=data['change']
        )
        res = await self._call_deepseek(prompt)
        if not res: return None
        return res.replace("ITEM_START", "").strip()

    async def rewrite_trending_report(self, items, platform="polymarket", lang="zh"):
        """
        V74: Trending Top20 改写（支持多平台 + 多语言）

        Args:
            items: List of market items to analyze
            platform: Platform name for context
            lang: Language for output ('zh' for Chinese, 'en' for English)

        Returns:
            Processed AI output string or None if failed
        """
        # Select prompt based on language
        if lang == "en":
            prompt_template = PROMPT_TRENDING_REWRITE_EN
        else:
            prompt_template = PROMPT_TRENDING_REWRITE_ZH

        prompt = prompt_template.format(
            platform=platform.capitalize(),
            data_json=json.dumps(items, ensure_ascii=False)
        )

        print(f"🤖 [AI] Generating summaries in {'English' if lang == 'en' else 'Chinese'}...")
        res = await self._call_deepseek(prompt, retries=2, timeout=90)
        if not res:
            return None

        # Parse output - return raw text for the caller to parse
        # This allows more flexible parsing in the ReportService
        return res
