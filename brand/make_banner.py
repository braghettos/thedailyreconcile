"""Builds the LinkedIn page cover from a rendered issue: the masthead, not a blind slice.

    python3 brand/make_banner.py <issue.pdf> [out.png]

A 1128x191 cover is 5.9:1, and any horizontal cut through the front page at that ratio runs
through a line of type. So the masthead block (ears, nameplate, folio, the Inside-today strip)
is taken whole and centred on a white canvas instead.
"""
import os, sys
import pymupdf

TW, TH = 2256, 382                       # 2x LinkedIn page cover, downscaled by them
CROP = pymupdf.Rect(18, 18, 577, 150)    # the masthead block on an A4 front page


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip()); sys.exit(2)
    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "brand/linkedin-banner-2256x382.png"
    src = pymupdf.open(pdf)[0]
    scale = min(TW / CROP.width, TH / CROP.height)
    w, h = CROP.width * scale, CROP.height * scale
    pix = src.get_pixmap(dpi=int(72 * scale), clip=CROP)
    doc = pymupdf.open()
    page = doc.new_page(width=TW, height=TH)
    page.draw_rect(pymupdf.Rect(0, 0, TW, TH), color=None, fill=(1, 1, 1))
    page.insert_image(pymupdf.Rect((TW - w) / 2, (TH - h) / 2, (TW + w) / 2, (TH + h) / 2), pixmap=pix)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    page.get_pixmap(dpi=72, alpha=False).save(out)
    print(f"{out}  {TW}x{TH}")


if __name__ == "__main__":
    main()
