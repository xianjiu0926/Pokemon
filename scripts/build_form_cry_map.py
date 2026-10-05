#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 form-cry-map.json：gen 形态英文名(小写) -> 叫声编号(form id)。
叫声文件 cries/{formid}.ogg 按 PokeAPI 形态编号命名（与 form-ids.json 的 key 一致）。

匹配策略：
  1. gen 形态 en 转小写，与 form-ids.json 的 en(小写) 精确匹配；
  2. 剩余用 MANUAL_MAP（52poke 与 PokeAPI 命名差异的显式别名表）；
  3. 对不上的（alcremie 装饰、无独立叫声形态等）不写入，HUD 播放时退回基础编号。

输出：仓库根目录 form-cry-map.json
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_FILES = ['gen-01', 'gen-02', 'gen-03', 'gen-04', 'gen-05',
             'gen-06', 'gen-07', 'gen-08', 'gen-09', 'gen-10']

# 52poke 英文名(小写) -> PokeAPI 形态编号（显式别名，覆盖命名差异）
MANUAL_MAP = {
    # 帽子皮卡丘（52poke 无 -cap 后缀，PokeAPI 带 -cap）
    'pikachu-original': 10094,
    'pikachu-hoenn': 10095,
    'pikachu-sinnoh': 10096,
    'pikachu-unova': 10097,
    'pikachu-kalos': 10098,
    'pikachu-alola': 10099,
    'pikachu-partner': 10148,
    'pikachu-world': 10160,
    # 标点差异
    "farfetch'd-galar": 10166,
    'mr.mime-galar': 10168,
    'zygarde-10%': 10181,
    "oricorio-pa'u": 10124,
    # 雌性形态（52poke 用 -f，PokeAPI 用 -female）
    'meowstic-f': 10025,
    'indeedee-f': 10186,
    'basculegion-f': 10248,
    'oinkologne-f': 10254,
    # 地区/其他命名差异
    'tauros-paldea-blaze': 10251,
    'tauros-paldea-aqua': 10252,
    'darmanitan-galar': 10177,
    'meowstic-mega': 10314,
    'necrozma-dusk-mane': 10155,
    'necrozma-dawn-wings': 10156,
    'toxtricity-gmax': 10219,
    'urshifu-gmax': 10226,
    'squawkabilly-blue': 10260,
    'squawkabilly-yellow': 10261,
    'squawkabilly-white': 10262,
    'dudunsparce-threesegment': 10255,
    'ogerpon-wellspring': 10273,
    'ogerpon-hearthflame': 10274,
    'ogerpon-cornerstone': 10275,
}

def load_form_ids():
    fi = json.load(open(os.path.join(REPO, 'form-ids.json')))
    # en(小写) -> form id
    return {v['en'].lower(): int(k) for k, v in fi.items()}

def gen_form_entries():
    """遍历 gen-*.json，收集形态 entry（有 suffix 的）的英文名(小写)。"""
    entries = {}
    for g in GEN_FILES:
        d = json.load(open(os.path.join(REPO, 'pokemon', g + '.json')))
        for p in d['data']:
            if p.get('suffix'):
                en = (p.get('en') or '').lower()
                if en:
                    entries[en] = p.get('no')
    return entries

def main():
    form_ids = load_form_ids()
    gen_forms = gen_form_entries()

    result = {}
    matched_exact = matched_manual = 0
    missing = []

    for en in gen_forms:
        fid = form_ids.get(en)
        if fid:
            result[en] = fid
            matched_exact += 1
            continue
        fid = MANUAL_MAP.get(en)
        if fid:
            result[en] = fid
            matched_manual += 1
            continue
        missing.append(en)

    out = os.path.join(REPO, 'form-cry-map.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    print('gen 形态 entry 总数: %d' % len(gen_forms))
    print('精确匹配: %d' % matched_exact)
    print('手动别名匹配: %d' % matched_manual)
    print('未映射(退回基础叫声): %d' % len(missing))
    for m in missing:
        print('  - %s' % m)
    print('已写入 %s（%d 条）' % (out, len(result)))

if __name__ == '__main__':
    main()
