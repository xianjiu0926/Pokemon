#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补齐 items.json 中 effect 为空的条目：从神奇宝贝百科（wiki.52poke.com）抓取道具的
「效果 / 使用效果 / 游戏中」段落，清洗成纯文本后写回。

相比旧版的关键改进：**批量请求**——MediaWiki API 一次可查最多 50 个页面标题，
把请求量从「1 条 1 次」降到「50 条 1 次」，彻底避开 429 限流。

用法：
  python3 fetch_item_effects.py [--merge]

流程：
  1. 读 items.json，找出 effect 为空的条目；
  2. 批量抓取（50/批），清洗后增量写入 items-effect-fill.json（可断点续跑）；
  3. 加 --merge 时，把 fill 里抓到的 effect 合并回 items.json。

来源：wiki.52poke.com 的 MediaWiki API（道具页 wikitext）。
"""
import re
import json
import sys
import time
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.1 (batch)'
FILL = 'items-effect-fill.json'
BATCH = 50
DELAY = 0.4


def api(params):
    params['format'] = 'json'
    url = 'https://wiki.52poke.com/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def pages_wikitext(titles):
    """批量抓取 titles 的 wikitext，返回 {title: wikitext}。"""
    titles = list(titles)
    d = api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content',
             'rvslots': 'main', 'titles': '|'.join(titles), 'redirects': 1})
    q = d.get('query', {})
    pages = {}
    for pid, p in q.get('pages', {}).items():
        if p.get('missing'):
            continue
        rev = p.get('revisions', [{}])[0]
        wt = rev.get('slots', {}).get('main', {}).get('*', '') or rev.get('*', '')
        pages[p.get('title', '')] = wt
    # 标题规范化 / 重定向映射（from -> to）
    redirect = {r.get('from', ''): r.get('to', '') for r in q.get('redirects', [])}
    normalized = {n.get('from', ''): n.get('to', '') for n in q.get('normalized', [])}
    out = {}
    for t in titles:
        cur = t
        if cur in normalized:
            cur = normalized[cur]
        if cur in redirect:
            cur = redirect[cur]
        out[t] = pages.get(cur, '')
    return out


def extract_section(wt, heading, level=2):
    eq = '=' * level
    m = re.search(r'%s\s*%s\s*%s\s*\n([\s\S]*?)(?=\n%s[^=]|\Z)' % (eq, re.escape(heading), eq, eq), wt)
    return m.group(1) if m else ''


# ---- wikitext 清洗 ----
TEMPLATE_REMOVE = {'msp', 'tcgsp', 'sprites', 'sprite'}
TEMPLATE_LAST_ARG = {'side', 'dl', 'advc', 'main', 'main2', 'see', 'tc', 'weather', 'pkm', 'p'}
TEMPLATE_FIRST_ARG = {'s', 'm', 'i', 'a', 't', 'type', 'ty', 'bag', 'game', 'par',
                      'gens', 'tt', 'ps', 'mov', 'id', 'form', 'rt', 'badge', 'stat',
                      'togglelink', 'roundy', 'roundytl', 'roundytr', 'roundybl', 'roundybr'}
GEN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
GEN_WORD = '一二三四五六七八九十'


def clean_template(inner):
    inner = inner.strip()
    if '|' in inner:
        parts = [p.strip() for p in inner.split('|')]
        name = parts[0].strip()
        args = parts[1:]
    else:
        name = inner
        args = []
    nl = name.lower()
    if name == '!':
        return '|'
    if nl in TEMPLATE_REMOVE:
        return ''
    if nl == 'frac':
        if len(args) >= 2:
            return args[0] + '⁄' + args[1]
        return '/'.join(args)
    if nl in ('gen', 'gens'):
        a = args[0] if args else ''
        n = GEN_NUM.get(a)
        if n is None and a.isdigit():
            n = int(a)
        if n and 1 <= n <= 10:
            return '第' + GEN_WORD[n - 1] + '世代'
        return a
    if not args:
        return ''
    if nl in TEMPLATE_LAST_ARG:
        return args[-1]
    if nl in TEMPLATE_FIRST_ARG:
        return args[0]
    for a in reversed(args):
        if a:
            return a
    return ''


def strip_templates(s):
    """反复剥离最内层 {{...}} 模板（支持嵌套）。"""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\{\{([^{}]*)\}\}', lambda m: clean_template(m.group(1)), s)
    return s


def clean_line(ln):
    ln = re.sub(r'<!--[\s\S]*?-->', '', ln)
    ln = re.sub(r'<ref[^>]*>[\s\S]*?</ref>', '', ln)
    ln = re.sub(r'<ref[^/>]*/>', '', ln)
    ln = re.sub(r'-\{zh-hans[:：]([^;}]+)(?:;[^}]*)?\}-', r'\1', ln)
    ln = re.sub(r'-\{([^}]*)\}-', r'\1', ln)
    ln = strip_templates(ln)
    ln = re.sub(r'\[\[(?:File|文件|Image):[^\]]*\]\]', '', ln)
    ln = re.sub(r'\[\[([^\]|]*)\|([^\]]*)\]\]', r'\2', ln)
    ln = re.sub(r'\[\[([^\]]*)\]\]', r'\1', ln)
    ln = re.sub(r'\[https?://[^\s\]\]]+(?:\s+([^\]]*))?\]', lambda m: m.group(1) or '', ln)
    ln = re.sub(r"'''?", '', ln)
    ln = re.sub(r'<br\s*/?>', '\n', ln)
    ln = re.sub(r'<[^>]+>', '', ln)
    ln = ln.replace('\u00a0', ' ')
    ln = re.sub(r'[ \t]+', ' ', ln)
    ln = re.sub(r'([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]) ([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef])', r'\1\2', ln)
    return ln.strip()


def extract_effect(wt):
    # 先按二级标题（==效果== / ==使用效果== / ==游戏中==）取，取不到再回退三级标题（===效果===）
    for level in (2, 3):
        for heading in ('效果', '使用效果', '游戏中', '对战', '对战效果'):
            sec = extract_section(wt, heading, level)
            if not sec:
                continue
            sec = re.sub(r'<!--[\s\S]*?-->', '', sec)          # 跨行注释
            sec = re.sub(r'^\s*\{\{main[^\n]*\}\}\s*$', '', sec, flags=re.M)  # 另见模板
            sec = strip_templates(sec)                          # 跨行模板（如 对话/中）
            lines = []
            for raw in sec.split('\n'):
                s = raw.strip()
                if not s or s[0] in '{=|;:':
                    continue
                if s.startswith('*'):
                    depth = 0
                    while s.startswith('*'):
                        depth += 1
                        s = s[1:]
                    s = s.strip()
                    c = clean_line(s)
                    if not c:
                        continue
                    prefix = '  ' * max(0, depth - 1)
                    lines.append(prefix + c)
                else:
                    c = clean_line(s)
                    if c:
                        lines.append(c)
            if lines:
                return '\n'.join(lines)
    return ''


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    merge = '--merge' in sys.argv[1:]
    items = load_json('items.json')['data']

    # 需要补的：effect 为空 且（fill 里没有 或 fill 里 effect 也为空）
    try:
        fill = load_json(FILL)
    except Exception:
        fill = {}

    todo = []
    for it in items:
        if (it.get('effect') or '').strip():
            continue
        fv = fill.get(it['name'])
        if not fv or not fv.get('effect'):
            todo.append(it)

    print('待补条目：%d' % len(todo))

    # 分批
    titles = [it['name'] + '（道具）' for it in todo]
    batches = [titles[i:i + BATCH] for i in range(0, len(titles), BATCH)]
    print('共 %d 批（每批 %d）' % (len(batches), BATCH))

    new = 0
    for bi, batch in enumerate(batches, 1):
        ok = False
        for attempt in range(4):
            try:
                wtmap = pages_wikitext(batch)
                ok = True
                break
            except Exception as e:
                time.sleep(4)
        if not ok:
            print('  第 %d/%d 批失败（限流），跳过' % (bi, len(batches)))
            continue
        for title in batch:
            name = title[:-4]  # 去掉 '（道具）'
            wt = wtmap.get(title, '')
            eff = extract_effect(wt) if wt else ''
            it = next((x for x in todo if x['name'] + '（道具）' == title), None)
            en = it['en'] if it else ''
            cat = it['cat'] if it else ''
            fill[name] = {'name': name, 'en': en, 'cat': cat, 'title': title, 'effect': eff}
            if eff:
                new += 1
        with open(FILL, 'w', encoding='utf-8') as f:
            json.dump(fill, f, ensure_ascii=False, indent=1)
        print('  批 %d/%d 完成，累计新得 %d' % (bi, len(batches), new))
        time.sleep(DELAY)

    print('抓取完成：新得效果 %d，缓存 %s' % (new, FILL))

    if merge:
        filled = 0
        for it in items:
            if not (it.get('effect') or '').strip():
                e = (fill.get(it['name']) or {}).get('effect', '')
                if e:
                    it['effect'] = e
                    filled += 1
        with open('items.json', 'w', encoding='utf-8') as f:
            json.dump({'count': len(items), 'data': items}, f, ensure_ascii=False, separators=(',', ':'))
        nonempty = sum(1 for it in items if (it.get('effect') or '').strip())
        print('合并完成：本次补全 %d，items.json effect 非空 %d/%d' % (filled, nonempty, len(items)))


if __name__ == '__main__':
    main()
