#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Pokémon Showdown 下载缺失的精灵图（像素小图，4 个槽位）到仓库。

源站 URL（play.pokemonshowdown.com/sprites/）：
  ani/{slug}.gif        动图普通
  ani-shiny/{slug}.gif  动图闪光
  gen5/{slug}.png       静态普通（Gen5 风格）
  gen5-shiny/{slug}.png 静态闪光

slug 规则（与 showdown 源站一致）：
  - -mega-x/-mega-y/-mega-z → -megax/-megay/-megaz（去 mega 与 x/y/z 间的连字符）
  - 基础名去连字符（mr-mime→mrmime、ho-oh→hooh、porygon-z→porygonz、type-null→typenull、nidoran-f→nidoranf、tapu-koko→tapukoko）
  每个 en 生成两个候选（原始 + 去连字符），逐个试，命中的那个即源站真实文件名。

断点续跑：文件已存在就跳过。
"""
import json
import os
import re
import time
import urllib.request

UA = 'Mozilla/5.0 pkm/1.0'
BASE = 'https://play.pokemonshowdown.com/sprites/'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SLOTS = [
    ('ani/%s.gif', 'pokemon-sprites/animated/showdown/normal/%s.gif'),
    ('ani-shiny/%s.gif', 'pokemon-sprites/animated/showdown/shiny/%s.gif'),
    ('gen5/%s.png', 'pokemon-sprites/static/showdown/normal/%s.png'),
    ('gen5-shiny/%s.png', 'pokemon-sprites/static/showdown/shiny/%s.png'),
]


def sd_candidates(en):
    s = str(en or '').lower().strip()
    s = s.replace('-mega-x', '-megax').replace('-mega-y', '-megay').replace('-mega-z', '-megaz')
    out = [s]
    noh = s.replace('-', '').replace(':', '')
    if noh != s:
        out.append(noh)
    return out


def main():
    dex = json.load(open(os.path.join(ROOT, 'dex-list.json'), encoding='utf-8'))['data']
    seen = set()
    entries = []
    for e in dex:
        en = e.get('en', '')
        if not en or en in seen:
            continue
        seen.add(en)
        entries.append(en)
    print('待检查 en 数：%d' % len(entries))

    got = skip = miss = 0
    for en in entries:
        cands = sd_candidates(en)
        for slot_url, slot_path in SLOTS:
            done = False
            for c in cands:
                path = os.path.join(ROOT, slot_path % c)
                if os.path.exists(path) and os.path.getsize(path) > 50:
                    skip += 1
                    done = True
                    break
            if done:
                continue
            # 下载：逐个候选试，命中即存
            for c in cands:
                url = BASE + slot_url % c
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': UA})
                    data = urllib.request.urlopen(req, timeout=15).read()
                    if len(data) >= 50:
                        path = os.path.join(ROOT, slot_path % c)
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        open(path, 'wb').write(data)
                        got += 1
                        if got % 20 == 0:
                            print('  已下 %d，跳过 %d，404 %d' % (got, skip, miss))
                        break
                except Exception:
                    continue
            else:
                miss += 1
        time.sleep(0.03)
    print('完成：下载 %d，跳过 %d，缺失/404 %d' % (got, skip, miss))


if __name__ == '__main__':
    main()
