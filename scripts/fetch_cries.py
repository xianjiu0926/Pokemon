#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载宝可梦叫声（.ogg）到仓库 cries/ 目录。来源 PokeAPI/cries（jsdelivr CDN）。
断点续跑：已存在且 >100 字节的文件跳过。

用法：
  python3 scripts/fetch_cries.py                # 默认 1~1025
  python3 scripts/fetch_cries.py --from 1026    # 只下 1026 起（加新叫声）
  python3 scripts/fetch_cries.py --to 151       # 只下到 151
  python3 scripts/fetch_cries.py --from 1026 --to 1100
"""
import os
import sys
import time
import urllib.request

UA = 'Mozilla/5.0 pkm/1.0'
BASE = 'https://cdn.jsdelivr.net/gh/PokeAPI/cries@main/cries/pokemon/latest/'
OUT = 'cries/'
DEFAULT_START = 1
DEFAULT_END = 1025


def parse_args(argv):
    start, end = DEFAULT_START, DEFAULT_END
    has_from = has_to = False
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == '--from' and i + 1 < len(argv):
            start = int(argv[i + 1]); has_from = True; i += 2
        elif a == '--to' and i + 1 < len(argv):
            end = int(argv[i + 1]); has_to = True; i += 2
        else:
            i += 1
    if has_from and not has_to:
        end = start + 999  # 只给 --from 时，默认往后扫 1000 个（404 自动跳过）
    return start, end


def main():
    start, end = parse_args(sys.argv)
    os.makedirs(OUT, exist_ok=True)
    ok = skip = fail = 0
    for i in range(start, end + 1):
        f = '%s%d.ogg' % (OUT, i)
        if os.path.exists(f) and os.path.getsize(f) > 100:
            skip += 1
            continue
        url = BASE + '%d.ogg' % i
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            data = urllib.request.urlopen(req, timeout=20).read()
            if len(data) < 100:
                fail += 1
                print('  [!] %d 过小(%dB)' % (i, len(data)))
                continue
            open(f, 'wb').write(data)
            ok += 1
            if ok % 100 == 0:
                print('  已下 %d，跳过 %d，失败 %d' % (ok, skip, fail))
        except Exception as e:
            fail += 1
            print('  [!] %d 失败: %s' % (i, e))
        time.sleep(0.05)
    print('完成（%d~%d）：下载 %d，跳过 %d，失败 %d' % (start, end, ok, skip, fail))


if __name__ == '__main__':
    main()
