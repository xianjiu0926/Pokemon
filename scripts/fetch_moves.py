#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从神奇宝贝百科（wiki.52poke.com）抓取招式文字数据，输出 moves 结构化 JSON。

来源：wiki.52poke.com 的「Category:招式」分类（分页取全部招式页）及每个招式页（信息框 + 招式附加效果段落）。

用法：
  python3 fetch_moves.py [输出json路径]

旧版从「招式列表」页的链接拿名单，那页现在要登录（API 回 mustbeloggedin），
改用 Category:招式 分类列页面；分类里混着列表页、说明页，没信息框的会被跳过。

新页面的 wikitext 常是繁体（極巨水流、Ｖ熱焰），名字用 zhconv 转简体；
没装 zhconv 也能跑，只是名字会留繁体。

输出 schema（与 moves.json 一致）：
  [ { "id": 1, "name": "拍击", "jp": "はたく", "en": "Pound",
      "type": "一般", "cat": "物理", "power": 40, "acc": 100, "pp": 35,
      "desc": "说明…", "effect": "效果…", "gen": 1, "scope": "除自身以外场上一只可以攻击到的宝可梦" } ]

scope（攻击范围）来自信息框的 |target= 码，TARGET_CN 是 52poke 那套码表。
"""
import re
import json
import sys
import time
import urllib.request
import urllib.parse

try:
    import zhconv
except ImportError:
    zhconv = None

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'


def s2s(v):
    """繁体转简体；没装 zhconv 就原样返回。"""
    return zhconv.convert(v, 'zh-cn') if (zhconv and v) else v

GEN_CN = {1: '第一世代', 2: '第二世代', 3: '第三世代', 4: '第四世代', 5: '第五世代',
          6: '第六世代', 7: '第七世代', 8: '第八世代', 9: '第九世代'}

# 信息框 |target= 码 → 中文范围（照 52poke 招式页「范围」那格的写法）
TARGET_CN = {
    '1': '取决于招式的具体效果',
    '2': '除自身以外场上一只可以攻击到的宝可梦',
    '3': '除自身以外场上任意一只我方宝可梦',
    '4': '我方场地',
    '5': '任意一只我方宝可梦',
    '6': '对手场地',
    '7': '自身',
    '8': '任意一只对手',
    '9': '除自身以外场上全部可以攻击到的宝可梦',
    '11': '全部可以攻击到的对手宝可梦',
    '12': '全部场地',
    '13': '除自身外我方全体宝可梦',
    '14': '随机一只对手',
    '15': '全部我方宝可梦',
    '16': '全部宝可梦',
}


def api(params):
    params['format'] = 'json'
    url = 'https://wiki.52poke.com/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def wikitext(title):
    d = api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content',
             'rvslots': 'main', 'titles': title, 'redirects': '1', 'converttitles': '1'})
    for pid, p in d.get('query', {}).get('pages', {}).items():
        rev = p.get('revisions', [{}])[0]
        return rev.get('slots', {}).get('main', {}).get('*', '') or rev.get('*', '')
    return ''


def list_move_titles():
    """从 Category:招式 分页取全部候选页（列表页和子页面先筛掉）。"""
    titles, cont = [], {}
    while True:
        params = {'action': 'query', 'list': 'categorymembers', 'cmtitle': 'Category:招式',
                  'cmlimit': '500', 'cmnamespace': '0', 'cmtype': 'page'}
        params.update(cont)
        d = api(params)
        titles += [m['title'] for m in d.get('query', {}).get('categorymembers', [])]
        cont = d.get('continue')
        if not cont:
            break
    return sorted({t for t in titles if '/' not in t and '招式列表' not in t})


def info_value(wt, key):
    m = re.search(r'\|\s*%s\s*=\s*([^|\n]*)' % re.escape(key), wt)
    return m.group(1).strip() if m else ''


def num(v):
    try:
        return int(str(v).replace(',', ''))
    except Exception:
        return None


def section(wt, title):
    m = re.search(r'==\s*%s\s*==\s*\n([\s\S]*?)(?=\n==[^=]|$)' % re.escape(title), wt)
    if not m:
        return ''
    out = []
    for ln in m.group(1).split('\n'):
        ln = ln.strip()
        if not ln:
            continue
        ln = re.sub(r'<ref[^>]*>[\s\S]*?</ref>|<ref[^/>]*/>', '', ln)
        ln = re.sub(r'\[\[(?:[^\]]*\|)?([^\]]*)\]\]', r'\1', ln)
        ln = re.sub(r'\{\{[^{}]*\}\}', '', ln).strip()
        if ln:
            out.append(ln)
    return '\n'.join(out)


def parse_move(title):
    wt = wikitext(title)
    box = re.search(r'\{\{[^{}\n]*信息框[\s\S]*?\n\}\}', wt)
    if not box:
        return None
    b = box.group(0)
    gen_num = num(info_value(b, 'gen'))
    return {
        'id': num(info_value(b, 'n')) or 0,
        'name': s2s(info_value(b, 'name')),
        'jp': info_value(b, 'jname'),
        'en': info_value(b, 'enname'),
        'type': info_value(b, 'type'),
        'cat': info_value(b, 'damagecategory'),
        'power': num(info_value(b, 'power')),
        'acc': num(info_value(b, 'accuracy')),
        'pp': num(info_value(b, 'basepp')),
        'gen': GEN_CN.get(gen_num, gen_num),
        'effect': section(wt, '招式附加效果'),
        'scope': TARGET_CN.get(info_value(b, 'target'), ''),
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'moves-new.json'

    print('== 抓取 52poke Category:招式 ==')
    moves = list_move_titles()
    print('  候选页面 %d' % len(moves))

    result = []
    for i, title in enumerate(moves, 1):
        try:
            item = parse_move(title)
            if item and item['name']:
                result.append(item)
        except Exception as e:
            print('  [!] %s 解析失败: %s' % (title, e))
        if i % 100 == 0:
            print('  ...%d/%d' % (i, len(moves)))
        time.sleep(0.15)

    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('  完成，输出 %s（%d 条）' % (out, len(result)))


if __name__ == '__main__':
    main()
