#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 PokeOS 下载缺失的宝可梦精灵图（HOME 动图 + 渲染静态图，普通/闪光）。

PokeOS URL 规则（2026-09 确认）：
  普通动图   home/animated/{编号}{形态}.gif
  闪光动图   home/animated/shiny/{编号}{形态}.gif
  普通静态   home/render/{编号}{形态}.png
  闪光静态   home/render/shiny/{编号}{形态}.png
形态后缀：-mega / -mega-x / -mega-y / -mega-z / -gmax / -regional-a|g|h|p / 其他英文形态（-attack、-heat、-origin、-ash…）

用法：
  python3 fetch_pokemon_sprites.py [--mega-only]

输出到 pokemon-sprites/ 对应目录，文件命名沿用仓库 slug（小写、连字符）。
"""
import json
import glob
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

UA = 'Mozilla/5.0 pkm-sprite-fetch/1.0'
BASE = 'https://s3.pokeos.com/pokeos-uploads/assets/pokemon/home/'
DELAY = 0.12
REG = {'alola': 'regional-a', 'galar': 'regional-g', 'hisui': 'regional-h', 'paldea': 'regional-p'}
# dex en 形态后缀 → pokeos 源站后缀（源站简化命名）
POKEOS_SUFFIX_FIX = {'primal': 'mega', 'dusk-mane': 'dusk', 'dawn-wings': 'dawn', 'threesegment': 'three-segment', 'original-mega': 'mega-original', 'droopy-mega': 'mega-droopy', 'stretchy-mega': 'mega-stretchy'}
POKEOS_CAP = ('original', 'hoenn', 'sinnoh', 'unova', 'kalos', 'alola', 'partner', 'world')  # 皮卡丘帽子
POKEOS_PALDEA = {'paldea-combat': 'regional-p-combat', 'paldea-blaze': 'regional-p-blaze', 'paldea-aqua': 'regional-p-aqua'}


def slugify(en):
    s = str(en).lower().replace("'", '')
    return re.sub(r'[^a-z0-9-]+', '-', s).strip('-')


def dl(url, path, tries=3):
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            data = urllib.request.urlopen(req, timeout=25).read()
            if len(data) < 50:
                return False
            open(path, 'wb').write(data)
            return True
        except Exception:
            time.sleep(1.5)
    return False


def load_entries():
    entries = []
    for f in sorted(glob.glob('pokemon/gen-*.json')):
        d = json.load(open(f, encoding='utf-8'))
        for p in d.get('data', []):
            entries.append(p)
    return entries


def build_mapping(entries):
    by_no = defaultdict(list)
    for p in entries:
        by_no[p['no']].append(p)
    base = {no: min(ps, key=lambda x: len(x['en'])) for no, ps in by_no.items()}
    base_slug = {no: slugify(p['en']) for no, p in base.items()}
    return base_slug


def pokeos_id(p, base_slug):
    no = p['no']
    en = slugify(p['en'])
    bs = base_slug.get(no, '')
    if en == bs:
        return str(no), en  # 基础形态
    if not en.startswith(bs):
        return None, en
    suf = en[len(bs):].lstrip('-')
    if not suf:
        return None, en
    if bs == 'pikachu' and suf in POKEOS_CAP:
        suf = suf + '-cap'              # 皮卡丘帽子
    elif suf in POKEOS_PALDEA:
        suf = POKEOS_PALDEA[suf]        # 肯泰罗帕底亚品种
    elif suf in POKEOS_SUFFIX_FIX:
        suf = POKEOS_SUFFIX_FIX[suf]    # 原始回归/奈克洛兹玛/土龙节节
    elif suf in REG:
        suf = REG[suf]                  # 地区形态
    elif suf in ('battle-bond', 'ash'):
        suf = 'ash'
    elif suf == '10%':
        suf = '10'
    return str(no) + '-' + suf, en


def main():
    only_mega = '--mega-only' in sys.argv[1:]
    entries = load_entries()
    base_slug = build_mapping(entries)

    todo = []
    for p in entries:
        pid, slug = pokeos_id(p, base_slug)
        if pid is None:
            continue
        if only_mega and '-mega' not in pid:
            continue
        todo.append((pid, slug, p['name']))

    print('待下载：%d 个（%s）' % (len(todo), '仅Mega' if only_mega else '全部缺失'))

    got = 0
    for pid, slug, cn in sorted(todo, key=lambda x: x[0]):
        pairs = [
            (BASE + 'animated/%s.gif' % pid, 'pokemon-sprites/animated/pokeos/normal/%s.gif' % slug),
            (BASE + 'animated/shiny/%s.gif' % pid, 'pokemon-sprites/animated/pokeos/shiny/%s.gif' % slug),
            (BASE + 'render/%s.png' % pid, 'pokemon-sprites/static/pokeos/normal/%s.png' % slug),
            (BASE + 'render/shiny/%s.png' % pid, 'pokemon-sprites/static/pokeos/shiny/%s.png' % slug),
        ]
        os.makedirs(os.path.dirname(pairs[0][1]), exist_ok=True)
        ok = 0
        for url, path in pairs:
            if os.path.exists(path):
                ok += 1
                continue
            if dl(url, path):
                ok += 1
            time.sleep(DELAY)
        if ok:
            got += 1
            print('  [OK %d/4] %s %s' % (ok, pid, cn))
        else:
            print('  [MISS] %s %s' % (pid, cn))
        time.sleep(DELAY)
    print('完成：%d/%d' % (got, len(todo)))


if __name__ == '__main__':
    main()
