#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 pokestats（PokeAPI sprites 镜像）抓 Legends Z-A 的 3D 模型动图，补新 Mega 的动图缺口。

源：https://assets.pokestats.gg/pokeapi/orig/pokemon/versions/generation-ix/legends-za/{id}.webp
    闪光在 .../shiny/{id}.webp；背面在 .../back/{id}.webp、.../back/shiny/{id}.webp
每张 512x512、约 170 帧、6MB 左右。

产物：pokemon-sprites/animated/pokeos/{normal,shiny}/{slug}.gif
     —— 放 pokeos 槽位是因为 HUD 兜底顺序 [['animated',sel],['animated',other],...]
        会跨来源找，补一处就够；3D 模型的观感也更接近 pokeos 那套。

转换：所有帧合并 bbox 统一裁剪（模型不抖）→ 缩到宽 128 → alpha 阈值二值化
      （>=128 留、保持原色、不预乘，跟 resize_pokeos_gifs.py 同一套）→ 每 step 帧取 1。

用法：
  python3 scripts/fetch_za_sprites.py            # 补 MISSING 清单里的新 Mega
  python3 scripts/fetch_za_sprites.py --only zeraora-mega
  python3 scripts/fetch_za_sprites.py --step 1   # 不抽帧（体积大）
  python3 scripts/fetch_za_sprites.py --maxframes 100  # 默认：每只最多 100 帧
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageSequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = 'https://assets.pokestats.gg/pokeapi/orig/pokemon/versions/generation-ix/legends-za/'
OUT_N = os.path.join(ROOT, 'pokemon-sprites/animated/pokeos/normal')
OUT_S = os.path.join(ROOT, 'pokemon-sprites/animated/pokeos/shiny')

# 新 Mega：slug（仓库用的名字）→ PokeAPI pokemon id
ZA_IDS = {
    'raichu-mega-x': 10304,
    'raichu-mega-y': 10305,
    'clefable-mega': 10278,
    'victreebel-mega': 10279,
    'starmie-mega': 10280,
    'dragonite-mega': 10281,
    'meganium-mega': 10282,
    'feraligatr-mega': 10283,
    'skarmory-mega': 10284,
    'froslass-mega': 10285,
    'emboar-mega': 10286,
    'excadrill-mega': 10287,
    'scolipede-mega': 10288,
    'scrafty-mega': 10289,
    'eelektross-mega': 10290,
    'chandelure-mega': 10291,
    'chesnaught-mega': 10292,
    'delphox-mega': 10293,
    'greninja-mega': 10294,
    'pyroar-mega': 10295,
    'floette-mega': 10296,
    'malamar-mega': 10297,
    'barbaracle-mega': 10298,
    'dragalge-mega': 10299,
    'hawlucha-mega': 10300,
    'zygarde-mega': 10301,
    'drampa-mega': 10302,
    'falinks-mega': 10303,
    'chimecho-mega': 10306,
    'absol-mega-z': 10307,
    'staraptor-mega': 10308,
    'garchomp-mega-z': 10309,
    'heatran-mega': 10311,
    'darkrai-mega': 10312,
    'golurk-mega': 10313,
    'meowstic-mega': 10314,
    'meowstic-female-mega': 10326,
    'crabominable-mega': 10315,
    'golisopod-mega': 10316,
    'magearna-mega': 10317,
    'magearna-original-mega': 10318,
    'zeraora-mega': 10319,
    'scovillain-mega': 10320,
    'glimmora-mega': 10321,
    'tatsugiri-mega': 10322,
    'tatsugiri-droopy-mega': 10323,
    'tatsugiri-stretchy-mega': 10324,
    'baxcalibur-mega': 10325,
    # 南瓜精/南瓜怪人分尺寸 —— 注意上游 10027=10028=710 是同一张图，
    # 只有 10029/10032（super）是独立的模型；补上去只是让清单不缺，看不出差别。
    'pumpkaboo-small': 10027,
    'pumpkaboo-large': 10028,
    'pumpkaboo-super': 10029,
    'gourgeist-small': 10030,
    'gourgeist-large': 10031,
    'gourgeist-super': 10032,
    # 美洛耶塔舞步形态（普通图已有，只缺闪光）
    'meloetta-pirouette': 10018,
}

WIDTH = 128


def download(url, dst):
    r = subprocess.run(['curl', '-sS', '-o', dst, '--max-time', '180', '-w', '%{http_code}', url],
                       capture_output=True, text=True, timeout=200)
    if r.stdout.strip() != '200' or not os.path.exists(dst) or os.path.getsize(dst) < 1000:
        return False
    return True


def webp_to_gif(src, dst, step=0, maxframes=100):
    """step=0 时按 maxframes 自动抽帧（原图 150-380 帧，全留太大）。"""
    im = Image.open(src)
    frames = [f.convert('RGBA') for f in ImageSequence.Iterator(im)]
    if not frames:
        return False
    if step <= 0:
        step = max(1, -(-len(frames) // maxframes))
    # 所有帧合一个 bbox，模型位置才不抖
    bbox = None
    for f in frames:
        bb = f.split()[3].getbbox()
        if bb is None:
            continue
        if bbox is None:
            bbox = list(bb)
        else:
            bbox[0] = min(bbox[0], bb[0]); bbox[1] = min(bbox[1], bb[1])
            bbox[2] = max(bbox[2], bb[2]); bbox[3] = max(bbox[3], bb[3])
    if bbox is None:
        return False
    pad = 3
    bbox = [max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(frames[0].width, bbox[2] + pad), min(frames[0].height, bbox[3] + pad)]

    out = []
    for f in frames[::step]:
        f = f.crop(bbox)
        w, h = f.size
        nh = max(1, round(h * WIDTH / w))
        f = f.resize((WIDTH, nh), Image.LANCZOS)
        r, g, b, a = f.split()
        a = a.point(lambda x: 255 if x >= 128 else 0)
        # GIF 的透明必须落到调色板索引上：255 号位留给透明，
        # 透明像素按 alpha 贴回 255；否则透明区会被量化成黑色（整张黑底）。
        q = f.convert('RGB').quantize(colors=255, method=Image.FASTOCTREE, dither=Image.NONE)
        q.paste(255, mask=a.point(lambda x: 255 if x < 128 else 0))
        out.append(q)

    out[0].save(dst, save_all=True, append_images=out[1:], duration=33 * step, loop=0,
                disposal=2, optimize=True, transparency=255)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--step', type=int, default=0, help='抽帧步长，0=按 --maxframes 自动')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--maxframes', type=int, default=100)
    a = ap.parse_args()

    todo = ZA_IDS
    if a.only:
        keys = [k.strip() for k in a.only.split(',') if k.strip()]
        todo = {k: ZA_IDS[k] for k in keys if k in ZA_IDS}
        if not todo:
            print('没有匹配的 slug'); return 1

    ok = skip = miss = 0
    for slug, pid in todo.items():
        for shiny, sub, outdir in ((False, '', OUT_N), (True, 'shiny/', OUT_S)):
            dst = os.path.join(outdir, slug + '.gif')
            if os.path.exists(dst) and not a.force:
                skip += 1
                continue
            url = SRC + sub + '%d.webp' % pid
            fd, tmpw = tempfile.mkstemp(suffix='.webp')
            os.close(fd)
            fdt, tmpg = tempfile.mkstemp(suffix='.gif')
            os.close(fdt)
            try:
                if not download(url, tmpw):
                    print('  [MISS] %s %s' % (slug, 'shiny' if shiny else 'normal'))
                    miss += 1
                    continue
                if not webp_to_gif(tmpw, tmpg, a.step, a.maxframes):
                    print('  [FAIL] %s %s（转换失败）' % (slug, 'shiny' if shiny else 'normal'))
                    miss += 1
                    continue
                os.replace(tmpg, dst)
                print('  [OK] %s %s %dKB' % (slug, 'shiny' if shiny else 'normal',
                                             os.path.getsize(dst) // 1024))
                ok += 1
            finally:
                for p in (tmpw, tmpg):
                    try: os.remove(p)
                    except Exception: pass
        sys.stdout.flush()

    print('\n完成：新增 %d，已存在跳过 %d，失败 %d' % (ok, skip, miss))
    return 0


if __name__ == '__main__':
    sys.exit(main())
