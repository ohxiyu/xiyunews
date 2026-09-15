import React from 'react';
import {createRoot} from 'react-dom/client';
import {flushSync} from 'react-dom';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Badge} from '@/components/ui/badge';
import './style.css';
function App(){return <main className="dashboard">
<header className="topbar"><a className="brand" href="/">FOMO<span>BTC</span></a><nav aria-label="主导航">{[['live','实时'],['history','历史'],['health','状态']].map(([v,t])=><Button key={v} variant="ghost" size="sm" className={'nav '+(v==='live'?'active':'')} data-view={v}>{t}</Button>)}</nav><Badge variant="outline" id="connection">连接中</Badge><span className="top-stats">记录 <b id="total">—</b> · 来源 <b id="sources">—</b> · 待发 <b id="pending">—</b></span></header>
<h1 id="heading" className="sr-only">数据库记录查看</h1><div id="warning" role="status" hidden/>
<section id="feed-view"><div className="toolbar"><div className="tabs">{[['','全部'],['market','异动'],['announcement','公告']].map(([v,t])=><Button key={v} variant="ghost" size="sm" className={v===''?'active':''} data-kind={v}>{t}</Button>)}</div><select aria-label="来源" id="source"><option value="">全部来源</option><option value="binance_spot">Binance 现货</option><option value="binance_futures">Binance 合约</option><option value="binance">Binance 公告</option><option value="okx">OKX</option><option value="hyperliquid">Hyperliquid</option></select><Input id="search" aria-label="搜索" placeholder="币种 / 公告" type="search"/><Button id="follow" variant="outline" size="sm" aria-pressed="true">自动更新：开</Button><span id="updated">等待数据</span></div><div id="feed" aria-label="数据库记录"/><Button variant="outline" size="sm" id="more" hidden>加载更早记录</Button><div className="footnote">只读数据库查看 · 按发现时间倒序 · 点标题展开正文 · 服务无需浏览器运行</div></section>
<section id="health-view" hidden><h2>来源与交付状态</h2><div id="health-list"/><div>本机判断 P99 <span id="latency">—</span>（非推送延迟）</div><div id="monitor"/><pre id="version"/></section>
</main>}
flushSync(()=>createRoot(document.getElementById('root')).render(<App/>));
import('./controller.js');
