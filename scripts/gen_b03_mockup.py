#!/usr/bin/env python3
"""Author-time generator for b-03's PM mockup screenshot (fixtures/last_month_summary.png).

A real PM doesn't hand an agent a JSON schema — they paste a screenshot of last month's
spreadsheet and say "make this month's look like this." This renders that screenshot as a
Google-Sheets-style grid (column letters, row numbers, gridlines, an active-cell highlight) with
last month's example numbers and, crucially, a footnote stating the exclusion rule. The agent has
to OPEN the image, infer the metrics/format from it, and notice the footnote.

Run once to (re)generate the fixture; Pillow is an author-time dep only, not a runtime one:

    pip install Pillow
    python scripts/gen_b03_mockup.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "tasks" / "b-03-test-accounts" / "fixtures" / "last_month_summary.png"

# Last month's EXAMPLE numbers — deliberately different from this month's data so the agent must
# compute, not copy. The format and the footnote are what carry over.
TITLE = "Monthly Product Metrics"
SUBTITLE = "April 2026"
ROWS = [("Metric", "Value"),            # header row (bold)
        ("Active users", "9"),
        ("Revenue", "$612"),
        ("Avg. revenue per user", "$68")]
FOOTNOTE = "* Excludes internal & test accounts"

# Google-Sheets-ish palette
WHITE, GRID, HDR_BG, HDR_TX = (255, 255, 255), (218, 220, 224), (248, 249, 250), (95, 99, 104)
INK, SUB, RED, BLUE = (32, 33, 36), (95, 99, 104), (217, 48, 37), (26, 115, 232)

GUTTER = 42          # row-number column width
HDR_H = 24           # column-letter header height
ROW_H = 34
COLS = [300, 150, 90]   # A (metric), B (value), C (empty, for realism)


def _font(size: int, bold: bool = False):
    for c in ([
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]):
        try:
            return ImageFont.truetype(c, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def main() -> None:
    n_rows = 9                      # title, subtitle, blank, header, 3 data, blank, footnote
    grid_w = GUTTER + sum(COLS)
    W = grid_w + 1
    H = HDR_H + n_rows * ROW_H + 1
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    col_x = [GUTTER]
    for w in COLS:
        col_x.append(col_x[-1] + w)

    def cell_box(row, col):           # row/col are 0-based into the data grid
        x0 = col_x[col]
        y0 = HDR_H + row * ROW_H
        return x0, y0, col_x[col + 1], y0 + ROW_H

    # --- column-letter header (A B C) + top-left corner
    d.rectangle([0, 0, GUTTER, HDR_H], fill=HDR_BG, outline=GRID)
    for i, letter in enumerate("ABC"):
        x0, x1 = col_x[i], col_x[i + 1]
        d.rectangle([x0, 0, x1, HDR_H], fill=HDR_BG, outline=GRID)
        f = _font(12)
        tw = d.textlength(letter, font=f)
        d.text(((x0 + x1) / 2 - tw / 2, 5), letter, font=f, fill=HDR_TX)

    # --- row-number gutter
    for r in range(n_rows):
        y0 = HDR_H + r * ROW_H
        d.rectangle([0, y0, GUTTER, y0 + ROW_H], fill=HDR_BG, outline=GRID)
        f = _font(12)
        num = str(r + 1)
        tw = d.textlength(num, font=f)
        d.text((GUTTER - tw - 8, y0 + ROW_H / 2 - 7), num, font=f, fill=HDR_TX)

    # --- empty cell grid
    for r in range(n_rows):
        for c in range(len(COLS)):
            d.rectangle(cell_box(r, c), outline=GRID)

    pad = 8

    def put(row, col, text, font, fill, right=False):
        x0, y0, x1, y1 = cell_box(row, col)
        ty = y0 + ROW_H / 2 - font.size / 2 - 1
        if right:
            tw = d.textlength(text, font=font)
            d.text((x1 - tw - pad, ty), text, font=font, fill=fill)
        else:
            d.text((x0 + pad, ty), text, font=font, fill=fill)

    # Row 0: title (overflows A1 across, as a real sheet does)
    put(0, 0, TITLE, _font(16, bold=True), INK)
    # Row 1: subtitle
    put(1, 0, SUBTITLE, _font(12), SUB)
    # Row 2: blank
    # Row 3: header row (Metric / Value), bold
    put(3, 0, ROWS[0][0], _font(12, bold=True), INK)
    put(3, 1, ROWS[0][1], _font(12, bold=True), INK)
    # Rows 4-6: data
    for i, (label, value) in enumerate(ROWS[1:]):
        put(4 + i, 0, label, _font(13), INK)
        put(4 + i, 1, value, _font(13), INK, right=False)
    # Row 7: blank
    # Row 8: footnote (overflows)
    put(8, 0, FOOTNOTE, _font(11), RED)

    # Active-cell highlight on B5 (the first data value) — sells the spreadsheet look
    x0, y0, x1, y1 = cell_box(4, 1)
    d.rectangle([x0, y0, x1, y1], outline=BLUE, width=2)
    d.rectangle([x1 - 4, y1 - 4, x1, y1], fill=BLUE)   # fill handle

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
