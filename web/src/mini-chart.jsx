import React,{useEffect,useRef,useState} from 'react';
export function MiniChart({pair}){
  const [open,setOpen]=useState(false),host=useRef(null);
  const valid=/^[A-Z0-9]{2,24}USDT$/.test(pair);
  useEffect(()=>{
    if(!open||!valid)return;
    const node=host.current;
    const script=document.createElement('script');
    script.src='https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js';
    script.async=true;
    script.textContent=JSON.stringify({symbol:'BINANCE:'+pair,width:'100%',height:180,locale:'zh_CN',dateRange:'1D',colorTheme:'dark',isTransparent:false,backgroundColor:'#0c0e11',autosize:false,chartOnly:true});
    node.appendChild(script);
    return()=>node.replaceChildren();
  },[open,pair,valid]);
  if(!valid)return null;
  return <section className="mini-chart"><button onClick={()=>setOpen(!open)}>{open?'收起走势图':'查看 TradingView 走势图'}</button>{open&&<><div ref={host} className="chart-host"/><small>当前 1 日走势 · 非事件时刻截图 · <a href={'https://www.tradingview.com/chart/?symbol=BINANCE%3A'+pair} target="_blank" rel="noopener noreferrer">TradingView ↗（图表不可用时查看）</a></small></>}</section>;
}
