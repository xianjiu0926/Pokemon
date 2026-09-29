#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从神奇宝贝百科（wiki.52poke.com）抓取特性文字数据，输出 abilities 结构化 JSON。

来源：wiki.52poke.com 的「特性列表」及每个特性页（信息框 + 特性效果段落）。

用法：
  python3 fetch_abilities.py [输出json路径]

输出 schema（与 abilities.json 一致）：
  [ { "id": 1, "name": "恶臭", "jp": "あくしゅう", "en": "Stench",
      "desc": "简介…", "effect": "详细效果…" } ]
"""
import re
import json
import sys
import time
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'


def api(params):
    params['format'] = 'json'
    url = 'https://wiki.52poke.com/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def wikitext(title):
    d = api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content',
             'rvslots': 'main', 'titles': title})
    for pid, p in d.get('query', {}).get('pages', {}).items():
        rev = p.get('revisions', [{}])[0]
        return rev.get('slots', {}).get('main', {}).get('*', '') or rev.get('*', '')
    return ''


def zh_hans(s):
    """从 -{zh-hans:XXX;zh-hant:YYY}- 中提取简体。"""
    m = re.search(r'zh-hans[:：]([^;}]+)', s or '')
    return m.group(1).strip() if m else s.strip()


def info_value(wt, key):
    m = re.search(r'\|\s*%s\s*=\s*([^|\n]*)' % re.escape(key), wt)
    return m.group(1).strip() if m else ''


def section(wt, title):
    m = re.search(r'==\s*%s\s*==\s*\n([\s\S]*?)(?=\n==[^=]|$)' % re.escape(title), wt)
    if not m:
        return ''
    out = []
    for ln in m.group(1).split('\n'):
        ln = ln.strip()
        if ln.startswith('*'):
            ln = re.sub(r'<ref[^>]*>[\s\S]*?</ref>|<ref[^/>]*/>', '', ln)
            ln = re.sub(r'\[\[(?:[^\]]*\|)?([^\]]*)\]\]', r'\1', ln)
            ln = re.sub(r'\{\{[^{}]*\}\}', '', ln).strip()
            if ln:
                out.append(ln)
    return '\n'.join(out)


def parse_ability(title):
    wt = wikitext(title)
    # 信息框
    box = re.search(r'\{\{[^{}\n]*信息框[\s\S]*?\n\}\}', wt)
    if not box:
        return None
    b = box.group(0)
    return {
        'id': int(info_value(b, 'n') or 0),
        'name': info_value(b, 'name'),
        'jp': info_value(b, 'jpname'),
        'en': info_value(b, 'enname'),
        'desc': zh_hans(info_value(b, 'text')),
        'effect': section(wt, '特性效果'),
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'abilities-new.json'

    print('== 抓取 52poke 特性列表 ==')
    d = api({'action': 'parse', 'page': '特性列表', 'prop': 'links'})
    titles = [l['*'] for l in d.get('parse', {}).get('links', [])]
    abilities = sorted(t for t in titles if t.endswith('（特性）'))
    print('  特性条目 %d' % len(abilities))

    result = []
    for i, title in enumerate(abilities, 1):
        try:
            item = parse_ability(title)
            if item and item['name']:
                result.append(item)
        except Exception as e:
            print('  [!] %s 解析失败: %s' % (title, e))
        if i % 50 == 0:
            print('  ...%d/%d' % (i, len(abilities)))
        time.sleep(0.2)

    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('  完成，输出 %s（%d 条）' % (out, len(result)))


if __name__ == '__main__':
    main()
