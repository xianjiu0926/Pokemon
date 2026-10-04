#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 pokemon-sprites 缺图清单。
pokeos 目录按 dex-list 的 en 精确匹配；showdown 目录按候选 slug 匹配
（showdown 会去连字符，mega-x->megax 等，见 pkm-hud.js 的 slugCandidates/fixSlug）。
输出 pokemon-sprites-missing.json 到仓库根目录。
"""
import json, re, os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.path.join(ROOT, 'pokemon-sprites')

dex = json.load(open(os.path.join(ROOT, 'dex-list.json')))['data']

SLOTS = {
    'animated-pokeos-normal':   'animated/pokeos/normal',
    'animated-pokeos-shiny':    'animated/pokeos/shiny',
    'animated-showdown-normal': 'animated/showdown/normal',
    'animated-showdown-shiny':  'animated/showdown/shiny',
    'static-pokeos-normal':     'static/pokeos/normal',
    'static-pokeos-shiny':      'static/pokeos/shiny',
    'static-showdown-normal':   'static/showdown/normal',
    'static-showdown-shiny':    'static/showdown/shiny',
}

# 收集每个目录的实际文件名（去扩展名）
files = {}
for key, rel in SLOTS.items():
    d = os.path.join(SP, rel)
    names = set()
    if os.path.isdir(d):
        for f in os.listdir(d):
            base = re.sub(r'\.(png|gif|jpe?g|webp)$', '', f)
            names.add(base)
    files[key] = names

# 形态后缀集合（用于 showdown 候选：基名 + 去连字符的形态）
suffs = set()
for x in dex:
    en = x['en']
    if '-' in en:
        parts = en.split('-')
        for i in range(1, len(parts)):
            suffs.add('-'.join(parts[i:]))
suffs = sorted(suffs, key=len, reverse=True)

def pokeos_cand(en):
    return {en}

def sd_cand(en):
    c = {en}
    m = en.replace('-mega-x', '-megax').replace('-mega-y', '-megay').replace('-mega-z', '-megaz')
    c.add(m)
    c.add(re.sub(r"[-:'\.]", '', en))
    c.add(re.sub(r"[-:'\.]", '', m))
    for s in suffs:
        if s in en and en != s:
            i = en.rfind('-' + s)
            if i >= 0:
                c.add(en[:i] + '-' + s.replace('-', ''))
    return c

def cand(en, key):
    return sd_cand(en) if 'showdown' in key else pokeos_cand(en)

# 逐条目判断
missing = {k: [] for k in SLOTS}
no_img = []
have_count = {k: 0 for k in SLOTS}
for x in dex:
    en = x['en']
    got = []
    for key in SLOTS:
        if cand(en, key) & files[key]:
            have_count[key] += 1
            got.append(key)
        else:
            missing[key].append({'no': x['no'], 'name': x['name'], 'en': en})
    if not got:
        no_img.append({'no': x['no'], 'name': x['name'], 'en': en})

# 反向：目录里存在但 dex-list 匹配不到的文件（多为未收录形态/性别差异，正常）
extra = {}
for key in SLOTS:
    used = set()
    for x in dex:
        used |= cand(x['en'], key)
    extra[key] = sorted(files[key] - used)

out = {
    'generated': date.today().isoformat(),
    'dexTotal': len(dex),
    'slots': SLOTS,
    'summary': {k: {'have': have_count[k], 'missing': len(missing[k])} for k in SLOTS},
    'missing': {k: missing[k] for k in SLOTS if missing[k]},
    'noImageAtAll': no_img,
    'noImageAtAllCount': len(no_img),
    'extraFilesNotInDex': {k: extra[k] for k in SLOTS},
}

dst = os.path.join(ROOT, 'pokemon-sprites-missing.json')
json.dump(out, open(dst, 'w'), ensure_ascii=False, indent=1)
print('written:', dst)
print('\n=== 摘要 (have/missing, 共 %d) ===' % len(dex))
for k in SLOTS:
    print('%-26s have=%4d  missing=%4d' % (k, have_count[k], len(missing[k])))
print('\n完全无图(8槽全缺): %d 只' % len(no_img))
for e in no_img[:40]:
    print('  #%s %s (%s)' % (e['no'], e['name'], e['en']))
print('\n各目录额外文件数(未在dex-list):')
for k in SLOTS:
    print('  %-26s %d' % (k, len(extra[k])))
