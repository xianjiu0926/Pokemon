#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从神奇宝贝百科（wiki.52poke.com）抓取精灵文字数据，输出 pokemon 结构化 JSON。

来源：wiki.52poke.com 的「宝可梦列表（按全国图鉴编号）/简单版」及各精灵页
     （宝可梦信息框 + 种族值模板 + 概述段落）。

用法：
  python3 fetch_pokemon.py [输出json路径] [起始序号] [结束序号]

输出 schema（与 pokemon/gen-XX.json 一致）：
  [ { "no": 1, "name": "妙蛙种子", "jp": "フシギダネ", "en": "bulbasaur",
      "types": ["草","毒"], "abilities": ["茂盛","叶绿素"],
      "stats": {"hp":45,"atk":49,"def":49,"spa":65,"spd":65,"spe":45},
      "height": 0.7, "weight": 6.9, "species": "种子",
      "eggGroups": ["怪兽","植物"], "catchRate": 45, "color": "绿",
      "gen": "第一世代", "desc": "概述…" } ]

注：desc 取自页面「概述」段落（非逐代图鉴描述），如需逐代图鉴文字可再扩展。
"""
import re
import json
import sys
import time
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'

GEN_BY_NDEX = [(1, 151, '第一世代'), (152, 251, '第二世代'), (252, 386, '第三世代'),
               (387, 493, '第四世代'), (494, 649, '第五世代'), (650, 721, '第六世代'),
               (722, 809, '第七世代'), (810, 905, '第八世代'), (906, 1025, '第九世代')]


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


def extract_template(wt, name):
    """括号配平提取 {{name ... }}。"""
    start = wt.find('{{' + name)
    if start < 0:
        return ''
    i = start + 2
    depth = 0
    while i < len(wt):
        if wt[i:i+2] == '{{':
            depth += 1
            i += 2
        elif wt[i:i+2] == '}}':
            if depth == 0:
                return wt[start:i+2]
            depth -= 1
            i += 2
        else:
            i += 1
    return ''


def info_value(tpl, key):
    m = re.search(r'\|\s*%s\s*=\s*([^|\n]*)' % re.escape(key), tpl)
    return m.group(1).strip() if m else ''


def num(v):
    try:
        return float(str(v).replace(',', ''))
    except Exception:
        return None


def int_or_none(v):
    n = num(v)
    return int(n) if n is not None else None


def gen_of(ndex):
    for lo, hi, g in GEN_BY_NDEX:
        if lo <= ndex <= hi:
            return g
    return '未知'


def parse_pokemon(title):
    wt = wikitext(title)
    box = extract_template(wt, '寶可夢信息框') or extract_template(wt, '宝可梦信息框')
    if not box:
        return None
    ndex = int_or_none(info_value(box, 'ndex')) or 0

    types = [info_value(box, 'type1')]
    if info_value(box, 'type2'):
        types.append(info_value(box, 'type2'))

    abis = [info_value(box, 'ability1'), info_value(box, 'ability2'), info_value(box, 'abilityd')]
    abis = [a for a in abis if a]

    egg = [info_value(box, 'egggroup1'), info_value(box, 'egggroup2')]
    egg = [e for e in egg if e]

    # 种族值模板
    st = extract_template(wt, '种族值')
    stats = {
        'hp': int_or_none(info_value(st, 'HP')),
        'atk': int_or_none(info_value(st, '攻击')),
        'def': int_or_none(info_value(st, '防御')),
        'spa': int_or_none(info_value(st, '特攻')),
        'spd': int_or_none(info_value(st, '特防')),
        'spe': int_or_none(info_value(st, '速度')),
    }

    # 概述段落（信息框后第一段文字）
    desc = ''
    after_box = wt[wt.find(box) + len(box):]
    m = re.search(r'\n\n([^\n={][\s\S]*?)\n\n==', after_box)
    if m:
        desc = re.sub(r'<ref[^>]*>[\s\S]*?</ref>|<ref[^/>]*/>', '', m.group(1))
        desc = re.sub(r'\[\[(?:[^\]]*\|)?([^\]]*)\]\]', r'\1', desc)
        desc = re.sub(r'\{\{[^{}]*\}\}', '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()

    return {
        'no': ndex,
        'name': info_value(box, 'name'),
        'jp': info_value(box, 'jname'),
        'en': info_value(box, 'enname').lower(),
        'types': types,
        'abilities': abis,
        'stats': stats,
        'height': num(info_value(box, 'height')),
        'weight': num(info_value(box, 'weight')),
        'species': info_value(box, 'species'),
        'eggGroups': egg,
        'catchRate': int_or_none(info_value(box, 'catchrate')),
        'color': info_value(box, 'color'),
        'gen': gen_of(ndex),
        'desc': desc,
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'pokemon-new.json'
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 1025

    print('== 抓取 52poke 宝可梦列表 ==')
    d = api({'action': 'parse', 'page': '宝可梦列表（按全国图鉴编号）/简单版', 'prop': 'wikitext'})
    wt = d.get('parse', {}).get('wikitext', {}).get('*', '')
    entries = [(int(a), b.strip()) for a, b in re.findall(r'\{\{\s*Rdexe\s*\|\s*(\d+)\s*\|\s*([^|]+)', wt)]
    print('  列表条目 %d（按序号 %d-%d 抓取）' % (len(entries), start, end))

    result = []
    for i, (ndex, name) in enumerate(entries, 1):
        if ndex < start or ndex > end:
            continue
        try:
            item = parse_pokemon(name)
            if item:
                item['no'] = ndex
                result.append(item)
        except Exception as e:
            print('  [!] %s 解析失败: %s' % (name, e))
        if i % 100 == 0:
            print('  ...已处理 %d' % i)
        time.sleep(0.15)

    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('  完成，输出 %s（%d 条）' % (out, len(result)))


if __name__ == '__main__':
    main()
