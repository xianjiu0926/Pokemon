#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补齐 items.json 缺失的 effect 字段（None / 空串），共 401 条。

来源：desc 里的招式名（前缀「招式名：」或纯描述反查 moves.json）+ 少量人工映射。

规则：
- 技能机/招式记录 -> effect = "让宝可梦学会{招式}。"
- 掉落物          -> effect = "制作招式学习器的材料。"
- 野餐道具        -> effect = "野餐装饰用品。"
- 食材            -> effect = "料理食材。"
- 进化道具(概念)  -> effect = "游戏机制数值。"
- 工艺制作        -> effect = "战斗辅助道具。"
- 一般道具(美丽之羽) -> effect = "无效果。"
"""
import json
import re
import sys

ROOT = '/workspace/Pokemon-repo'
items_path = ROOT + '/items.json'
moves_path = ROOT + '/moves.json'

# 人工确认的映射（从 52poke 招式学习器页核对，Gen5~7 世代）
TM_MAP = {
    'tm03': '精神冲击', 'tm07': '冰雹', 'tm10': '觉醒力量', 'tm17': '守住',
    'tm21': '迁怒', 'tm36': '污泥炸弹', 'tm37': '沙暴', 'tm38': '大字爆炎',
    'tm43': '蓄能焰袭', 'tm50': '过热', 'tm58': '自由落体', 'tm72': '伏特替换',
    'tm89': '急速折返', 'tm99': '魔法闪耀',
}
TR_MAP = {
    'tr18': '汲取', 'tr21': '绝处逢生', 'tr81': '移花接木', 'tr95': '深渊突刺',
}

CAT_FIXED = {
    '掉落物': '制作招式学习器的材料。',
    '野餐道具': '野餐装饰用品。',
    '食材': '料理食材。',
    '进化道具': '游戏机制数值。',
    '工艺制作': '战斗辅助道具。',
}


def norm(s):
    return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', str(s or ''))


def main():
    items = json.load(open(items_path, encoding='utf-8'))
    data = items['data']
    moves = json.load(open(moves_path, encoding='utf-8'))
    if isinstance(moves, dict):
        moves = moves.get('data', moves)
    mnames = {m.get('name') for m in moves}
    # desc -> [招式名]
    from collections import defaultdict
    mdesc = defaultdict(list)
    for m in moves:
        mdesc[norm(m.get('desc', ''))].append(m.get('name'))

    filled = 0
    leftover = []

    for it in data:
        e = it.get('effect')
        if e is not None and str(e).strip():
            continue  # 已有值，跳过
        cat = it.get('cat', '')
        en = it.get('en', '')
        desc = str(it.get('desc', ''))

        if cat in ('技能机', '招式记录'):
            move = None
            # 1) 人工映射
            if en in TM_MAP:
                move = TM_MAP[en]
            elif en in TR_MAP:
                move = TR_MAP[en]
            # 2) desc 前缀「招式名：」
            if move is None:
                m = re.match(r'^([^：:]+)[：:]', desc)
                if m and m.group(1).strip() in mnames:
                    move = m.group(1).strip()
            # 3) desc 反查 moves.json
            if move is None:
                cand = mdesc.get(norm(desc), [])
                if len(cand) == 1:
                    move = cand[0]
            if move:
                it['effect'] = '让宝可梦学会%s。' % move
                filled += 1
            else:
                leftover.append((en, desc[:30]))
        elif cat in CAT_FIXED:
            it['effect'] = CAT_FIXED[cat]
            filled += 1
        elif cat == '一般道具':
            it['effect'] = '无效果。'
            filled += 1
        else:
            leftover.append((en, 'cat=' + cat))

    # 写回
    json.dump(items, open(items_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    nonempty = sum(1 for x in data if x.get('effect') and str(x['effect']).strip())
    print('补全 %d 条，effect 非空 %d/%d' % (filled, nonempty, len(data)))
    if leftover:
        print('--- 仍未补的 %d 条 ---' % len(leftover))
        for en, why in leftover:
            print('  %-12s %s' % (en, why))


if __name__ == '__main__':
    main()
