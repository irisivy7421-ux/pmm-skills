# -*- coding: utf-8 -*-
"""
measure_ink.py — LOGO 墙「二次缩小」防线的量化闸门工具。

用途:测量一张(或一批)图里 Logo 墨迹占画布的宽/高百分比。
它是 SKILL.md 第零点一节「交付前量化闸门」的配套脚本——把"有没有被二次缩小"
从肉眼判断变成可量化的数字对比。

典型用法:
  1) 处理前,测量每个【源文件】的墨迹占比,存为基线:
       python3 measure_ink.py SRC_DIR --json baseline.json
  2) 处理后,测量每个【做好的砖块】的墨迹占比:
       python3 measure_ink.py TILES_DIR --json output.json
  3) 对比:成品砖做完后墨迹占比应与源文件基线基本一致(±3%);
     整批中位数应落在 宽 70–80% / 高 40–50%。低于此区间 = 被二次缩小,返工。
     python3 measure_ink.py TILES_DIR --baseline baseline.json

判定口径(与 SKILL.md 一致):
  - 比例(宽/高)∈ [1.85, 2.15]  → 成品砖:原样铺满,禁止裁墨迹/套版心。
  - 比例在此区间之外            → 原始 Logo:才走版心缩放。
"""
import os, sys, json, argparse, statistics as st
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

INK_THRESHOLD = 235   # 合成白底后, min(R,G,B) < 235 视为墨迹


def ink_pct(path):
    """返回 (画布宽, 画布高, 宽高比, 墨迹宽占比%, 墨迹高占比%, 是否白底matte)。"""
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    comp = Image.alpha_composite(bg, im).convert("RGB")
    px = comp.load()
    step = max(1, min(W, H) // 600)
    minx, miny, maxx, maxy = W, H, 0, 0
    found = False
    for y in range(0, H, step):
        for x in range(0, W, step):
            r, g, b = px[x, y]
            if min(r, g, b) < INK_THRESHOLD:
                found = True
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    if not found:
        return (W, H, W / H, 0.0, 0.0, "EMPTY")
    wp = (maxx - minx) * 100.0 / W
    hp = (maxy - miny) * 100.0 / H
    alpha = im.split()[3]
    corners = [alpha.getpixel((0, 0)), alpha.getpixel((W - 1, 0)),
               alpha.getpixel((0, H - 1)), alpha.getpixel((W - 1, H - 1))]
    matte = "WHITE" if all(a > 250 for a in corners) else "TRANSP"
    return (W, H, W / H, wp, hp, matte)


def classify(ratio):
    return "FINISHED_TILE(成品砖)" if 1.85 <= ratio <= 2.15 else "RAW_LOGO(原始Logo)"


def main():
    ap = argparse.ArgumentParser(description="测量 Logo 墨迹占比,防二次缩小")
    ap.add_argument("path", help="单个图片,或一个目录(批量测所有 png/jpg)")
    ap.add_argument("--json", help="把结果写到该 json 文件(作为基线)")
    ap.add_argument("--baseline", help="与该基线 json 逐文件对比,超 ±3% 报警")
    args = ap.parse_args()

    if os.path.isdir(args.path):
        files = sorted(f for f in os.listdir(args.path)
                       if f.lower().endswith((".png", ".jpg", ".jpeg")))
        items = [(f, os.path.join(args.path, f)) for f in files]
    else:
        items = [(os.path.basename(args.path), args.path)]

    results = {}
    ws, hs = [], []
    print(f"{'file':38s} {'ratio':>6s} {'inkW%':>6s} {'inkH%':>6s}  class")
    for name, p in items:
        W, H, ratio, wp, hp, matte = ink_pct(p)
        results[name] = {"w": W, "h": H, "ratio": round(ratio, 3),
                         "inkW": round(wp, 1), "inkH": round(hp, 1), "matte": matte}
        ws.append(wp); hs.append(hp)
        print(f"{name[:38]:38s} {ratio:6.2f} {wp:6.1f} {hp:6.1f}  {classify(ratio)}")

    if ws:
        mw, mh = st.median(ws), st.median(hs)
        print("\n=== 汇总 ===")
        print(f"墨迹宽占比: min {min(ws):.0f}  max {max(ws):.0f}  中位数 {mw:.0f}  (目标 70–80)")
        print(f"墨迹高占比: min {min(hs):.0f}  max {max(hs):.0f}  中位数 {mh:.0f}  (目标 40–50)")
        flag = (mw < 65) or (mh < 35)
        print("判定:", "❌ 疑似被二次缩小,请返工" if flag else "✅ 视觉重量达标")

    if args.baseline:
        base = json.load(open(args.baseline, encoding="utf-8"))
        print("\n=== 与基线逐文件对比(容差 ±3%)===")
        bad = 0
        for name, r in results.items():
            b = base.get(name)
            if not b:
                continue
            dw, dh = r["inkW"] - b["inkW"], r["inkH"] - b["inkH"]
            # 只有成品砖需要与源文件基本一致
            if 1.85 <= b["ratio"] <= 2.15 and (dw < -3 or dh < -3):
                bad += 1
                print(f"  ❌ {name[:34]:34s} 源 {b['inkW']:.0f}/{b['inkH']:.0f}"
                      f" → 砖 {r['inkW']:.0f}/{r['inkH']:.0f}  (缩小了)")
        print("成品砖二次缩小数量:", bad, "→", "通过 ✅" if bad == 0 else "返工 ❌")

    if args.json:
        json.dump(results, open(args.json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("\n已写入", args.json)


if __name__ == "__main__":
    main()
