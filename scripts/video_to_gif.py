#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把「录屏视频」转成仓库用的透明背景 GIF（精灵图）。

背景：有些缺图只有录屏能拿到，但录屏是带背景的不透明视频，
而 GIF 又不支持半透明。本脚本负责：

  1. 用 ffmpeg 把视频抽成帧（固定帧率）
  2. 抠掉背景 → 还原透明（两种方式，见下）
  3. 按项目约定：缩放 → alpha 阈值二值化(>=128 保留、保持原色、不预乘)
  4. 存成 GIF（disposal=2, loop=0, optimize）

依赖：ffmpeg / ffprobe（PATH 里）+ Pillow。

━━━━ 两种抠背景方式 ━━━━
方式 A（推荐，颜色无关、最稳）—— 两次录屏差分抠像：
    同一个动画，在纯绿底 #00FF00 录一次，再在纯洋红底 #FF00FF 录一次，
    精灵位置/大小保持不变。两遍「相同的像素 = 精灵本身，不同的像素 = 背景」，
    因此精灵无论什么颜色都能被精确抠出，且无杂边。
    用法：
      python3 video_to_gif.py a.mp4 --second b.mp4 --width 128 -o out.gif

方式 B（简单）—— 单色背景色度抠像：
    精灵背后垫一个它身上没有的纯色（绿/洋红/蓝），录一次。
    用法：
      python3 video_to_gif.py in.mp4 --bg "#00ff00" --tol 40 --width 128 -o out.gif

常用参数：
  --fps N        手动指定帧率（默认从视频读取；动画是 30fps 而录屏 60fps 时
                 建议 --fps 30 去重，GIF 更小）
  --width N      目标宽 px（pokeos 动图=128；0 表示不缩放）
  --tol N        抠像容差 0~255（默认 40；边缘有杂点就调大，精灵被误抠就调小）
  --align N      方式 A 两段自动对齐的最大偏移（默认 ±6；0 关闭）
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops


def parse_hex(s):
    s = s.strip().lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def probe_fps(path):
    out = subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=avg_frame_rate', '-of', 'csv=p=0', path,
    ]).decode().strip()
    if '/' in out:
        a, b = out.split('/')
        return float(a) / float(b)
    return float(out)


def extract_frames(video, fps, workdir):
    fps_s = ('%g' % fps) if fps == int(fps) else ('%d/%d' % _frac(fps))
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', video,
           '-vf', 'fps=%s' % fps_s, '-f', 'image2',
           os.path.join(workdir, 'f_%06d.png')]
    subprocess.check_call(cmd)
    return sorted(f for f in os.listdir(workdir) if f.endswith('.png'))


def _frac(x, limit=1001):
    # 把 float 转成近似的分数，保证抽帧帧率与时长一致
    from fractions import Fraction
    fr = Fraction(x).limit_denominator(limit)
    return fr.numerator, fr.denominator


def max_channel_dist(im):
    r, g, b = im.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b)


def key_single(frame, bg_rgb, tol):
    """单色背景：离背景色越近越透明。"""
    rgb = frame.convert('RGB')
    bg = Image.new('RGB', rgb.size, bg_rgb)
    dist = max_channel_dist(ImageChops.difference(rgb, bg))
    alpha = dist.point(lambda x: 0 if x <= tol else 255)
    out = rgb.convert('RGBA')
    out.putalpha(alpha)
    return out


def key_diff(a, b, tol):
    """两次录屏差分：两遍相同的像素=精灵(保留)，不同的像素=背景(透明)。"""
    ar = a.convert('RGB')
    br = b.convert('RGB')
    dist = max_channel_dist(ImageChops.difference(ar, br))
    alpha = dist.point(lambda x: 255 if x <= tol else 0)
    out = ar.convert('RGBA')
    out.putalpha(alpha)
    return out


def translate(im, dx, dy):
    # 非环绕平移（超出部分填黑），用于两段录屏对齐
    return im.transform(im.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy),
                        fillcolor=(0, 0, 0))


def best_offset(a, b, rng, tol):
    """在 ±rng 内找使两段「相同像素数」最多的偏移。

    差分抠像里：精灵本身两遍完全一致（匹配），背景两遍不同色（不匹配），
    所以「匹配像素数最多」的位置 = 精灵对齐的位置（颜色无关、不受纯色背景干扰）。
    """
    ar = a.convert('RGB')
    br = b.convert('RGB')
    best = None
    for dy in range(-rng, rng + 1):
        for dx in range(-rng, rng + 1):
            d = ImageChops.difference(ar, translate(br, dx, dy))
            dist = max_channel_dist(d)
            cnt = sum(dist.histogram()[:tol + 1])
            if best is None or cnt > best[0]:
                best = (cnt, dx, dy)
    return best[1], best[2]


def threshold_alpha(im):
    """alpha>=128 保留、否则全透明，保持原色（不预乘）。"""
    r, g, b, a = im.split()
    a = a.point(lambda x: 255 if x >= 128 else 0)
    return Image.merge('RGBA', (r, g, b, a))


def save_gif(frames, durations, out):
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=True)


def main():
    ap = argparse.ArgumentParser(description='录屏视频 → 透明 GIF')
    ap.add_argument('input', help='录屏视频（方式 A 为第一遍）')
    ap.add_argument('--second', help='第二遍录屏（方式 A 差分抠像）')
    ap.add_argument('--bg', default='#00ff00', help='方式 B 的背景色 hex')
    ap.add_argument('--tol', type=int, default=40, help='抠像容差 0~255')
    ap.add_argument('--width', type=int, default=128, help='目标宽 px，0=不缩放')
    ap.add_argument('--fps', type=float, default=None, help='手动帧率')
    ap.add_argument('--align', type=int, default=6, help='方式 A 对齐搜索 ±N')
    ap.add_argument('-o', '--out', required=True)
    args = ap.parse_args()

    fps = args.fps or probe_fps(args.input)
    print('帧率：%.3f fps' % fps)
    dur = max(1, round(1000.0 / fps))

    with tempfile.TemporaryDirectory() as wd:
        names = extract_frames(args.input, fps, wd)
        if args.second:
            wd2 = tempfile.mkdtemp()
            try:
                names2 = extract_frames(args.second, fps, wd2)
                n = min(len(names), len(names2))
                names, names2 = names[:n], names2[:n]
                print('两段各 %d 帧' % n)
            except Exception:
                raise

        print('帧数：%d' % len(names))
        durations = [dur] * len(names)

        frames = []
        dx = dy = 0
        for i, name in enumerate(names):
            a = Image.open(os.path.join(wd, name))
            if args.second:
                b = Image.open(os.path.join(wd2, names2[i]))
                if i == 0 and args.align:
                    dx, dy = best_offset(a, b, args.align, args.tol)
                    print('对齐偏移：%+d,%+d' % (dx, dy))
                b = translate(b, dx, dy)
                f = key_diff(a, b, args.tol)
            else:
                f = key_single(a, parse_hex(args.bg), args.tol)

            if args.width:
                w, h = f.size
                nh = max(1, round(h * args.width / w))
                f = f.resize((args.width, nh), Image.LANCZOS)
                f = threshold_alpha(f)
            frames.append(f)
            if (i + 1) % 30 == 0 or i == 0:
                print('  帧 %d/%d (%dx%d)' % (i + 1, len(names), f.width, f.height))

        save_gif(frames, durations, args.out)
        print('完成：%s  %d 帧  %dKB' % (args.out, len(frames),
                                        os.path.getsize(args.out) // 1024))


if __name__ == '__main__':
    sys.exit(main())
