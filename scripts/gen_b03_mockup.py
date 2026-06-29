#!/usr/bin/env python3
"""Author-time generator for b-03's PM mockup screenshot (fixtures/last_month_summary.png).

A real PM doesn't hand an agent a JSON schema — they paste a picture of last month's summary and
say "make this month's look like this." This renders that picture: a small metrics-summary card
with last month's example numbers and, crucially, a footnote stating the exclusion rule. The
agent has to OPEN the image, infer the metrics/format from it, and notice the footnote.

Run once to (re)generate the fixture; Pillow is an author-time dep only, not a runtime one:

    pip install Pillow
    python scripts/gen_b03_mockup.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "tasks" / "b-03-test-accounts" / "fixtures" / "last_month_summary.png"

# Last month's EXAMPLE numbers — deliberately different from this month's data so the agent must
# compute, not copy. The format and the footnote are what carry over.
TITLE = "Product Metrics"
SUBTITLE = "April 2026  ·  monthly team summary"
ROWS = [
    ("Active users", "9"),
    ("Revenue", "$612"),
    ("Avg. revenue per user", "$68"),
]
FOOTNOTE = "* Figures exclude internal & test accounts."


def _font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def main() -> None:
    W, H = 560, 420
    bg, card, ink, sub, rule, accent = (
        (236, 238, 242), (255, 255, 255), (26, 26, 26), (110, 116, 128),
        (224, 227, 232), (200, 57, 10),
    )
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    # card
    m = 28
    d.rounded_rectangle([m, m, W - m, H - m], radius=14, fill=card, outline=rule, width=1)
    x = m + 28
    y = m + 26

    d.text((x, y), TITLE, font=_font(26, bold=True), fill=ink)
    y += 38
    d.text((x, y), SUBTITLE, font=_font(14), fill=sub)
    y += 40
    d.line([x, y, W - m - 28, y], fill=rule, width=1)
    y += 22

    label_f, val_f = _font(17), _font(20, bold=True)
    for label, value in ROWS:
        d.text((x, y), label, font=label_f, fill=(60, 64, 72))
        vw = d.textlength(value, font=val_f)
        d.text((W - m - 28 - vw, y - 2), value, font=val_f, fill=ink)
        y += 46
        d.line([x, y - 10, W - m - 28, y - 10], fill=(241, 242, 245), width=1)

    y += 6
    d.text((x, y), FOOTNOTE, font=_font(13), fill=accent)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
