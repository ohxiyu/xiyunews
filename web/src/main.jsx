import React from 'react';
import {createRoot} from 'react-dom/client';
import {flushSync} from 'react-dom';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import './style.css';
function App(){return <div className="dashboard">
<header className="masthead"><div className="header-inner"><a className="brand" href="/" aria-label="FomoBTC 首页"><span className="brand-mark">F.</span>FomoBTC</a><nav aria-label="主导航">{[['live','信息流'],['history','历史记录'],['health','运行状态']].map(([v,t])=><Button key={v} variant="ghost" className={v==='live'?'active':''} data-view={v} aria-current={v==='live'?'page':undefined}>{t}</Button>)}</nav><button id="theme" className="theme-button" aria-label="切换深色模式" title="切换主题">◐</button></div></header>
<main className="content"><h1 id="heading" className="sr-only">信息流</h1>
<div className="edition"><div><span className="edition-label">实时</span><strong id="edition-date">FomoBTC</strong><span id="connection" role="status">连接中</span></div><div className="top-stats"><span><b id="total">—</b> 条记录</span><span><b id="sources">—</b> 来源正常</span><span><b id="pending">—</b> 待发送</span></div></div>
<div className="channel-status" id="telegram-status">Telegram 状态待核验</div>
<div id="warning" role="status" hidden/>
<section id="feed-view"><div className="toolbar"><div className="tabs" aria-label="事件类型">{[['','全部'],['market','行情异动'],['announcement','交易所公告']].map(([v,t])=><Button key={v} variant="ghost" className={v===''?'active':''} data-kind={v} aria-pressed={v===''}>{t}</Button>)}</div><Button id="follow" variant="outline" aria-pressed="true">自动更新：开</Button></div><div className="exchanges" id="exchanges" aria-label="交易所" hidden>{[['','全部交易所'],['binance','Binance'],['okx','OKX'],['bybit','Bybit'],['bitget','Bitget'],['kucoin','KuCoin'],['htx','HTX'],['upbit','Upbit'],['bithumb','Bithumb'],['gate','Gate'],['mexc','MEXC'],['hyperliquid','Hyperliquid']].map(([v,t])=><Button key={v} variant="ghost" className={v===''?'active':''} data-source={v} aria-pressed={v===''}>{t}</Button>)}</div><div className="filters"><Input id="search" aria-label="搜索币种或公告" placeholder="搜索币种或公告…" type="search"/><span id="updated" role="status">等待数据</span></div><div id="feed" aria-label="市场信息流"/><Button variant="outline" id="more" hidden>加载更早记录 ↓</Button></section>
<section id="health-view" hidden><h2>来源与交付状态</h2><div id="health-list"/><div className="latency">本机判断 P99 <span id="latency">—</span><small>不包含网络与推送耗时</small></div><div id="monitor"/><pre id="version"/></section>
<footer><a className="footer-brand" href="/">FomoBTC</a><span>现货异动与官方公告 · 持续采集，及时获知</span><small>按发现时间倒序 · 网页关闭不影响后台采集与推送</small></footer></main></div>}
flushSync(()=>createRoot(document.getElementById('root')).render(<App/>));
const theme=document.getElementById('theme');
function setTheme(dark){document.documentElement.dataset.theme=dark?'dark':'light';theme.setAttribute('aria-label',dark?'切换浅色模式':'切换深色模式');theme.setAttribute('aria-pressed',String(dark));}
try{setTheme(localStorage.getItem('fomobtc-theme')==='dark');}catch{setTheme(false);}
theme.onclick=()=>{const dark=document.documentElement.dataset.theme!=='dark';setTheme(dark);try{localStorage.setItem('fomobtc-theme',dark?'dark':'light');}catch{/* Storage may be unavailable in private browsing. */}};
document.getElementById('edition-date').textContent=new Date().toLocaleDateString('sv-SE').replaceAll('-','.');
import('./controller.js');
