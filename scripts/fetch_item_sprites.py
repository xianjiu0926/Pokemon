#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从公开网站抓取宝可梦道具图标，按 slug 规则命名后输出。

来源：
  1. Serebii.net ItemDex（https://www.serebii.net/itemdex/）—— 全分类道具图标
  2. 神奇宝贝百科图床（https://media.52poke.com）—— 部分 Serebii 没有的道具图

命名规则（与 Serebii 图床一致）：
  小写 + 去掉连字符/下划线/空格 + 保留点号，例如：
    poke-ball   -> pokeball.png
    cheri-berry -> cheriberry.png
    azelf'sfang -> azelfsfang.png

用法：
  python3 fetch_item_sprites.py [输出目录] [--only-serebii]

依赖：仅 Python 3 标准库（urllib）。
"""
import re
import os
import sys
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# Serebii ItemDex 的 14 个分类列表页
SEREBII_CATS = [
    'battleeffect', 'berry', 'decorations', 'eventitem', 'evolutionary',
    'fossil', 'gsberry', 'holditem', 'keyitem', 'mail', 'miscellaneous',
    'pokeball', 'recovery', 'vitamins',
]

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) pkm-data-fetch/1.0'


def slug(s):
    """与 HUD / Serebii 一致的 slug 规则。"""
    s = str(s).lower()
    s = re.sub(r'\.(png|gif|jpe?g|webp)$', '', s)
    s = re.sub(r'[^a-z0-9.]+', '', s)
    return s


def http_get(url, referer=None, timeout=20):
    headers = {'User-Agent': UA}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def serebii_slugs():
    """抓 Serebii ItemDex 各分类页，提取全部道具 slug。"""
    slugs = []
    for cat in SEREBII_CATS:
        url = 'https://www.serebii.net/itemdex/list/%s.shtml' % cat
        try:
            html = http_get(url).decode('utf-8', 'ignore')
        except Exception as e:
            print('  [!] 分类页抓取失败 %s: %s' % (cat, e))
            continue
        found = re.findall(r'itemdex/([a-z0-9.-]+)\.shtml', html)
        slugs.extend(s for s in found if s != 'list')
        time.sleep(0.3)
    return sorted(set(slugs))


def download_one(s, out):
    """下载单个 Serebii 道具图，返回 (状态, slug, 输出名)。"""
    # 有些 slug 带多余点号（如 guardspec.），尝试多个变体
    for cand in dict.fromkeys([s, s.rstrip('.')]):
        url = 'https://www.serebii.net/itemdex/sprites/%s.png' % cand
        try:
            data = http_get(url, referer='https://www.serebii.net/itemdex/')
            if data[:8] == b'\x89PNG\r\n\x1a\n':
                dest = os.path.join(out, slug(cand) + '.png')
                if not os.path.exists(dest):
                    with open(dest, 'wb') as f:
                        f.write(data)
                return ('ok', s, slug(cand))
        except Exception:
            continue
    return ('fail', s, '')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'item-sprites'
    os.makedirs(out, exist_ok=True)

    print('== 抓取 Serebii ItemDex 分类列表 ==')
    slugs = serebii_slugs()
    print('  共 %d 个道具 slug' % len(slugs))

    print('== 下载道具图标 ==')
    ok, fail = 0, []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for st, s, nm in ex.map(lambda s: download_one(s, out), slugs):
            if st == 'ok':
                ok += 1
            else:
                fail.append(s)
    print('  成功 %d，失败 %d' % (ok, len(fail)))
    if fail:
        print('  失败清单（Serebii 无图或图挂了）：')
        for s in fail:
            print('    -', s)
    print('  输出目录：%s（共 %d 个文件）' % (out, len(os.listdir(out))))


if __name__ == '__main__':
    main()
