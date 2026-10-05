"""Renders the brand assets from brand.py: print mark, LinkedIn avatar, GitHub social preview.

    python3 make_brand_assets.py [outdir]     (default: ./brand)
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import pymupdf
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import brand          # noqa: E402  (after sys.path is set)

CREAM = Color(0.965, 0.94, 0.88)          # the paper's own tint
RED = Color(0.6, 0.09, 0.09)
CREAM_HEX, RED_HEX = "#F6F0E1", "#991717"
FONTS = os.path.join(ROOT, "engine", "fonts")
TITLE = "The Daily Reconcile."
TAG = "Kubernetes, platform engineering and GitOps - written and printed every morning"


def _fonts():
    pdfmetrics.registerFont(TTFont("Display", os.path.join(FONTS, "LiberationSerif-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Sans", os.path.join(FONTS, "Carlito-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Sans-B", os.path.join(FONTS, "Carlito-Bold.ttf")))


def _raster(draw_fn, w, h, path, scale=1):
    """draw at w x h points, rasterise to exactly (w*scale) x (h*scale) pixels"""
    buf = path + ".tmp.pdf"
    c = canvas.Canvas(buf, pagesize=(w, h))
    draw_fn(c)
    c.showPage(); c.save()
    pymupdf.open(buf)[0].get_pixmap(dpi=int(72 * scale), alpha=False).save(path)
    os.remove(buf)
    print("  ", path)


def avatar(px):
    """square page/profile picture: the seal on the paper's cream"""
    def d(c):
        c.setFillColor(CREAM); c.rect(0, 0, 512, 512, stroke=0, fill=1)
        brand.draw(c, 256, 256, 186)
    return lambda path: _raster(d, 512, 512, path, scale=px / 512)


def social(path):
    """GitHub repo social preview, 1280x640: a masthead"""
    def d(c):
        W, H = 1280, 640
        c.setFillColor(CREAM); c.rect(0, 0, W, H, stroke=0, fill=1)
        c.setStrokeColor(black)
        for y, lw in ((H - 40, 3), (H - 48, 1), (40, 3), (48, 1)):
            c.setLineWidth(lw); c.line(70, y, W - 70, y)
        brand.draw(c, 212, 330, 116)
        x = 372
        c.setFillColor(RED); c.setFont("Sans-B", 19)
        c.drawString(x, 430, "DAILY EDITION  ·  TWO PAGES  ·  ONE SHEET", charSpace=1.6)
        c.setFillColor(black); c.setFont("Display", 76)
        c.drawString(x, 332, TITLE)
        c.setLineWidth(1); c.line(x, 300, W - 110, 300)
        c.setFont("Sans", 23)
        c.drawString(x, 262, TAG)
        c.setFont("Sans-B", 18); c.setFillColor(RED)
        c.drawString(x, 214, "Researched, written and laid out by Claude Code", charSpace=.6)
    _raster(d, 1280, 640, path)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "brand"
    os.makedirs(out, exist_ok=True)
    _fonts()
    print("brand assets ->", out)
    open(os.path.join(out, "mark.svg"), "w").write(brand.svg(512))
    print("   mark.svg")
    open(os.path.join(out, "mark-on-cream.svg"), "w").write(brand.svg(512, bg=CREAM_HEX))
    print("   mark-on-cream.svg")
    for px in (1024, 400, 128):
        avatar(px)(os.path.join(out, f"avatar-{px}.png"))
    social(os.path.join(out, "social-preview-1280x640.png"))


if __name__ == "__main__":
    main()
