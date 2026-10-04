#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 PokeAPI 抓取精灵可学招式，输出 movesets/pokemon-XXXX.json（与现有格式一致）。

来源：https://pokeapi.co/api/v2/pokemon/{id} 的 moves[].version_group_details[]，
     按「主版本 version group」分组，move_learn_method 分 levelup/machine/egg/tutor。

用法：
  python3 fetch_movesets.py [起始编号] [结束编号]
  默认抓 899-1025（Gen8 后期 + Gen9）。

说明：
  - move id 直接沿用 PokeAPI 的 move id（与 moves.json 的 id 一致）。
  - 只保留主版本 version group（跳过 DLC / 旁支 / Gen10 champions 等）。
  - 断点续跑：文件已存在则跳过；删掉该文件可重抓。
"""

import json
import sys
import time
import urllib.request
import urllib.error

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'
BASE = 'https://pokeapi.co/api/v2/'

# version group（PokeAPI 名）→ 文件内缩写，按时间顺序（与现有 movesets 保持一致）
VG_SLUG = [
    ('red-blue', 'redblue'),
    ('yellow', 'yellow'),
    ('gold-silver', 'goldsilver'),
    ('crystal', 'crystal'),
    ('ruby-sapphire', 'rubysapphire'),
    ('emerald', 'emerald'),
    ('firered-leafgreen', 'fireredleafgreen'),
    ('diamond-pearl', 'diamondpearl'),
    ('platinum', 'platinum'),
    ('heartgold-soulsilver', 'hgsl'),
    ('black-white', 'blackwhite'),
    ('colosseum', 'colosseum'),
    ('xd', 'xd'),
    ('black-2-white-2', 'blackwhitetwo'),
    ('x-y', 'xy'),
    ('omega-ruby-alpha-sapphire', 'oras'),
    ('sun-moon', 'sunmoon'),
    ('ultra-sun-ultra-moon', 'usum'),
    ('lets-go-pikachu-lets-go-eevee', 'lgplge'),
    ('sword-shield', 'swordshield'),
    ('brilliant-diamond-shining-pearl', 'bdsp'),
    ('legends-arceus', 'legendsarceus'),
    ('scarlet-violet', 'scarletviolet'),
]
VG_MAP = dict(VG_SLUG)
VG_ORDER = [s for _, s in VG_SLUG]


def http_get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def fetch_moveset(pid):
    d = http_get(BASE + 'pokemon/%d' % pid)
    by_vg = {}
    for m in d.get('moves', []):
        try:
            mid = int(m['move']['url'].rstrip('/').split('/')[-1])
        except Exception:
            continue
        for vd in m.get('version_group_details', []):
            vg = vd['version_group']['name']
            method = vd['move_learn_method']['name']
            lvl = vd.get('level_learned_at', 0) or 0
            slug = VG_MAP.get(vg)
            if not slug:
                continue
            g = by_vg.setdefault(slug, {'gen': slug, 'levelup': [], 'machine': [], 'egg': [], 'tutor': []})
            if method == 'level-up':
                g['levelup'].append([mid, int(lvl)])
            elif method == 'machine':
                g['machine'].append(mid)
            elif method == 'egg':
                g['egg'].append(mid)
            elif method == 'tutor':
                g['tutor'].append(mid)
    allgen = []
    for slug in VG_ORDER:
        g = by_vg.get(slug)
        if not g:
            continue
        g['levelup'].sort(key=lambda x: (x[1], x[0]))
        g['machine'] = sorted(set(g['machine']))
        g['egg'] = sorted(set(g['egg']))
        g['tutor'] = sorted(set(g['tutor']))
        allgen.append(g)
    return {'id': pid, 'allgen': allgen}


def main():
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 899
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 1025
    import os
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'movesets')
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)

    done = skipped = 0
    for pid in range(lo, hi + 1):
        outfile = os.path.join(outdir, 'pokemon-%04d.json' % pid)
        if os.path.exists(outfile):
            skipped += 1
            continue
        try:
            data = fetch_moveset(pid)
        except Exception as e:
            print('FAIL %d: %s' % (pid, e), flush=True)
            time.sleep(2)
            continue
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        done += 1
        print('OK %d (%d moves)' % (pid, len(data['allgen'])), flush=True)
        time.sleep(0.3)

    print('完成：新增 %d，跳过 %d' % (done, skipped), flush=True)


if __name__ == '__main__':
    main()
