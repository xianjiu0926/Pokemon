#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""52poke 页面变更监控 / 数据同步检查

监控「道具列表」「特性列表」「招式列表」等页面，做到两件事：
  1. 有没有更新：对比页面最新 revid 与上次记录的基线
  2. 更新了什么：拉最新 wikitext，解析出条目名，跟上次快照比 -> 新增/删除；
     再跟本地 JSON（items.json / abilities.json / moves.json）比 -> 「wiki 有、本地缺」

用法：
  python3 watch_wiki.py            # 只检查并打印报告（不写基线）
  python3 watch_wiki.py --save     # 检查后把当前状态存为基线
  python3 watch_wiki.py --init     # 首次建立基线（等价于 --save，但要求没有基线）
  python3 watch_wiki.py --full     # 忽略基线，只做「wiki vs 本地 JSON」全量核对

说明：
  - 基线存在脚本同目录 wiki-watch-state.json（含每个页面的 revid + 条目名快照），
    建议跟仓库一起提交，换电脑也能续。
  - 只做只读请求（action=query），不登录、不改 wiki。
  - 52poke 的 API 对多页面查询 offset 有限制：批量查 revid 不能带 rvlimit。
"""

import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

API = 'https://wiki.52poke.com/api.php'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE_FILE = os.path.join(HERE, 'wiki-watch-state.json')
REPORT_FILE = os.path.join(HERE, 'wiki-watch-report.md')

# 繁 -> 简映射（比对用：wiki 部分条目写的是繁体名，如 薄霧球 / 精神衝擊）
T2S = {}
_t2s_path = os.path.join(ROOT, 't2s-map.json')
if os.path.exists(_t2s_path):
    with open(_t2s_path, encoding='utf-8') as _f:
        T2S = json.load(_f).get('data', {})

# 要监控的页面：标题 -> 解析方式 / 本地对应文件
PAGES = [
    {'title': '道具列表', 'kind': 'items', 'local': 'items.json'},
    {'title': '特性列表', 'kind': 'abilities', 'local': 'abilities.json'},
    {'title': '招式列表', 'kind': 'moves', 'local': 'moves.json'},
    {'title': '宝可梦列表（按全国图鉴编号）', 'kind': 'dex', 'local': 'dex-list.json'},
]


# ---------------------------------------------------------------- HTTP
def api_get(params, tries=3):
    params = dict(params)
    params.setdefault('format', 'json')
    params.setdefault('action', 'query')
    url = API + '?' + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode('utf-8'))
            if 'error' in data:
                raise RuntimeError('API error: %s' % data['error'].get('info'))
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError('请求失败：%s (%s)' % (url, last))


def fetch_revids(titles):
    """一次请求拿到多个页面的最新 revid（注意：多页面时不能带 rvlimit）。"""
    out = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        data = api_get({
            'prop': 'revisions',
            'titles': '|'.join(chunk),
            'rvprop': 'ids|timestamp|size',
        })
        for p in data.get('query', {}).get('pages', {}).values():
            if p.get('missing') is not None:
                out[p['title']] = None
                continue
            revs = p.get('revisions') or [{}]
            r = revs[0]
            out[p['title']] = {
                'revid': r.get('revid'),
                'timestamp': r.get('timestamp'),
                'size': r.get('size'),
            }
        time.sleep(0.4)
    return out


def fetch_wikitext(title):
    data = api_get({
        'prop': 'revisions',
        'titles': title,
        'rvprop': 'content',
        'rvslots': 'main',
        'rvlimit': 1,
    })
    page = list(data.get('query', {}).get('pages', {}).values())[0]
    if page.get('missing') is not None:
        return None
    return page['revisions'][0]['slots']['main']['*']


# ---------------------------------------------------------------- 解析
def _clean_tt(s):
    """展开 {{tt*|名字|注释}} / {{tt|名字|注释}} -> 名字（可能嵌套，循环展开）"""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\{\{tt\*?\|([^{}|]*)\|[^{}]*\}\}', r'\1', s)
    return s


def _norm(s):
    """比较用的归一化：繁转简、全角转半角、去空白/标点/连字符、英文小写"""
    s = ''.join(T2S.get(ch, ch) for ch in str(s or ''))
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', s.lower())


def parse_items(wt):
    """道具列表：| {{I|道具名}}"""
    return [{'name': m.group(1).strip()}
            for m in re.finditer(r'^\|\s*\{\{I\|([^}|]+)', wt, re.M)]


def parse_abilities(wt):
    """特性列表：{{特性列表|编号|中文|日文|英文|说明|常见|隐藏}}
       个别行把名字和 tt 备注挤在编号位：{{特性列表|076{{tt|*|...}}|杂音|そうおん|Cacophony|...}}"""
    out = []
    for ln in wt.split('\n'):
        s = _clean_tt(ln.strip())
        m = re.match(r'\{\{特性列表\|(.*?)\}\}$', s)
        if not m:
            continue
        p = m.group(1).split('|')
        head = p[0]
        no = re.match(r'(\d+)', head)
        no = no.group(1) if no else ''
        rest = re.sub(r'^\d+', '', head).replace('*', '').strip()
        if rest:  # 名字挤在编号位
            name, jp, en = rest, p[1] if len(p) > 1 else '', p[2] if len(p) > 2 else ''
            desc = p[3] if len(p) > 3 else ''
        else:
            name = p[1].strip() if len(p) > 1 else ''
            jp = p[2] if len(p) > 2 else ''
            en = p[3] if len(p) > 3 else ''
            desc = p[4] if len(p) > 4 else ''
        desc = re.sub(r'-\{zh-hans:([^;]*);.*?-\}', r'\1', desc).strip()
        out.append({'no': no, 'name': name, 'jp': jp, 'en': en.strip(), 'desc': desc})
    return out


def parse_moves(wt):
    """招式列表：{{Movelist/gen/ex|编号|中文|日文|英文|属性|分类|威力|命中|PP}}"""
    out = []
    for m in re.finditer(r'\{\{Movelist/gen/ex\|([^}]*?)\}\}', wt):
        p = m.group(1).split('|')
        if len(p) < 2:
            continue
        out.append({
            'no': p[0].strip(),
            'name': p[1].strip(),
            'jp': p[2].strip() if len(p) > 2 else '',
            'en': p[3].strip() if len(p) > 3 else '',
            'type': p[4].strip() if len(p) > 4 else '',
            'cat': p[5].strip() if len(p) > 5 else '',
            'pow': p[6].strip() if len(p) > 6 else '',
            'acc': p[7].strip() if len(p) > 7 else '',
            'pp': p[8].strip() if len(p) > 8 else '',
        })
    return out


def parse_dex(wt):
    """宝可梦列表（按全国图鉴编号）：{{Rdexn|编号|中文|日文|英文|属性1|属性2|filter=...}}"""
    out = []
    for m in re.finditer(r'\{\{Rdexn\|([^{}]*?)\}\}', wt):
        p = [x.strip() for x in m.group(1).split('|')]
        p = [x for x in p if not re.match(r'^[a-z_]+=', x)]  # 丢掉 filter= 之类具名参数
        if len(p) < 2:
            continue
        out.append({
            'no': p[0],
            'name': p[1],
            'jp': p[2] if len(p) > 2 else '',
            'en': p[3] if len(p) > 3 else '',
            'type1': p[4] if len(p) > 4 else '',
            'type2': p[5] if len(p) > 5 else '',
        })
    return out


PARSERS = {'items': parse_items, 'abilities': parse_abilities, 'moves': parse_moves,
           'dex': parse_dex}


# ---------------------------------------------------------------- 道具图标
SPRITE_DIR = os.path.join(ROOT, 'item-sprites')
# 这些类别不单独存图：HUD 里技能机按招式属性用 tm-{属性}.png
SKIP_ITEM_CATS = {'技能机', '招式记录', '秘传学习器'}
# HUD 的 ITEM_IMG 已硬编码映射的（不走 item-sprites）
ITEM_IMG_MAPPED = {'Mega手镯', 'Z强力手环', 'Z手环', '阿尔宙斯手机', '手机',
                   '太晶珠', '钥石', '极巨腕带', '宝可梦图鉴'}
# 源站就没有图标的道具（52poke 道具列表里显示「Bag 无」/共用 GSC 果实树图，Serebii ItemDex 也 404）
# 这类条目不再计入缺失，否则报告里天天提示又无法补
NO_ICON_ITEMS = {
    # 第二世代遗留道具（官方无图标；10 种果实已用 52poke 共用的 GSC 果实树图填充，其余无图可用）
    '水玉色之带', '粉红色丝带', '破坏基因', '破坏基因(破坏因子)', '碎瓦片', '木箱', '桐木箱',
    '宝可梦的蛋兑换券',
    # 不是道具的系统概念/旧版条目
    '亲密度', '经验值', '太阳碎片', '月亮碎片',
    # 剑盾 DLC 料理（Serebii ItemDex 无 sprites/maxsoup.png，52poke 道具列表也无图标，实测 404）
    '极巨汤',
}


def _item_slug(s):
    """与 HUD 的 serebiiItemSlug 完全一致：小写、只保留英文字母和数字（点号/冒号/连字符都去掉）"""
    return re.sub(r'[^a-z0-9]+', '', str(s or '').lower())


def check_item_sprites():
    """items.json 有条目、item-sprites 没有对应 png 的道具（排除设计上不需要图的）"""
    if not os.path.isdir(SPRITE_DIR):
        return []
    have = set(os.listdir(SPRITE_DIR))
    out = []
    for it in load_local(os.path.join(ROOT, 'items.json')):
        if (it.get('cat') in SKIP_ITEM_CATS or it.get('name') in ITEM_IMG_MAPPED
                or it.get('name') in NO_ICON_ITEMS):
            continue
        cands = []
        if it.get('en'):
            cands.append(_item_slug(it['en']) + '.png')
        cands.append(_item_slug(it['name']) + '.png')
        if not any(c in have for c in cands):
            out.append(it)
    return out


# ---------------------------------------------------------------- 本地数据
def load_local(path):
    """读本地 JSON，返回 [{name,en}]（items/abilities/moves 都是 {count,data:[{name...}]}）"""
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    data = d.get('data') if isinstance(d, dict) else d
    return [{'name': x.get('name', ''), 'en': x.get('en', ''), 'cat': x.get('cat', '')}
            for x in (data or [])]


# ---------------------------------------------------------------- 主流程
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
        f.write('\n')


def main():
    args = set(sys.argv[1:])
    do_save = '--save' in args or '--init' in args
    full = '--full' in args
    state = load_state()

    if '--init' in args and state:
        print('已存在基线（%s），--init 中止。要重建基线请先删掉该文件。' % STATE_FILE)
        return 1

    titles = [p['title'] for p in PAGES]
    print('查询 %d 个页面的最新版本…' % len(titles))
    revs = fetch_revids(titles)

    lines = []
    lines.append('## 52poke 变更检查 %s' % time.strftime('%Y-%m-%d %H:%M'))
    lines.append('')
    lines.append('| 页面 | 状态 | revid | 最后编辑 | 上次条目数 | 本地对应 |')
    lines.append('|---|---|---|---|---|---|')

    changed = []
    for page in PAGES:
        title = page['title']
        now = revs.get(title)
        old = state.get(title) or {}
        local_items = load_local(os.path.join(ROOT, page['local']))

        if now is None:
            lines.append('| %s | ⚠ 页面不存在 | - | - | - | %s |' % (title, page['local']))
            continue

        same = (not full) and old.get('revid') == now['revid']
        status = '无变化' if same else ('★ 有更新' if old else '新基线')
        if full:
            status = '全量核对'
        lines.append('| %s | %s | %s | %s | %s | %s |' %
                     (title, status, now['revid'], (now.get('timestamp') or '')[:10],
                      old.get('count', '-'), page['local']))

        if same:
            continue
        changed.append((page, now, old, local_items))

    detail = []
    new_state = dict(state)
    for page, now, old, local_items in changed:
        title = page['title']
        print('拉取 %s 的最新版本…' % title)
        wt = fetch_wikitext(title)
        if wt is None:
            continue
        items = PARSERS[page['kind']](wt)
        names = [x['name'] for x in items if x['name']]

        prev = set(old.get('names') or [])
        cur = set(names)
        added = sorted(cur - prev) if prev else []
        removed = sorted(prev - cur) if prev else []

        local_set = {_norm(x['name']) for x in local_items}
        local_ens = {_norm(x['en']) for x in local_items if x.get('en')}
        # 精灵的基础形态在本地可能带后缀，如 wiki「野蛮鲈鱼」对应本地「野蛮鲈鱼(红条纹)」
        local_base = {_norm(re.split(r'[（(]', x['name'])[0]) for x in local_items}

        def known(it):
            if _norm(it['name']) in local_set:
                return True
            if it.get('en') and _norm(it['en']) in local_ens:
                return True
            if page['kind'] == 'dex' and _norm(it['name']) in local_base:
                return True
            return False

        missing = [x for x in items if x['name'] and not known(x)]

        detail.append('')
        detail.append('### %s（%s 条 → %s 条）' % (title, len(prev) or '-', len(cur)))
        if not prev:
            detail.append('- 首次记录快照，暂无法对比增删')
        else:
            detail.append('- 新增：%s' % ('、'.join(added) if added else '无'))
            detail.append('- 删除：%s' % ('、'.join(removed) if removed else '无'))
        if missing:
            detail.append('- **本地 %s 缺 %d 条**：%s' %
                          (page['local'], len(missing),
                           '、'.join(x['name'] for x in missing[:40]) +
                           ('…' if len(missing) > 40 else '')))
        else:
            detail.append('- 本地 %s 无缺失 ✅' % page['local'])

        new_state[title] = {
            'revid': now['revid'],
            'timestamp': now['timestamp'],
            'count': len(cur),
            'names': sorted(cur),
        }

    # 道具图标检查
    sp_missing = check_item_sprites()
    detail.append('')
    if sp_missing:
        detail.append('### 道具图标缺失（%d 条，item-sprites 里没有对应 png）' % len(sp_missing))
        detail.append('- ' + '、'.join(x['name'] for x in sp_missing[:60]) +
                      ('…' if len(sp_missing) > 60 else ''))
        detail.append('- 补图：`python3 scripts/fetch_item_sprites.py item-sprites`'
                      '（Serebii ItemDex 全量扫；已存在的文件不重写，但每个 slug 仍会发一次请求，约 3~5 分钟）')
    else:
        detail.append('### 道具图标：齐全 ✅')

    report = '\n'.join(lines + detail) + '\n'
    print()
    print(report)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    print('报告已写入 %s' % REPORT_FILE)

    if do_save:
        save_state(new_state)
        print('基线已更新：%s' % STATE_FILE)
    elif changed:
        print('（基线未更新，确认无误后加 --save 再跑一次）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
