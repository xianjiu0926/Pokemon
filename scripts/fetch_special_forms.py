#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按 pokeos 实际命名（编号+简化后缀）补齐「命名特殊」形态的缺失图。

背景：pokeos 源站 URL 用 编号+简化后缀，和 dex-list 的英文形态不一致，
历史抓取脚本按英文形态拼 URL 导致一批图 404。本脚本用显式映射表修正。

映射（dex en -> pokeos 编号+简化后缀）见 SPECIAL。
"""
import json
import os
import struct
import tempfile
import time
import urllib.request
from PIL import Image, ImageSequence

BASE = 'https://s3.pokeos.com/pokeos-uploads/assets/pokemon/home/'
UA = 'Mozilla/5.0 pkm-sprite-fetch/1.0'
DELAY = 0.2
WIDTH = 128

# dex en -> pokeos 编号+简化后缀
SPECIAL = {
    'groudon-primal': '383-mega',       # 原始回归（pokeos 用 -mega）
    'kyogre-primal': '382-mega',
    'pikachu-original': '25-original-cap',
    'pikachu-hoenn': '25-hoenn-cap',
    'pikachu-sinnoh': '25-sinnoh-cap',
    'pikachu-unova': '25-unova-cap',
    'pikachu-kalos': '25-kalos-cap',
    'pikachu-alola': '25-alola-cap',
    'pikachu-partner': '25-partner-cap',
    'pikachu-world': '25-world-cap',    # 可能 404
    'tauros-paldea-combat': '128-regional-p-combat',
    'tauros-paldea-blaze': '128-regional-p-blaze',
    'tauros-paldea-aqua': '128-regional-p-aqua',
    'necrozma-dusk-mane': '800-dusk',
    'necrozma-dawn-wings': '800-dawn',
    'shellos': '422-west',              # dex 基础 en 实际=西海
    'gastrodon': '423-west',
    'unfezant-f': 'female/521',         # 雌性：pokeos 用 female/ 子目录（动图+静图都走这个）
    'meowstic-f': '678-female',         # 雌性静图用 -female；动图走 female/678 子目录
    'indeedee-f': '876-female',         # 动图 female/876
    'basculegion-f': '902-female',      # 动图 female/902
    'oinkologne-f': '916-female',       # 动图 female/916
    # 第二批：基础形态静态图（render 基础编号）＋部分动图
    'shaymin': '492',                   # 陆上=基础 492（静态用 492，非 492-land）
    'aegislash': '681',                 # 盾牌=基础 681
    'zygarde': '718',                   # 50%=基础 718
    'morpeko-hangry': '877-hangry',
    'maushold': '925-family-of-three',       # 基础=三只
    'maushold-four': '925',                  # 四只=pokeos 基础编号
    'dudunsparce-threesegment': '982-three-segment',
    'basculin-blue-striped': '550-blue-striped',
    'basculin-white-striped': '550-white-striped',
    'floette-eternal': '670-eternal',   # 永恒之花（pokeos 用 -eternal）
    'ursaluna-bloodmoon': '901-bloodmoon',
}

# 现有文件可疑（历史按错误命名下载），强制覆盖。已修复完毕，置空避免重复下载。
FORCE = set()

SLOTS = [
    ('animated/%s.gif',        'animated/pokeos/normal/%s.gif'),
    ('animated/shiny/%s.gif',  'animated/pokeos/shiny/%s.gif'),
    ('render/%s.png',          'static/pokeos/normal/%s.png'),
    ('render/shiny/%s.png',    'static/pokeos/shiny/%s.png'),
]


def dl(url, path):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        data = urllib.request.urlopen(req, timeout=30).read()
        if len(data) < 50:
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
        return True
    except Exception:
        return False


def resize_gif(path, width=WIDTH):
    try:
        im = Image.open(path)
        if im.width <= width:
            return
        durations, frames = [], []
        for f in ImageSequence.Iterator(im):
            durations.append(f.info.get('duration', 100))
            fr = f.convert('RGBA')
            w, h = fr.size
            nh = max(1, round(h * width / w))
            frames.append(fr.resize((width, nh), Image.LANCZOS))
        if not frames:
            return
        fd, tmp = tempfile.mkstemp(suffix='.gif')
        os.close(fd)
        try:
            frames[0].save(tmp, save_all=True, append_images=frames[1:],
                           duration=durations, loop=0, disposal=2, optimize=True)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    except Exception as e:
        print('    resize 失败 %s: %s' % (path, e))


def main():
    total_ok = 0
    for en, pid in SPECIAL.items():
        marks = []
        for url_tpl, path_tpl in SLOTS:
            url = BASE + url_tpl % pid
            path = 'pokemon-sprites/' + path_tpl % en
            force = en in FORCE
            if os.path.exists(path) and not force:
                marks.append('有')
                continue
            if dl(url, path):
                if path.endswith('.gif'):
                    resize_gif(path)
                marks.append('OK')
                total_ok += 1
            else:
                marks.append('MISS')
            time.sleep(DELAY)
        print('%-22s %-22s %s' % (en, pid, ' '.join(marks)))
    print('新下载 %d 张' % total_ok)


if __name__ == '__main__':
    main()
