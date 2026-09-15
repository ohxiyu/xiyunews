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
  const change=event.signal?.change ?? Number(event.title.match(/([+-]\d+(?:\.\d+)?)%/)?.[1]);
  const symbol=(event.symbol||event.title.split(' ')[0]).replace(/USDT$/,'');
  if(!Number.isFinite(change)) return event.title;
  return `${symbol} 币约 2–3 分钟内${change>=0?'上涨':'下跌'} ${Math.abs(change).toFixed(2)}%`;
}
