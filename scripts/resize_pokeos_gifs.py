#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 PokeOS HOME 动图（原图分辨率，~600-1200px）压到 128px 宽，保持动画与帧时长。
用法：python3 resize_pokeos_gifs.py
只处理宽度 > 200px 的 GIF（128px 的已达标会跳过），原地覆盖。
"""
import glob
import os
import struct
import sys
import tempfile
from PIL import Image, ImageSequence, ImageChops

WIDTH = 128


def gif_width(path):
    try:
        d = open(path, 'rb').read(10)
        if d[:4] != b'GIF8':
            return 0
        return struct.unpack('<HH', d[6:10])[0]
    except Exception:
        return 0


def resize_gif(src, width=WIDTH, premult=True):
    im = Image.open(src)
    durations = []
    frames = []
    for frame in ImageSequence.Iterator(im):
        durations.append(frame.info.get('duration', 100))
        f = frame.convert('RGBA')
        w, h = f.size
        nh = max(1, round(h * width / w))
        f = f.resize((width, nh), Image.LANCZOS)
        if premult:
            # 预乘 alpha：半透明边缘像素颜色按 alpha 变暗，避免存 GIF 时硬切成浅色毛边
            r, g, b, a = f.split()
            r = ImageChops.multiply(r, a)
            g = ImageChops.multiply(g, a)
            b = ImageChops.multiply(b, a)
            f = Image.merge('RGBA', (r, g, b, a))
        frames.append(f)
    if not frames:
        return
    fd, tmp = tempfile.mkstemp(suffix='.gif')
    os.close(fd)
    try:
        frames[0].save(tmp, save_all=True, append_images=frames[1:],
                       duration=durations, loop=0, disposal=2, optimize=True)
        os.replace(tmp, src)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    files = sorted(glob.glob('pokemon-sprites/animated/pokeos/*/*.gif'))
    todo = [f for f in files if gif_width(f) > 200]
    print('需压至 128px 的动图：%d 个' % len(todo))
    n = 0
    for f in todo:
        before = os.path.getsize(f)
        resize_gif(f)
        after = os.path.getsize(f)
        n += 1
        if n % 10 == 0 or after > before:
            print('  [%d/%d] %s %dKB -> %dKB' % (n, len(todo), f.split('/')[-1], before // 1024, after // 1024))
    print('完成：%d 个' % n)


if __name__ == '__main__':
    main()
