// Keep article-specific facts, removing only identifiable publication boilerplate.
export function mainBody(value='') {
  let text=value.trim();
  const general=/(?:这是|此为|这是一则|本公告为)?一般性(?:币安交易所|币安)?公告[。．，,：:]?/;
  const first=text.search(general);
  if(first>=0){
    if(text.slice(0,first).trim()) text=text.slice(0,first).trim();
    else {
      const end=text.indexOf('\n',first);
      text=end>=0?text.slice(end+1).trim():'';
    }
  }
  text=text.replace(/^亲爱的用户[：:]\s*/, '');
  const tail=text.search(/(?:^|\n)\s*(?:(?:注[：:]?\s*)?英文原版|感谢您对币安的支持|免责声明[：:]?|风险提示[：:]?|欧易将持续为您提供|币安团队|欧易团队)/);
  if(tail>=0) text=text.slice(0,tail).trim();
  return text;
}
export function marketLine(event) {
  if (event.signal?.policy_version === 2) return event.title;
  const change=event.signal?.change ?? Number(event.title.match(/([+-]\d+(?:\.\d+)?)%/)?.[1]);
  const symbol=(event.symbol||event.title.split(' ')[0]).replace(/USDT$/,'');
  if(!Number.isFinite(change)) return event.title;
  return `${symbol} 币约 2–3 分钟内${change>=0?'上涨':'下跌'} ${Math.abs(change).toFixed(2)}%`;
}

export function marketBody(event) {
  const match=(event.body||'').match(/24h quote volume:\s*([\d.]+) USDT; group:\s*(LOW|MID|HIGH)/);
  if(!match) return mainBody(event.body)||'以分钟收盘价比较现货价格变化。';
  const volume=Number(match[1]);
  return `24 小时成交额 ${volume.toLocaleString('zh-CN',{maximumFractionDigits:0})} USDT · ${{LOW:'低',MID:'中',HIGH:'高'}[match[2]]}成交额组。与前三个分钟桶的收盘价比较，非严格滚动 180 秒。`;
}

// Extract concise article facts, not the introduction or legal boilerplate.
export function announcementBrief(event) {
  const clean=value=>(value||'').replace(/(?:尊敬的|亲爱的)用户[：:]?/g,'').trim();
  const excluded=/一般性.*公告|本文所述产品|所在地区|免责声明|风险提示|感谢.*支持|条款与条件|不构成.*建议|更多信息.*参考|为提升.*体验|为给用户提供/;
  const split=value=>clean(value).split(/(?<=[。！？])\s*|\n+/).map(s=>s.trim()).filter(s=>s.length>8&&!excluded.test(s));
  const action=/上线|下线|下架|移除|暂停|恢复|升级|硬分叉|调整|开放|停止|维护|新增|支持|上市|交易对|UTC|\d{1,2}:\d{2}/;
  let facts=split(event.body).filter(s=>action.test(s));
  if(!facts.length) facts=split(event.brief);
  if(!facts.length) facts=split(event.body);
  const selected=[...new Set(facts)].filter(s=>s!==event.title).slice(0,2).join(' ');
  if(!selected) return '公告正文待补充';
  return selected.length>180?selected.slice(0,177)+'…':selected;
}

export function announcementCoins(event) {
  const result=new Set();
  const ignore=new Set(['USDT','USDC','USD','API','UTC','ETF','NFT','VIP','OKX','BUSD','CEO','APR','APY','POS','POW']);
  const add=value=>{const s=value.toUpperCase().replace(/(?:USDT|USDC|USD)$/,'');if(s&&!ignore.has(s)&&/^[A-Z0-9]{2,20}$/.test(s))result.add(s);};
  if(event.symbol)add(event.symbol);
  const title=event.title||'';
  for(const match of title.matchAll(/\b([A-Z0-9]{2,20})\s*[/／-]?\s*(?:USDT|USDC|USD)\b/g))add(match[1]);
  for(const match of title.matchAll(/[（(]\s*([A-Z][A-Z0-9]{1,19})\s*[）)]/g))add(match[1]);
  for(const match of title.matchAll(/\b([A-Z][A-Z0-9]{1,19})\s*(?:永续|现货|代币|网络|币种|交易对|股票|合约)/g))add(match[1]);
  // Only explicit pairs in the body; unrelated uppercase acronyms are not coin names.
  if(!result.size)for(const match of (event.body||'').matchAll(/\b([A-Z0-9]{2,20})\s*[/／]\s*(?:USDT|USDC|USD)\b/g))add(match[1]);
  return [...result].slice(0,12);
}
