#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只补 PokeOS 动图缺口：HEAD 探测→GET 下载→压到 128px。"""
import os, sys, json, glob, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_pokemon_sprites import load_entries, build_mapping, pokeos_id, slugify, BASE
from resize_pokeos_gifs import resize_gif

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN_N = os.path.join(ROOT, 'pokemon-sprites/animated/pokeos/normal')
AN_S = os.path.join(ROOT, 'pokemon-sprites/animated/pokeos/shiny')

def have(dirn, slug, ext):
    return os.path.exists(os.path.join(dirn, slug + ext))

def head_ok(url):
    r = subprocess.run(['curl','-s','-o','/dev/null','-w','%{http_code}','--max-time','8','-I',url],
                       capture_output=True, text=True, timeout=20)
    return r.stdout.strip() == '200'

def fetch_resize(url, dst):
    fd, tmp = tempfile.mkstemp(suffix='.gif')
    os.close(fd)
    r = subprocess.run(['curl','-s','-o',tmp,'--max-time','45','-w','%{http_code}',url],
                       capture_output=True, text=True, timeout=90)
    code = r.stdout.strip()
    if code != '200' or not os.path.exists(tmp) or os.path.getsize(tmp) < 500:
        try: os.remove(tmp)
        except: pass
        return False
    try:
        resize_gif(tmp)
        os.replace(tmp, dst)
        return True
    except Exception as e:
        try: os.remove(tmp)
        except: pass
        return False

entries = load_entries()
base_slug = build_mapping(entries)
by_en = {}
for p in entries:
    by_en.setdefault(slugify(p['en']), p)

missing = []
for p in entries:
    slug = slugify(p['en'])
    if not have(AN_N, slug, '.gif') or not have(AN_S, slug, '.gif'):
        pid, _ = pokeos_id(p, base_slug)
        if pid is None:
            continue
        missing.append((slug, pid, p['name'], p['no']))

# 去重
seen = set(); todo = []
for s, pid, cn, no in missing:
    if s in seen: continue
    seen.add(s); todo.append((s, pid, cn, no))

print('缺动图(至少一个槽)条目: %d' % len(todo), flush=True)
ok = miss = 0
for slug, pid, cn, no in sorted(todo):
    need_n = not have(AN_N, slug, '.gif')
    need_s = not have(AN_S, slug, '.gif')
    got = []
    if need_n:
        u = BASE + 'animated/%s.gif' % pid
        if fetch_resize(u, os.path.join(AN_N, slug + '.gif')): got.append('N')
    if need_s:
        u = BASE + 'animated/shiny/%s.gif' % pid
        if fetch_resize(u, os.path.join(AN_S, slug + '.gif')): got.append('S')
    if got:
        ok += 1
        print('  [OK %s] #%s %s (%s)' % ('/'.join(got), no, cn, slug), flush=True)
    else:
        miss += 1
        print('  [MISS] #%s %s (%s)  pid=%s' % (no, cn, slug, pid), flush=True)

print('\n完成: OK=%d MISS=%d' % (ok, miss), flush=True)
