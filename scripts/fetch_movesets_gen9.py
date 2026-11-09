#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给已有的 movesets/pokemon-XXXX.json 补第九世代（朱紫）数据。

背景：1-898 那份是更早的流程生成的，最新只到剑盾；899-1025 是 fetch_movesets.py
抓的，已经有 scarletviolet。这个脚本只做一件事：把 PokeAPI 的 scarlet-violet
version group 追加到 1-898 的文件末尾，**不动**任何已有世代。

为什么不用 fetch_movesets.py 重抓：那个脚本会把 bdsp / legendsarceus 一起写进去，
不在朱紫的老宝可梦，HUD 取「最后一个有等级招式的世代」时会显示传说阿尔宙斯那一代，
那不是我们要的。这里只取 scarlet-violet。

用法：
  python3 fetch_movesets_gen9.py [起始编号] [结束编号]   # 默认 1 898
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'
BASE = 'https://pokeapi.co/api/v2/'
VG = 'scarlet-violet'
OUTDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'movesets'))


def http_get(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def sv_entry(pid):
    d = http_get(BASE + 'pokemon/%d' % pid)
    lv, machine, egg, tutor = [], set(), set(), set()
    for m in d.get('moves', []):
        try:
            mid = int(m['move']['url'].rstrip('/').split('/')[-1])
        except Exception:
            continue
        for vd in m.get('version_group_details', []):
            if vd['version_group']['name'] != VG:
                continue
            method = vd['move_learn_method']['name']
            if method == 'level-up':
                lv.append([mid, int(vd.get('level_learned_at', 0) or 0)])
            elif method == 'machine':
                machine.add(mid)
            elif method == 'egg':
                egg.add(mid)
            elif method == 'tutor':
                tutor.add(mid)
    if not (lv or machine or egg or tutor):
        return None
    lv.sort(key=lambda x: (x[1], x[0]))
    return {'gen': 'scarletviolet', 'levelup': lv,
            'machine': sorted(machine), 'egg': sorted(egg), 'tutor': sorted(tutor)}


def process(pid):
    try:
        return _process(pid)
    except Exception as e:
        return pid, 'error:%s' % e


def _process(pid):
    path = os.path.join(OUTDIR, 'pokemon-%04d.json' % pid)
    if not os.path.exists(path):
        return pid, 'missing-file'
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    gens = d.get('allgen', [])
    if any(g.get('gen') == 'scarletviolet' for g in gens):
        return pid, 'already'
    e = sv_entry(pid)
    if e is None:
        return pid, 'no-sv'
    gens.append(e)
    d['allgen'] = gens
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    return pid, 'added'


def main():
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 898
    stats = {}
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for pid, st in ex.map(process, range(lo, hi + 1)):
            stats[st] = stats.get(st, 0) + 1
            done += 1
            if done % 100 == 0:
                print('... %d/%d %s' % (done, hi - lo + 1, stats), flush=True)
    print('完成：', stats)


if __name__ == '__main__':
    main()
