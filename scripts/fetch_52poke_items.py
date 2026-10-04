#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从神奇宝贝百科（wiki.52poke.com）抓取道具效果文字，输出 items 效果 JSON。

用于：当 52poke 新增/更新道具效果时，刷新本仓库的 items.json 的 effect 字段。

用法：
  python3 fetch_52poke_items.py [输出json路径]

来源：wiki.52poke.com 的 MediaWiki API（道具页信息框 |img= / 效果段落）。
"""
import re
import json
import sys
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'


def api(params):
    params['format'] = 'json'
    url = 'https://wiki.52poke.com/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def page_wikitext(title):
    d = api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content',
             'rvslots': 'main', 'titles': title})
    for pid, p in d.get('query', {}).get('pages', {}).items():
        rev = p.get('revisions', [{}])[0]
        return rev.get('slots', {}).get('main', {}).get('*', '') or rev.get('*', '')
    return ''


def item_intro_and_effect(wt):
    """从道具页 wikitext 提取：说明（intro）与效果（==效果== 段落）。"""
    text = ''
    # 信息框里的 img 字段（部分道具在这里有说明）
    m = re.search(r'\|\s*(?:text|效果|effect|说明|desc)\s*=\s*([^|\n]+)', wt)
    if m:
        text = re.sub(r'zh-hans[：:]\s*', '', m.group(1)).strip()
    # ==效果== 段落
    detail = ''
    m2 = re.search(r'==\s*效果\s*==\s*\n([\s\S]*?)(?=\n==[^=]|$)', wt)
    if m2:
        lines = []
        for ln in m2.group(1).split('\n'):
            ln = ln.strip()
            if ln.startswith('*'):
                ln = re.sub(r'<ref[^>]*>[\s\S]*?</ref>|<ref[^/>]*/>', '', ln)
                ln = re.sub(r'\[\[(?:[^\]]*\|)?([^\]]*)\]\]', r'\1', ln)
                ln = re.sub(r'\{\{[^{}]*\}\}', '', ln).strip()
                if ln:
                    lines.append(ln)
        detail = '\n'.join(lines)
    return text, detail


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'items-effect.json'

    print('== 从 52poke 抓取道具效果 ==')
    # 1) 拿道具列表页的链接
    d = api({'action': 'parse', 'page': '道具列表', 'prop': 'links'})
    links = [l['*'] for l in d.get('parse', {}).get('links', [])]
    items = [t for t in links if t.endswith('（道具）')]
    print('  道具条目 %d' % len(items))

    result = []
    for i, title in enumerate(items, 1):
        name = title.replace('（道具）', '')
        wt = page_wikitext(title)
        text, detail = item_intro_and_effect(wt)
        result.append({'name': name, 'text': text, 'effect': detail})
        if i % 100 == 0:
            print('  ...%d/%d' % (i, len(items)))

    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('  完成，输出 %s（%d 条）' % (out, len(result)))


if __name__ == '__main__':
    main()
