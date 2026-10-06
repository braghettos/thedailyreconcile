"""Composes the LinkedIn page cover: the paper as texture, the nameplate set over it.

    python3 brand/make_cover.py <issue.pdf> [out.png] [WIDTHxHEIGHT]

A crop of the masthead looks like a scanned document on LinkedIn - black type floating in a
white interface, with the page logo dropped over one corner. This sets a row of the actual
pages across the full width instead, washed back so it reads as newsprint rather than as
something to be read, and runs a cream band across the middle carrying the nameplate.

The pages are set taller than the banner and pushed up, so the strips that show are story
columns, the factbox and the word search rather than a row of repeated mastheads competing with
the real one. Each tile is offset differently so the repeat does not line up.

LinkedIn documents the cover as 1512x256, minimum and recommended, PNG or JPEG, 3 MB maximum
(linkedin.com/help/linkedin/answer/a563312). That is 5.906:1, not the 6:1 most size guides
repeat. The default here is twice the documented size, at the documented ratio.

The page logo is overlaid on the lower left and the edges crop on a phone, so the nameplate
sits centred and nothing load-bearing goes near a corner.
"""
import os
import re
import sys

import pymupdf

W, H = 3024, 512
PAPER, INK, ACCENT = (0.965, 0.941, 0.882), (0.067, 0.067, 0.067), (0.600, 0.090, 0.090)
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "fonts")
MOTTO = "All the cloud native news that’s fit to reconcile"
NAMEPLATE = "The Daily Reconcile."
TOPICS = "KUBERNETES  ·  PLATFORM ENGINEERING  ·  GITOPS  ·  CLOUD NATIVE"
OFFSETS = (0.30, 0.46, 0.22, 0.54, 0.36, 0.26)      # per-tile, so the tiling does not repeat


def font(name, alias):
    path = os.path.join(FONTS, name)
    f = pymupdf.Font(fontfile=path)
    f.path, f.alias = path, alias
    return f


def main():
    global W, H
    args = [a for a in sys.argv[1:]]
    size = next((a for a in args if re.fullmatch(r"\d+x\d+", a)), "")
    if size:
        W, H = (int(v) for v in size.split("x"))
    rest = [a for a in args if a != size]
    if not rest:
        print(__doc__.strip()); sys.exit(2)
    pdf = rest[0]
    out = rest[1] if len(rest) > 1 else f"brand/linkedin-cover-{W}x{H}.png"
    s = H / 512.0                                   # geometry is specified at 512 high

    doc = pymupdf.open(pdf)
    o = pymupdf.open()
    page = o.new_page(width=W, height=H)
    page.draw_rect(pymupdf.Rect(0, 0, W, H), color=None, fill=PAPER)

    tile_h = H * 1.75
    x, i = -60 * s, 0
    while x < W:
        src = doc[i % doc.page_count]
        scale = tile_h / src.rect.height
        w = src.rect.width * scale
        top = -tile_h * OFFSETS[i % len(OFFSETS)]
        pix = src.get_pixmap(dpi=int(72 * scale))
        page.insert_image(pymupdf.Rect(x, top, x + w, top + tile_h), pixmap=pix)
        x += w + 18 * s
        i += 1

    page.draw_rect(pymupdf.Rect(0, 0, W, H), color=None, fill=PAPER, fill_opacity=0.55)

    bt, bb = H * 0.185, H * 0.825
    page.draw_rect(pymupdf.Rect(0, bt, W, bb), color=None, fill=PAPER, fill_opacity=0.97)
    for y, t in ((bt - 13 * s, 10 * s), (bt - 1 * s, 3 * s),
                 (bb + 1 * s, 3 * s), (bb + 10 * s, 10 * s)):
        page.draw_rect(pymupdf.Rect(0, y, W, y + t), color=None, fill=INK)

    serif_b, serif_i, sans_b = (font("LiberationSerif-Bold.ttf", "NAME"),
                                font("Lora-Italic.ttf", "MOTTO"),
                                font("Carlito-Bold.ttf", "TOPIC"))

    def fit(text, f, size_, baseline, colour, spacing=0.0):
        w = f.text_length(text, fontsize=size_) + spacing * (len(text) - 1)
        xx = W / 2 - w / 2
        if not spacing:
            page.insert_text((xx, baseline), text, fontname=f.alias, fontfile=f.path,
                             fontsize=size_, color=colour)
            return
        for ch in text:
            page.insert_text((xx, baseline), ch, fontname=f.alias, fontfile=f.path,
                             fontsize=size_, color=colour)
            xx += f.text_length(ch, fontsize=size_) + spacing

    fit(MOTTO, serif_i, 33 * s, 178 * s, INK)
    fit(NAMEPLATE, serif_b, 148 * s, 312 * s, INK)
    fit(TOPICS, sans_b, 25 * s, 372 * s, ACCENT, spacing=2.8 * s)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    page.get_pixmap(dpi=72, alpha=False).save(out)
    print(f"{out}  {W}x{H}  {os.path.getsize(out) // 1024} KB")


if __name__ == "__main__":
    main()
