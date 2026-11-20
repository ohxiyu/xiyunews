import {cp, mkdir, readFile, readdir, rm, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {marked} from 'marked';

const snapshot = process.argv[2] ?? '.edition-snapshot';
const output = 'dist';
const site = 'https://xiyu.news';

const escape = value => value.replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);

function page(title, content, section = '') {
  return `<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escape(title)} · xiyu.news</title>
<link rel="icon" href="/assets/mark.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css">
<a class="skip" href="#content">跳到正文</a>
<header class="masthead"><div class="wrap topline">
<a class="brand" href="/"><img src="/assets/mark.svg" alt="" width="32" height="32">xiyu<span>.news</span></a>
<nav aria-label="主导航"><a href="/">快讯</a><a href="/history/"${section === 'history' ? ' aria-current="page"' : ''}>往期日报</a><a href="/about/"${section === 'about' ? ' aria-current="page"' : ''}>关于</a></nav>
</div></header>
<main class="wrap" id="content"><div class="pane prose">${content}</div></main>
<footer class="wrap footer"><a href="/">xiyu.news</a><div><a href="/contact/">联系</a><a href="/legal/">内容权利</a></div></footer>
</html>`;
}

async function put(path, content) {
  const destination = join(output, path);
  await mkdir(join(destination, '..'), {recursive: true});
  await writeFile(destination, content);
}

function digestPath(date) {
  return '/' + date.replaceAll('-', '/') + '/summary-zh.html';
}

function xml(body) {
  return '<?xml version="1.0" encoding="UTF-8"?>\n' + body + '\n';
}

const dates = (await readdir(join(snapshot, '_posts')))
  .flatMap(name => name.match(/^(\d{4}-\d{2}-\d{2})-summary-zh\.md$/)?.[1] ?? [])
  .sort().reverse();
const latestJson = await readFile(join(snapshot, 'api/latest.json'));
const latest = JSON.parse(latestJson);
if (!dates.length || latest.date !== dates[0] || !latest.items?.length) {
  throw new Error('Archive snapshot is incomplete or inconsistent');
}

await rm(output, {recursive: true, force: true});
await cp('site', output, {recursive: true, filter: path => !path.endsWith('/CNAME')});
await put('api/latest.json', latestJson);
for (const date of dates) {
  const fragment = await readFile(join(snapshot, 'editions', date, 'zh.html'), 'utf8');
  const match = fragment.match(/^\s*(<div class="daily-feed-content"[^>]*>)([\s\S]*)<\/div>\s*$/);
  if (!match || !match[2].trim()) throw new Error(`Missing historical edition ${date}`);
  const body = match[2].includes('data-core-feed=') ? match[2] : marked.parse(match[2]);
  await put(`editions/${date}/zh.html`, match[1] + body + '</div>');
  await put(digestPath(date).slice(1), page(`${date} 日报`,
    `<a href="/history/">全部往期日报</a><h1>${date} 日报</h1>${body}`, 'history'));
}

await put('history/index.html', page('往期日报', `<h1>往期日报</h1>
<p>浏览 xiyu.news 已发布的加密与 AI 日报。</p>
<ul class="archive-list">${dates.map(date => `<li><a href="${digestPath(date)}">${date} 日报</a></li>`).join('')}</ul>
<p><a href="/history/feed.xml">日报存档 RSS</a></p>`, 'history'));

await put('history/feed.xml', xml(`<rss version="2.0"><channel><title>xiyu.news 往期日报</title><link>${site}/history/</link><description>已发布的加密与 AI 日报</description>${dates.slice(0, 30).map(date => {
  const url = site + digestPath(date);
  return `<item><title>${date} 日报</title><link>${url}</link><guid>${url}</guid><pubDate>${new Date(date + 'T00:00:00Z').toUTCString()}</pubDate></item>`;
}).join('')}</channel></rss>`));

await put('sitemap.xml', xml(`<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['/', '/history/', '/about/', '/contact/', '/legal/', ...dates.map(digestPath)].map(url => `<url><loc>${site + url}</loc></url>`).join('')}</urlset>`));
await put('about/index.html', page('关于', `<h1>关于 xiyu.news</h1>
<p>xiyu.news 聚合加密市场快讯、交易所公告和市场异动，支持按频道、币种或关键词浏览。</p>
<p>快讯、翻译和 AI 解读由 <a href="https://eqn.news/">方程式新闻</a> 提供。页面采用北京时间。</p>
<p>项目由 <a href="https://x.com/ohxiyu">xiyu</a> 维护。此前发布的加密与 AI 日报可在 <a href="/history/">往期日报</a> 查阅。</p>`, 'about'));
await put('contact/index.html', page('联系', `<h1>联系</h1>
<p>通过 <a href="https://x.com/ohxiyu">@ohxiyu</a> 提交页面反馈、更正或内容权利请求。请附上受影响的页面地址及相关材料。</p>`));
await put('legal/index.html', page('内容权利', `<h1>内容权利</h1>
<p>软件依据 <a href="/legal/software-license.txt">MIT 许可证</a> 发布。新闻与第三方材料的权利归各自权利人。</p>
<p><a href="/legal/content-rights.txt">内容与数据权利</a> · <a href="/legal/third-party-notices.txt">第三方声明</a> · <a href="/contact/">联系与更正</a></p>`));
await put('404.html', page('页面未找到', '<h1>页面未找到</h1><p><a href="/">查看最新快讯</a> · <a href="/history/">查看往期日报</a></p>'));
console.log(`Built xiyu.news with ${dates.length} archived editions (last ${dates[0]}).`);
