#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 pokemon-sprites-missing.json 渲染成人看的 MISSING-SPRITES.md。
先跑 check_sprites.py 生成 json，再跑本脚本。

用法：python3 scripts/make_missing_report.py
"""
import json
import os
import re
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'pokemon-sprites-missing.json')
OUT = os.path.join(ROOT, 'MISSING-SPRITES.md')

ABBR = {
    'animated-pokeos-normal': 'APN',
    'animated-pokeos-shiny': 'APS',
    'animated-showdown-normal': 'ADN',
    'animated-showdown-shiny': 'ADS',
    'static-pokeos-normal': 'SPN',
    'static-pokeos-shiny': 'SPS',
    'static-showdown-normal': 'SDN',
    'static-showdown-shiny': 'SDS',
}
ORDER = ['APN', 'APS', 'ADN', 'ADS', 'SPN', 'SPS', 'SDN', 'SDS']


def group(name, en):
    en = en.lower()
    if re.search(r'-gmax$', en):
        return '超极巨化（动图源站没有）'
    if re.match(r'pikachu-(original|hoenn|sinnoh|unova|kalos|alola|partner|world)$', en):
        return '皮卡丘帽子（闪光动图源站没有）'
    if re.search(r'-mega(-[xyz])?$', en):
        return 'DLC 新 Mega（源站未补）'
    if '-stellar' in en or '-tera' in en:
        return '太乐巴戈斯太晶/星晶'
    if en in ('browt', 'pombon', 'gecqua') or re.match(r'^(browt|pombon|gecqua)', en):
        return 'Gen10（新作，源站只有静态普通图）'
    if re.search(r'pumpkaboo|gourgeist', en):
        return '南瓜精/南瓜怪人尺寸'
    return '其他'


def main():
    d = json.load(open(SRC, encoding='utf-8'))
    missing = d['missing']
    per = defaultdict(lambda: defaultdict(set))  # en -> name/no/slots
    info = {}
    for slot, items in missing.items():
        ab = ABBR.get(slot, slot)
        for it in items:
            en = it['en']
            per[en]['name'] = it['name']
            per[en]['no'] = it['no']
            per[en]['slots'].add(ab)
            info[en] = it
    buckets = defaultdict(list)
    for en in per:
        buckets[group(per[en]['name'], en)].append(en)

    total = sum(len(v) for v in missing.values())
    lines = [
        '# 宝可梦缺图清单（待补）',
        '',
        '> 生成: %s | 由 `scripts/check_sprites.py` + `scripts/make_missing_report.py` 生成，别手改' % date.today().isoformat(),
        '> 槽位缩写：APN/APS=动图普通/闪光（pokeos）、ADN/ADS=动图普通/闪光（showdown）、',
        '> SPN/SPS=静态普通/闪光（pokeos）、SDN/SDS=静态普通/闪光（showdown）',
        '',
        '## 总览',
        '',
        '| 槽位 | 缺 | 有 |',
        '|---|---|---|',
    ]
    for slot in d['slots']:
        s = d['summary'][slot]
        lines.append('| %s `%s` | %d | %d |' % (ABBR.get(slot, slot), d['slots'][slot], s['missing'], s['have']))
    lines.append('')
    lines.append('合计缺 **%d** 个槽位（共 %d 只，dex 条目 %d）。' % (total, len(per), d['dexTotal']))
    if d.get('noImageAtAllCount'):
        lines.append('')
        lines.append('⚠️ 八个槽位全缺：%d 只' % d['noImageAtAllCount'])
    lines.append('')

    for g in sorted(buckets, key=lambda k: (k == '其他', k)):
        ens = sorted(buckets[g], key=lambda e: (per[e]['no'], e))
        lines.append('## %s（%d 只）' % (g, len(ens)))
        lines.append('')
        for en in ens:
            v = per[en]
            slots = ','.join([s for s in ORDER if s in v['slots']])
            lines.append('- `#%s` %s（`%s`）缺：%s' % (v['no'], v['name'], en, slots))
        lines.append('')

    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
    print('written: %s（%d 只 / %d 槽位）' % (OUT, len(per), total))


if __name__ == '__main__':
    main()
