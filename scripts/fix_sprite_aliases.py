#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐精灵图命名别名：把 pokeos 实际文件名复制到 dex-list 的 en 名，
让「图在但名字对不上→404」的问题消除。只复制、不删除，完全可逆。"""
import os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'pokemon-sprites')

# dex en -> pokeos 实际文件名（去掉扩展名）
ALIAS = {
    'pikachu-original': 'pikachu-original-cap',
    'pikachu-hoenn': 'pikachu-hoenn-cap',
    'pikachu-sinnoh': 'pikachu-sinnoh-cap',
    'pikachu-unova': 'pikachu-unova-cap',
    'pikachu-kalos': 'pikachu-kalos-cap',
    'pikachu-alola': 'pikachu-alola-cap',
    'pikachu-partner': 'pikachu-partner-cap',
    'pikachu-world': 'pikachu-world-cap',
    'tauros-paldea-combat': 'tauros-paldea-combat-breed',
    'tauros-paldea-blaze': 'tauros-paldea-blaze-breed',
    'tauros-paldea-aqua': 'tauros-paldea-aqua-breed',
    'squawkabilly-blue': 'squawkabilly-blue-plumage',
    'squawkabilly-yellow': 'squawkabilly-yellow-plumage',
    'squawkabilly-white': 'squawkabilly-white-plumage',
    'ogerpon-wellspring': 'ogerpon-wellspring-mask',
    'ogerpon-hearthflame': 'ogerpon-hearthflame-mask',
    'ogerpon-cornerstone': 'ogerpon-cornerstone-mask',
    'darmanitan-galar': 'darmanitan-galar-standard',
    'meowstic-f': 'meowstic-female',
    'indeedee-f': 'indeedee-female',
    'basculegion-f': 'basculegion-female',
    'oinkologne-f': 'oinkologne-female',
    'necrozma-dusk-mane': 'necrozma-dusk',
    'necrozma-dawn-wings': 'necrozma-dawn',
    'toxtricity-gmax': 'toxtricity-amped-gmax',
    'urshifu-gmax': 'urshifu-single-strike-gmax',
    'dudunsparce-threesegment': 'dudunsparce-three-segment',
}

SLOTS = {
    'static/pokeos/normal': '.png',
    'static/pokeos/shiny': '.png',
    'animated/pokeos/normal': '.gif',
    'animated/pokeos/shiny': '.gif',
}

done, skipped = [], []
for slot, ext in SLOTS.items():
    d = os.path.join(SP, slot)
    for dex_en, src in ALIAS.items():
        s = os.path.join(d, src + ext)
        t = os.path.join(d, dex_en + ext)
        if not os.path.exists(s):
            skipped.append((slot, dex_en, src, '源不存在'))
            continue
        if os.path.exists(t):
            skipped.append((slot, dex_en, src, '目标已存在'))
            continue
        shutil.copy2(s, t)
        done.append((slot, dex_en, src))

print('复制完成 %d 个，跳过 %d 个' % (len(done), len(skipped)))
for slot, dex_en, src in done:
    print('  + %-28s %-30s <- %s' % (slot, dex_en, src))
if skipped:
    print('--- 跳过 ---')
    for slot, dex_en, src, why in skipped:
        print('  - %-28s %-30s (%s)' % (slot, dex_en, why))
