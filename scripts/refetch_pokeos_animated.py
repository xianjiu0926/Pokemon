#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重新下载 PokeOS HOME 动图原图，用「阈值二值化」压到 128px，消除半透明硬切毛边。

背景：旧图直接 resize+存 GIF，半透明抗锯齿边缘被硬切成白边/黑边。
此脚本重新从源站拉原图（大 GIF），resize_pokeos_gifs.resize_gif 已改阈值二值化。

断点续跑：pokeos-refetch-done.txt 记录已完成的 slug。
用法：python3 scripts/refetch_pokeos_animated.py [并发数]
"""
import os
import sys
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_pokemon_sprites import load_entries, build_mapping, pokeos_id, slugify, BASE
from resize_pokeos_gifs import resize_gif

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN_N = os.path.join(ROOT, 'pokemon-sprites/animated/pokeos/normal')
AN_S = os.path.join(ROOT, 'pokemon-sprites/animated/pokeos/shiny')
DONE = os.path.join(ROOT, 'pokeos-refetch-done.txt')


def load_done():
    if os.path.exists(DONE):
        return set(l.strip() for l in open(DONE, encoding='utf-8') if l.strip())
    return set()


def mark_done(slug):
    with open(DONE, 'a', encoding='utf-8') as f:
        f.write(slug + '\n')


def fetch_resize(url, dst):
    fd, tmp = tempfile.mkstemp(suffix='.gif')
    os.close(fd)
    try:
        r = subprocess.run(['curl', '-s', '-o', tmp, '--connect-timeout', '10',
                            '--max-time', '45', '-w', '%{http_code}', url],
                           capture_output=True, text=True, timeout=60)
        code = r.stdout.strip()
        if code != '200' or not os.path.exists(tmp) or os.path.getsize(tmp) < 500:
            return False
        resize_gif(tmp)  # 阈值二值化，压 128px
        os.replace(tmp, dst)
        return True
    except Exception:
        return False
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def process_one(item):
    slug, pid, no, cn = item
    got = []
    if fetch_resize(BASE + 'animated/%s.gif' % pid, os.path.join(AN_N, slug + '.gif')):
        got.append('N')
    if fetch_resize(BASE + 'animated/shiny/%s.gif' % pid, os.path.join(AN_S, slug + '.gif')):
        got.append('S')
    return slug, ''.join(got)


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    entries = load_entries()
    base_slug = build_mapping(entries)
    done = load_done()

    todo, seen = [], set()
    for p in entries:
        slug = slugify(p['en'])
        if slug in seen:
            continue
        seen.add(slug)
        if slug in done:
            continue
        pid, _ = pokeos_id(p, base_slug)
        if pid is None:
            continue
        todo.append((slug, pid, p['no'], p['name']))

    print('待处理 %d 个（已完成 %d，并发 %d）' % (len(todo), len(done), workers), flush=True)
    ok = miss = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(process_one, t): t for t in todo}
        for fut in as_completed(futs):
            slug, got = fut.result()
            if got:
                ok += 1
                mark_done(slug)
            else:
                miss += 1
            n = ok + miss
            if n % 25 == 0 or not got:
                print('  %4d/%d %s [%s]' % (n, len(todo), slug, got or 'X'), flush=True)
    print('完成：OK=%d MISS=%d' % (ok, miss), flush=True)


if __name__ == '__main__':
    main()
