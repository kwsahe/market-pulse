# screenshots/generate_logo.py
# Market Pulse 대표 로고(아이콘 마크) 생성 스크립트.
# 대시보드(dashboard/theme.py)와 동일한 다크 테마 색상·배경 글로우를 재사용해서
# "실제 제품과 같은 브랜드"로 보이게 만든다. 4배 슈퍼샘플링 후 다운스케일해서
# 곡선/사선 가장자리가 계단현상 없이 매끈하게 나오도록 한다.
#
# 아이콘 모티프: 막대그래프(시장 데이터) 위로 펄스(심박) 파형이 지나가는 형태 —
# "Market"(막대) + "Pulse"(파형)를 문자 그대로 결합했다.

import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path(__file__).parent
FONT_PATH = OUT_DIR / "fonts" / "Outfit-Bold.ttf"

# 대시보드와 동일한 색상 토큰 (dashboard/theme.py)
BG = (13, 15, 20)          # #0D0F14
CYAN = (34, 211, 238)       # #22D3EE
VIOLET = (139, 92, 246)     # #8B5CF6
TEXT = (243, 244, 246)      # #F3F4F6
GLOW_CYAN_A = 90            # 배경 글로우 알파 (favicon 크기에서도 보이도록 웹 배경보다 조금 진하게)
GLOW_VIOLET_A = 80

SS = 4  # 슈퍼샘플링 배수
SIZE = 1024 * SS


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def radial_glow(size, center, radius, color, max_alpha):
    """중심에서 바깥으로 부드럽게 사라지는 원형 글로우 레이어 (RGBA)"""
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = center
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    alpha = np.clip(1.0 - dist, 0, 1) ** 1.6 * max_alpha
    layer = np.zeros((size, size, 4), dtype=np.uint8)
    layer[..., 0] = color[0]
    layer[..., 1] = color[1]
    layer[..., 2] = color[2]
    layer[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def pulse_path(x0, x1, y_mid, amp):
    """심박 모니터(ECG) 스타일 폴리라인 좌표 리스트"""
    pts = []
    span = x1 - x0
    # 구간 비율: 평탄 - 완만한 굴곡 - 급격한 스파이크 - 평탄
    xs = [0.0, 0.16, 0.30, 0.38, 0.44, 0.50, 0.58, 0.66, 0.82, 1.0]
    ys = [0.0, 0.0, -0.18, 0.35, -1.0, 0.55, -0.05, 0.0, 0.0, 0.0]
    for xr, yr in zip(xs, ys):
        pts.append((x0 + span * xr, y_mid + amp * yr))
    return pts


def smooth_polyline(points, samples_per_seg=24):
    """Catmull-Rom 스플라인으로 폴리라인을 부드럽게 보간"""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(points[-1])
    return out


def main():
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # ---------- 1. 배경 (둥근 사각형 배지 + 앰비언트 글로우) ----------
    corner_r = int(SIZE * 0.225)  # iOS 스타일 squircle에 가까운 라운드
    bg_layer = Image.new("RGBA", (SIZE, SIZE), BG + (255,))
    bg_layer = Image.alpha_composite(bg_layer, radial_glow(SIZE, (SIZE * 0.08, SIZE * 0.06), SIZE * 0.95, CYAN, GLOW_CYAN_A))
    bg_layer = Image.alpha_composite(bg_layer, radial_glow(SIZE, (SIZE * 0.95, SIZE * 0.97), SIZE * 0.95, VIOLET, GLOW_VIOLET_A))

    mask = rounded_mask(SIZE, corner_r)
    badge = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    badge.paste(bg_layer, (0, 0), mask)

    draw = ImageDraw.Draw(badge)

    # 배지 테두리 (은은한 라이트 스트로크로 다크모드 카드 느낌)
    draw.rounded_rectangle(
        (SS * 2, SS * 2, SIZE - SS * 2, SIZE - SS * 2),
        radius=corner_r, outline=(45, 51, 64, 255), width=SS * 3,
    )

    # ---------- 2. 막대그래프 (시장 데이터) ----------
    n_bars = 4
    bar_w = SIZE * 0.10
    gap = SIZE * 0.045
    heights_ratio = [0.30, 0.48, 0.66, 0.86]
    base_y = SIZE * 0.74
    total_w = n_bars * bar_w + (n_bars - 1) * gap
    start_x = (SIZE - total_w) / 2

    bar_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(bar_layer)
    for i in range(n_bars):
        x0 = start_x + i * (bar_w + gap)
        x1 = x0 + bar_w
        h = SIZE * 0.40 * heights_ratio[i]
        y0 = base_y - h
        color = lerp(CYAN, VIOLET, i / (n_bars - 1))
        bar_draw.rounded_rectangle((x0, y0, x1, base_y), radius=bar_w * 0.28, fill=color + (235,))
    badge = Image.alpha_composite(badge, Image.composite(bar_layer, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    # ---------- 3. 펄스(심박) 파형 — 막대 위로 가로지르는 흰색 라인 + 글로우 ----------
    y_mid = SIZE * 0.40
    raw_pts = pulse_path(SIZE * 0.12, SIZE * 0.88, y_mid, SIZE * 0.16)
    smooth_pts = smooth_polyline(raw_pts, samples_per_seg=28)

    pulse_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pulse_layer)
    pd.line(smooth_pts, fill=TEXT + (255,), width=int(SIZE * 0.017), joint="curve")
    for xy in (smooth_pts[0], smooth_pts[-1]):
        r = SIZE * 0.012
        pd.ellipse((xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r), fill=TEXT + (255,))

    glow = pulse_layer.filter(ImageFilter.GaussianBlur(SIZE * 0.012))
    glow_boost = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow_boost.paste(Image.new("RGBA", (SIZE, SIZE), CYAN + (140,)), (0, 0), glow.split()[3])

    badge = Image.alpha_composite(badge, Image.composite(glow_boost, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))
    badge = Image.alpha_composite(badge, Image.composite(pulse_layer, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    # ---------- 4. 다운스케일 (슈퍼샘플링 안티에일리어싱) ----------
    final_size = SIZE // SS
    final = badge.resize((final_size, final_size), Image.LANCZOS)

    out_path = OUT_DIR / "logo_mark.png"
    final.save(out_path)
    print(f"saved: {out_path.resolve()}  ({final_size}x{final_size})")


if __name__ == "__main__":
    main()
