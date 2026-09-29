#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补齐 moves.json 中 effect 为空的条目：从神奇宝贝百科（wiki.52poke.com）抓取招式的
「招式附加效果」段落（渲染后 HTML），清洗成纯文本后写回。

说明：
  - 招式效果段落里含大量专用模板（{{招式效果/…}}），所以走 action=parse 拿渲染好的
    HTML（模板已展开），再剥标签取纯文本；这类接口一次只能查一页，因此逐页抓、单线程。
  - 结果增量写入 moves-effect-fill.json（可断点续跑），--merge 时合并回 moves.json。

用法：
  python3 fetch_move_effects.py [--merge]

来源：wiki.52poke.com 的 MediaWiki API。
"""
import re
import json
import sys
import time
import html as H
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.1 (move)'
FILL = 'moves-effect-fill.json'
DELAY = 0.15


def api(params):
    params['format'] = 'json'
    url = 'https://wiki.52poke.com/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_html(title):
    d = api({'action': 'parse', 'page': title, 'prop': 'text',
             'variant': 'zh-hans', 'redirects': 1})
    return d.get('parse', {}).get('text', {}).get('*', '')


def normalize_width(s):
    out = []
    for ch in s:
        code = ord(ch)
        if 0xFF21 <= code <= 0xFF3A:
            out.append(chr(code - 0xFF21 + 0x41))
        elif 0xFF10 <= code <= 0xFF19:
            out.append(chr(code - 0xFF10 + 0x30))
        else:
            out.append(ch)
    return ''.join(out)


def fullwidth(s):
    """半角转全角（V热焰 等标题用全角）。"""
    out = []
    for ch in s:
        code = ord(ch)
        if 0x41 <= code <= 0x5A:
            out.append(chr(code - 0x41 + 0xFF21))
        elif 0x61 <= code <= 0x7A:
            out.append(chr(code - 0x61 + 0xFF41))
        else:
            out.append(ch)
    return ''.join(out)


def resolve_html(name):
    """优先原名（+招式），失败则用 converttitles 转繁体再试（含无后缀的 Z/超极巨招式）。"""
    title = name + '（招式）'
    h = get_html(title)
    if h:
        return title, h
    # 繁体转换（MediaWiki converttitles）
    trad = convert_title(name)
    if trad and trad != name:
        for t in (trad + '（招式）', trad):
            h2 = get_html(t)
            if h2:
                return t, h2
    # 无后缀原名（部分 Z/超极巨招式标题不带「（招式）」）
    h_nosuffix = get_html(name)
    if h_nosuffix:
        return name, h_nosuffix
    # 半角/全角兜底（V热焰）
    for variant in (normalize_width(name), fullwidth(name)):
        if variant == name:
            continue
        title3 = variant + '（招式）'
        h3 = get_html(title3)
        if h3:
            return title3, h3
    return title, ''


_convert_cache = {}


def convert_title(name):
    if name in _convert_cache:
        return _convert_cache[name]
    try:
        d = api({'action': 'query', 'titles': name, 'converttitles': 1})
        conv = d.get('query', {}).get('converted', [])
        trad = conv[0].get('to', '') if conv else ''
    except Exception:
        trad = ''
    _convert_cache[name] = trad
    return trad


def extract_section(html, want):
    """取标题为 want 的段落内容（到下一个 h2 为止，含 h3 子段）。"""
    m = re.search(r'<span class="mw-headline" id="' + re.escape(want) + r'">.*?</span></h[1-6]>(.*?)(?=<h2\b|\Z)', html, re.S)
    return m.group(1) if m else ''


def html_to_text(seg):
    # 去掉编辑链接 / 目录
    seg = re.sub(r'<span class="mw-editsection">.*?</span>', '', seg, flags=re.S)
    seg = re.sub(r'<div class="toc">.*?</div>', '', seg, flags=re.S)
    seg = re.sub(r'<style[^>]*>.*?</style>|<script[^>]*>.*?</script>', '', seg, flags=re.S)
    # h3~h6 子段标题 → 标记行（只取 mw-headline 文本，避开编辑链接）
    seg = re.sub(r'<h[3-6][^>]*>.*?<span class="mw-headline"[^>]*>(.*?)</span>.*?</h[3-6]>',
                 lambda m: '\n【' + H.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() + '】\n',
                 seg, flags=re.S)
    # 列表项
    seg = re.sub(r'<li[^>]*>', '\n- ', seg)
    # 段落/换行
    seg = re.sub(r'<(?:p|div|dl|dd|tr|br|ul|ol)[^>]*>', '\n', seg)
    seg = re.sub(r'<(?:td|th)[^>]*>', ' | ', seg)
    # 剥掉剩余标签
    seg = re.sub(r'<[^>]+>', '', seg)
    seg = H.unescape(seg)
    # 逐行清洗
    out = []
    for ln in seg.split('\n'):
        ln = re.sub(r'[ \t]+', ' ', ln).strip()
        # 去掉编辑链接残留
        ln = re.sub(r'编辑(?:源代码)?[\]】]?', '', ln).strip()
        if not ln or ln in ('主页面：',) or ln.startswith('主页面：'):
            continue
        if ln.startswith('[') and ln.endswith(']') and '编辑' in ln:
            continue
        out.append(ln)
    # 合并：连续非【】行用换行，【】标记行单独成段
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 子段标题后接段落，避免多余换行
    text = text.replace('】\n\n', '】\n')
    return text.strip()


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    merge = '--merge' in sys.argv[1:]
    moves = load_json('moves.json')['data']

    try:
        fill = load_json(FILL)
    except Exception:
        fill = {}

    todo = []
    for m in moves:
        if (m.get('effect') or '').strip():
            continue
        fv = fill.get(m['name'])
        if not fv or not fv.get('effect'):
            todo.append(m)

    print('待补招式：%d' % len(todo))

    new = 0
    for i, m in enumerate(todo, 1):
        name = m['name']
        eff = ''
        for attempt in range(3):
            try:
                title, html = resolve_html(name)
                seg = extract_section(html, '招式附加效果') if html else ''
                eff = html_to_text(seg)
                break
            except Exception as e:
                time.sleep(3)
        fill[name] = {'name': name, 'en': m.get('en', ''), 'effect': eff}
        if eff:
            new += 1
        if i % 25 == 0:
            with open(FILL, 'w', encoding='utf-8') as f:
                json.dump(fill, f, ensure_ascii=False, indent=1)
            print('  %d/%d（新得 %d）' % (i, len(todo), new))
        time.sleep(DELAY)

    with open(FILL, 'w', encoding='utf-8') as f:
        json.dump(fill, f, ensure_ascii=False, indent=1)
    print('抓取完成：新得效果 %d，缓存 %s' % (new, FILL))

    if merge:
        filled = 0
        for m in moves:
            if not (m.get('effect') or '').strip():
                e = (fill.get(m['name']) or {}).get('effect', '')
                if e:
                    m['effect'] = e
                    filled += 1
        with open('moves.json', 'w', encoding='utf-8') as f:
            json.dump({'count': len(moves), 'data': moves}, f, ensure_ascii=False, separators=(',', ':'))
        nonempty = sum(1 for m in moves if (m.get('effect') or '').strip())
        print('合并完成：本次补全 %d，moves.json effect 非空 %d/%d' % (filled, nonempty, len(moves)))


if __name__ == '__main__':
    main()
