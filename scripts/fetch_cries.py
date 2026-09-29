#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载宝可梦叫声（.ogg）到仓库 cries/ 目录。来源 PokeAPI/cries（jsdelivr CDN）。
断点续跑：已存在且 >100 字节的文件跳过。
"""
import os
import time
import urllib.request

UA = 'Mozilla/5.0 pkm/1.0'
BASE = 'https://cdn.jsdelivr.net/gh/PokeAPI/cries@main/cries/pokemon/latest/'
OUT = 'cries/'
START = 1
END = 1025  # 全国编号 1~1025（Gen10 1026+ 无叫声）


def main():
    os.makedirs(OUT, exist_ok=True)
    ok = skip = fail = 0
    for i in range(START, END + 1):
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
                if i <= 1025:
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
    print('完成：下载 %d，跳过 %d，失败 %d' % (ok, skip, fail))


if __name__ == '__main__':
    main()
