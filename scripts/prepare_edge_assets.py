"""Validate the daily reader and stage only public production assets."""
import argparse
from datetime import date
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.parse import urlsplit,unquote


class Assets(HTMLParser):
    def __init__(self):
        super().__init__();self.paths=set();self.inline=0;self.script=False
    def handle_starttag(self,tag,attrs):
        row=dict(attrs)
        if tag=='script':
            self.script=not row.get('src')
            if row.get('src'):self.paths.add(row['src'])
        if tag=='link' and 'stylesheet' in row.get('rel','').split() and row.get('href'):self.paths.add(row['href'])
    def handle_endtag(self,tag):
        if tag=='script':self.script=False
    def handle_data(self,text):
        if self.script:self.inline+=len(text.encode('utf8'))


def asset_budget(root):
    maximum=0
    for page in root.rglob('*.html'):
        parser=Assets();parser.feed(page.read_text());size=parser.inline
        for value in parser.paths:
            url=urlsplit(value)
            if url.scheme or url.netloc:raise ValueError('external scripts/styles exceed the owned reader boundary')
            path=(root/unquote(url.path).lstrip('/')).resolve()
            if not path.is_relative_to(root) or not path.is_file():raise ValueError('missing or escaping reader asset')
            size+=path.stat().st_size
        if size>20_000:raise ValueError('reader CSS + JS exceeds 20KB: '+str(page.relative_to(root)))
        maximum=max(maximum,size)
    return maximum


def prepare(source:Path,destination:Path):
    source,destination=source.resolve(),destination.resolve()
    if source==destination or source.is_relative_to(destination) or destination.is_relative_to(source):raise ValueError('source and destination must be separate directories')
    if destination.exists():raise ValueError('destination must not already exist')
    required = ('index.html', 'api/latest.json', 'about/index.html', 'feed.xml',
                'assets/css/core.css', 'assets/js/core.js')
    for name in required:
        if not (source/name).is_file():raise ValueError('missing rendered public output: '+name)
    latest=json.loads((source/'api/latest.json').read_text())
    if not latest.get('date') or not isinstance(latest.get('items'),list) or not latest['items']:raise ValueError('invalid or empty published latest edition')
    day = date.fromisoformat(latest['date']).isoformat()
    if day != latest['date']:
        raise ValueError('noncanonical publication date')
    if f'data-latest-edition-date="{latest["date"]}"' not in (source/'index.html').read_text():raise ValueError('homepage does not match latest edition')
    for path in source.rglob('*'):
        if path.is_symlink():raise ValueError('symlinks are not allowed in edge assets')
        if any(part in {'.git','.env','.dev.vars','node_modules'} or part.startswith(('.env.','.dev.vars.')) for part in path.relative_to(source).parts):raise ValueError('private files are not allowed in edge assets')
    # The immutable producer snapshot can still contain archive files during
    # migration. Publish an allowlist so none can be reached at alternate URLs.
    files = set(required) | {
        '404.html', '_headers', 'robots.txt', 'favicon.ico',
        f"{day.replace('-', '/')}/summary-zh.html",
        f'editions/{day}/zh.html', f'editions/{day}/edition.json',
    }
    destination.mkdir(parents=True)
    for name in files:
        if (source / name).is_file():
            (destination / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, destination / name)
    for name in ('assets/images', 'contact', 'legal', 'media-kit'):
        if (source / name).is_dir():
            shutil.copytree(source / name, destination / name,
                            ignore=shutil.ignore_patterns('*.md', '*-en.html'))
    asset_budget(destination)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();prepare(args.source,args.destination)
