#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 52poke 抓取人物立绘到仓库「人物立绘/」目录。

筛选规则：只抓有「登场人物信息框 / 登場人物信息框」模板的“具体角色”页面；
NPC 训练家类型（医生、护士、场长、短裤小子等）没有该信息框，自动跳过。

合并规则：
  - 排除旁支游戏角色（随乐拍/巡护员/Masters/Champions/圆形竞技场/XD/卡牌GB/名侦探皮卡丘等）
  - 去掉角色名的「（动画）/（動畫）/（特别篇）/（全书）/（THE ORIGIN）」等媒体后缀
  - 同一角色的所有版本立绘（游戏/动画/特别篇）合并进一个以角色名命名的文件夹

目录结构：人物立绘/{角色名}/{该角色所有立绘}

用法：
  python3 scripts/fetch_portraits.py --scan    # 只扫描+合并，写清单，不下载
  python3 scripts/fetch_portraits.py --download  # 读清单，只下载（断点续跑）
  python3 scripts/fetch_portraits.py --titles "小智（动画）|大吾（特别篇）"  # 补指定角色
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'
API = 'https://wiki.52poke.com/api.php'
REFERER = 'https://wiki.52poke.com/'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, '人物立绘')
MANIFEST = os.path.join(OUT_DIR, '_portraits-manifest.json')
DEFAULT_CATS = ['主角', '勁敵', '道馆馆主', '四天王', '冠军', '训练家类型']

INFOBOX = ('登场人物信息框', '登場人物信息框')

# 旁支游戏角色（随乐拍/巡护员/Masters/Champions/圆形竞技场/XD/战棋大师/卡牌GB/名侦探皮卡丘/Café Mix）
SPIN_OFF = [
    '仁美', '創一', '南美', '夏也', '如初', '日向', '牌克', '風月',
    '威爾', '小亮', '小結', '小霓', '果塔', '蓓琪', '阿徹', '阿齊',
    '雷歐', '龍人', '夏蓉', '梧桐', '盧卡', '菲爾', '鎯琊',
]
SPIN_OFF_KW = ['古德曼', '提姆']  # 名侦探皮卡丘的提姆·古德曼（字符点不一致，用关键字）

# 简体→繁体 归一化（与 52poke 繁体主体一致，用于合并同名不同字体角色）
SIMPLIFY = str.maketrans({
    '兰': '蘭', '遥': '遙', '丽': '麗', '红': '紅', '绿': '綠',
    '蓝': '藍', '叶': '葉', '长': '長', '丝': '絲', '尔': '爾',
    '龙': '龍', '凤': '鳳', '贝': '貝', '声': '聲', '门': '門',
    '马': '馬', '见': '見', '车': '車', '东': '東', '乐': '樂',
})


def api_get(params, tries=3):
    params = dict(params)
    params['format'] = 'json'
    url = API + '?' + urllib.parse.urlencode(params)
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.5)
    return None


def get_category_members(cat):
    titles = []
    cont = None
    while True:
        params = {'action': 'query', 'list': 'categorymembers',
                  'cmtitle': 'Category:' + cat, 'cmlimit': '500'}
        if cont:
            params.update(cont)
        d = api_get(params)
        if not d:
            break
        for m in d.get('query', {}).get('categorymembers', []):
            titles.append(m['title'])
        if 'continue' in d:
            cont = d['continue']
        else:
            break
        time.sleep(0.3)
    return titles


def batch_wikitext(titles):
    out = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        params = {'action': 'query', 'prop': 'revisions',
                  'rvprop': 'content', 'rvslots': 'main',
                  'titles': '|'.join(chunk), 'redirects': '1'}
        d = api_get(params)
        print('    wikitext 批次 %d/%d (%d 页)' % (i // 50 + 1, (len(titles) + 49) // 50, len(chunk)), flush=True)
        if not d:
            continue
        redir = {}
        for r in d.get('query', {}).get('redirects', []):
            redir[r['from']] = r['to']
        for pid, p in d.get('query', {}).get('pages', {}).items():
            if 'revisions' not in p:
                continue
            wt = p['revisions'][0].get('slots', {}).get('main', {}).get('*', '') \
                 or p['revisions'][0].get('*', '')
            out[p.get('title')] = wt
        for orig, to in redir.items():
            if to in out:
                out[orig] = out[to]
        time.sleep(0.3)
    return out


def has_infobox(wt):
    return any(tpl in wt for tpl in INFOBOX)


def extract_infobox(wt):
    for tpl in INFOBOX:
        start = wt.find('{{' + tpl)
        if start >= 0:
            i = start + 2
            depth = 0
            while i < len(wt):
                if wt[i:i + 2] == '{{':
                    depth += 1
                    i += 2
                elif wt[i:i + 2] == '}}':
                    if depth == 0:
                        return wt[start:i + 2]
                    depth -= 1
                    i += 2
                else:
                    i += 1
    return ''


def extract_images(wt):
    box = extract_infobox(wt)
    imgs = []
    for m in re.finditer(r'\|image(\d*)\s*=\s*([^|\n]+)', box):
        fname = m.group(2).strip()
        if fname and fname.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            imgs.append(fname)
    return imgs


def batch_imageurl(fnames):
    url_map = {}
    fnames = list(fnames)
    for i in range(0, len(fnames), 50):
        chunk = fnames[i:i + 50]
        params = {'action': 'query',
                  'titles': '|'.join('File:' + f for f in chunk),
                  'prop': 'imageinfo', 'iiprop': 'url|size'}
        d = api_get(params)
        print('    imageinfo 批次 %d/%d' % (i // 50 + 1, (len(fnames) + 49) // 50), flush=True)
        if not d:
            continue
        for pid, p in d.get('query', {}).get('pages', {}).items():
            title = p.get('title', '')
            if title.startswith('File:'):
                title = title[len('File:'):]
            ii = p.get('imageinfo', [{}])
            if ii and ii[0].get('url'):
                url_map[title] = ii[0]['url']
                # 也按原始查询名写（后续用原始 fname 查）
        time.sleep(0.2)
    return url_map


def download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return 'skip'
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': REFERER})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) < 100:
                return 'small'
            open(path, 'wb').write(data)
            return 'ok'
        except Exception:
            time.sleep(0.5)
    return 'fail'


def is_spin_off(name):
    if name in SPIN_OFF:
        return True
    return any(k in name for k in SPIN_OFF_KW)


def base_name(name):
    """去媒体/消歧义括号后缀 + 简繁归一化。"""
    name = name.strip()
    name = re.sub(r'[（(][^）)]*[）)]\s*$', '', name).strip()
    return name.translate(SIMPLIFY)


def merge_chars(chars):
    """按 base_name 合并，同一角色多版本立绘合到一起。"""
    merged = {}
    for c in chars:
        base = base_name(c['name'])
        if base in merged:
            merged[base].update(c['images'])
        else:
            merged[base] = set(c['images'])
    return [{'name': k, 'images': sorted(v)} for k, v in merged.items()]


def scan(cats, titles=None):
    seen_titles = set()
    all_titles = []
    if titles:
        all_titles = list(titles)
        seen_titles = set(titles)
    else:
        for cat in cats:
            for t in get_category_members(cat):
                if t.startswith('User:') or t.startswith('Category:'):
                    continue
                if t not in seen_titles:
                    seen_titles.add(t)
                    all_titles.append(t)
    print('待扫描页面（去重后）: %d 个' % len(all_titles))
    wt_map = batch_wikitext(all_titles)
    print('抓到 wikitext: %d 页' % len(wt_map))
    chars = []
    for t in all_titles:
        wt = wt_map.get(t, '')
        if not wt or not has_infobox(wt):
            continue
        imgs = extract_images(wt)
        if imgs:
            chars.append({'name': t, 'images': imgs})
    return chars


def main():
    args = sys.argv[1:]
    scan_only = '--scan' in args
    download_only = '--download' in args
    cats = DEFAULT_CATS
    if '--cats' in args:
        i = args.index('--cats')
        if i + 1 < len(args):
            cats = [c for c in args[i + 1].split('|') if c]
    titles = None
    if '--titles' in args:
        i = args.index('--titles')
        if i + 1 < len(args):
            titles = [t for t in args[i + 1].split('|') if t]

    if download_only:
        if not os.path.exists(MANIFEST):
            print('manifest 不存在，先跑 --scan')
            return
        chars = json.load(open(MANIFEST)).get('characters', [])
        print('从 manifest 读取 %d 个角色，开始下载' % len(chars))
    else:
        if titles:
            print('指定标题: %d 个' % len(titles))
        else:
            print('分类: %s' % ' + '.join(cats))
        raw = scan(cats, titles)
        print('\n本次扫描到具体角色: %d 个' % len(raw))

        # 累积到 manifest 的 raw（去重 name，合并 images），支持分段扫描
        old_raw = []
        if os.path.exists(MANIFEST):
            try:
                old_raw = json.load(open(MANIFEST)).get('raw', [])
            except Exception:
                pass
        raw_map = {}
        for c in old_raw + raw:
            if c['name'] in raw_map:
                raw_map[c['name']].extend(c['images'])
            else:
                raw_map[c['name']] = list(c['images'])
        raw = [{'name': k, 'images': sorted(set(v))} for k, v in raw_map.items()]

        # 排除旁支游戏
        chars = [c for c in raw if not is_spin_off(c['name'])]
        spin = [c['name'] for c in raw if is_spin_off(c['name'])]
        print('累计原始角色 %d 个，排除旁支 %d 个' % (len(raw), len(spin)))

        # 合并（去后缀 + 同角色合并）
        chars = merge_chars(chars)
        print('合并后角色: %d 个' % len(chars))

        os.makedirs(OUT_DIR, exist_ok=True)
        manifest = {'generated': time.strftime('%Y-%m-%d'),
                    'cats': cats, 'raw': raw, 'characters': chars,
                    'excluded_spinoff': spin}
        json.dump(manifest, open(MANIFEST, 'w'), ensure_ascii=False, indent=1)
        print('清单已写入: %s（累计 %d 个合并角色）' % (MANIFEST, len(chars)))
        if scan_only:
            print('（--scan 模式，未下载图片）')
            return

    # 下载立绘：批量取 URL + 并发下载
    from concurrent.futures import ThreadPoolExecutor
    import threading
    all_fnames = set()
    for c in chars:
        for f in c['images']:
            all_fnames.add(f)
    print('批量获取图片 URL（%d 个文件）...' % len(all_fnames))
    url_map = batch_imageurl(all_fnames)
    print('拿到 URL: %d 个' % len(url_map))

    tasks = []
    for c in chars:
        folder = re.sub(r'[\\/:*?"<>|]', '_', c['name']).strip()
        for fname in c['images']:
            url = url_map.get(fname)
            if not url:
                print('  [无URL] %s / %s' % (c['name'], fname))
                continue
            path = os.path.join(OUT_DIR, folder, fname)
            tasks.append((url, path, c['name'], fname))

    ok = skip = fail = 0
    lock = threading.Lock()

    def work(task):
        nonlocal ok, skip, fail
        url, path, name, fname = task
        r = download(url, path)
        with lock:
            if r == 'ok':
                ok += 1
            elif r == 'skip':
                skip += 1
            else:
                fail += 1
                print('  [%s] %s / %s' % (r, name, fname))
        return r

    print('开始并发下载 %d 张图...' % len(tasks))
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(work, tasks))
    print('\n下载完成：成功 %d，跳过 %d，失败 %d' % (ok, skip, fail))


if __name__ == '__main__':
    main()
