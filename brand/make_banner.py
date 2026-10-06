"""Builds the LinkedIn page cover from a rendered issue: the masthead, not a blind slice.

    python3 brand/make_banner.py <issue.pdf> [out.png] [WIDTHxHEIGHT]

LinkedIn documents the page cover as 1512x256, minimum and recommended, max 3 MB
(linkedin.com/help/linkedin/answer/a563312). That is 5.906:1, not the 6:1 quoted by most
third-party size guides. The default here is 3024x512: the documented ratio exactly, at twice
the size, so it stays sharp on a high-DPI screen and still lands well under the size limit.

Any horizontal cut through the front page at that ratio runs through a line of type, so the
masthead block (ears, nameplate, folio, the Inside-today strip) is taken whole and centred on a
white canvas instead. The crop is narrower than 6:1, so it is scaled to the full height and the
remaining width stays white; that is the design, not padding to be trimmed.
"""
import os, re, sys
import pymupdf

TW, TH = 3024, 512                       # 2x LinkedIn's documented 1512x256 cover (5.906:1)
CROP = pymupdf.Rect(18, 18, 577, 150)    # the masthead block on an A4 front page


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip()); sys.exit(2)
    pdf = sys.argv[1]
    global TW, TH
    size = next((a for a in sys.argv[2:] if re.fullmatch(r"\d+x\d+", a)), "")
    if size:
        TW, TH = (int(v) for v in size.split("x"))
    rest = [a for a in sys.argv[2:] if a != size]
    out = rest[0] if rest else f"brand/linkedin-banner-{TW}x{TH}.png"
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
