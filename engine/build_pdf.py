#!/usr/bin/env python3
"""The Daily Reconcile: lays out content.json as a two-page A4 newspaper (front and back).

Page 1: nameplate with ears, folio line, "Inside today" teasers, lead story with drop cap and
        factbox, two-column second stories, single-column stories, cartoon and "Dates to watch".
Page 2: running head, news in brief on four columns, word search with upside-down solution.
Body text is scaled automatically so that everything fits without truncation; a pull quote is
used as a filler where a column would otherwise end with a hole.
"""
import datetime
import io
import json
import random
import sys

from reportlab.graphics import renderPDF
from reportlab.lib.colors import Color, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4

import brand
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Spacer
from reportlab.platypus.flowables import Flowable, HRFlowable, ImageAndFlowables
from svglib.svglib import svg2rlg

# ------------------------------------------------------------------ fonts, colours, grid
LIB = "/usr/share/fonts/truetype/liberation/"
CX = "/usr/share/fonts/truetype/crosextra/"
DJ = "/usr/share/fonts/truetype/dejavu/"
import os
LORA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"


def ensure_lora(src="/usr/share/fonts/truetype/google-fonts/"):
    """Builds static Lora instances (OFL, Google Fonts) from the variable fonts, with distinct names."""
    styles_ = {"Regular": ("Lora-Variable.ttf", 400, "Regular"), "Bold": ("Lora-Variable.ttf", 700, "Bold"),
               "Italic": ("Lora-Italic-Variable.ttf", 400, "Italic"),
               "BoldItalic": ("Lora-Italic-Variable.ttf", 700, "Bold Italic")}
    if all(os.path.exists(f"{LORA}Lora-{k}.ttf") for k in styles_):
        return
    from fontTools.ttLib import TTFont as FTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    os.makedirs(LORA, exist_ok=True)
    for key, (f, wght, sub) in styles_.items():
        inst = instantiateVariableFont(FTFont(src + f), {"wght": wght}, updateFontNames=False)
        nm = inst["name"]
        for nid in (1, 2, 3, 4, 6, 16, 17):
            nm.removeNames(nameID=nid)
        for nid, val in ((1, "Lora"), (2, sub), (3, f"Lora-{key}-static"), (4, f"Lora {sub}"), (6, f"Lora-{key}")):
            nm.setName(val, nid, 3, 1, 0x409)
        inst.save(f"{LORA}Lora-{key}.ttf")


ensure_lora()


def _font(path):
    """Uses a copy bundled in fonts/ when present (e.g. on macOS), else the system path."""
    local = LORA + os.path.basename(path) + ".ttf"
    return local if os.path.exists(local) else path + ".ttf"


for _n, _p in [("Serif", LORA + "Lora-Regular"), ("Serif-B", LORA + "Lora-Bold"),
               ("Serif-I", LORA + "Lora-Italic"), ("Serif-BI", LORA + "Lora-BoldItalic"),
               ("Sans", CX + "Carlito-Regular"), ("Sans-B", CX + "Carlito-Bold"),
               ("Sans-I", CX + "Carlito-Italic"), ("Sans-BI", CX + "Carlito-BoldItalic"),
               ("Mono-B", DJ + "DejaVuSansMono-Bold"), ("Display", LIB + "LiberationSerif-Bold"),
               ("Sym", DJ + "DejaVuSans")]:
    pdfmetrics.registerFont(TTFont(_n, _font(_p)))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B", italic="Serif-I", boldItalic="Serif-BI")
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans-I", boldItalic="Sans-BI")

W, H = A4
M = 28                      # page margin
G = 12                      # gutter
NCOL = 4
CW = (W - 2 * M - G * (NCOL - 1)) / NCOL      # one grid column
RED = Color(0.6, 0.09, 0.09)                  # single accent colour, prints as dark grey in B/W
RED_HEX = "#991717"
TINT = Color(0.93, 0.93, 0.93)
CHAMPAGNE = Color(0.965, 0.94, 0.88)       # WSJ-style tint for the index strip
GRAY = Color(0.33, 0.33, 0.33)
HAIR = Color(0.55, 0.55, 0.55)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
HY = dict(hyphenationLang="en_US", embeddedHyphenation=0, uriWasteReduce=0.3)


def span(n):
    return n * CW + (n - 1) * G


def colx(i):
    return M + i * (CW + G)


def styles(s):
    body = dict(fontName="Serif", fontSize=8.5 * s, leading=11.4 * s, alignment=TA_LEFT, **HY)
    return {
        "kicker": ParagraphStyle("k", fontName="Sans-B", fontSize=7.2 * s, leading=8.6 * s, textColor=RED, spaceAfter=1.5),
        "h_lead": ParagraphStyle("hl", fontName="Serif-B", fontSize=27 * s, leading=30 * s, spaceAfter=4),
        "h_wide": ParagraphStyle("hw", fontName="Serif-B", fontSize=16 * s, leading=18 * s, spaceAfter=3),
        "h_col": ParagraphStyle("hc", fontName="Serif-B", fontSize=12.5 * s, leading=14.2 * s, spaceAfter=2.5),
        "h_brief": ParagraphStyle("hb", fontName="Serif-B", fontSize=10 * s, leading=11.6 * s, spaceAfter=2.5),
        "deck_lead": ParagraphStyle("dl", fontName="Serif-I", fontSize=11.5 * s, leading=14.5 * s, spaceAfter=4),
        "deck": ParagraphStyle("d", fontName="Serif-I", fontSize=9.4 * s, leading=11.8 * s, spaceAfter=3),
        "byline": ParagraphStyle("by", fontName="Sans-B", fontSize=6.6 * s, leading=8 * s, textColor=GRAY, spaceAfter=5),
        "body": ParagraphStyle("b", firstLineIndent=0, **body),
        "body_ind": ParagraphStyle("bi", firstLineIndent=9 * s, **body),
        "link": ParagraphStyle("l", fontName="Sans-I", fontSize=6.8 * s, leading=8.1 * s, textColor=GRAY,
                               spaceBefore=2.5, splitLongWords=1),
    }


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def show_url(u):
    return u.split("://", 1)[-1].rstrip("/")


def links_markup(urls):
    return "<br/>".join(f"<link href='{esc(u)}' color='{RED_HEX}'>{esc(show_url(u))}</link>" for u in urls)


# ------------------------------------------------------------------ flowables
class DropCap(Flowable):
    """three-line drop cap aligned to the first and third baselines of the paragraph"""

    def __init__(self, letter, st):
        super().__init__()
        size, lead = st.fontSize, st.leading
        self.letter = letter
        self.fs = 2 * lead / 0.7 + size * 0.98
        self.base = 2 * lead + size
        self.w = pdfmetrics.stringWidth(letter, "Serif-B", self.fs) + 3
        self.h = self.base + 2

    def wrap(self, aW, aH):
        return self.w, self.h

    def _restrictSize(self, aW, aH):          # required by ImageAndFlowables
        return self.w, self.h

    def draw(self):
        self.canv.setFont("Serif-B", self.fs)
        self.canv.setFillColor(RED)
        self.canv.drawString(0, self.h - self.base, self.letter)
        self.canv.setFillColor(black)


def body_flow(it, st, kind, dropcap=False):
    texts = it["text"] if isinstance(it["text"], list) else [it["text"]]
    out = []
    for i, t in enumerate(texts):
        style = st["body"] if i == 0 else st["body_ind"]
        if i == 0 and dropcap and t[:1].isalpha():
            out.append(ImageAndFlowables(DropCap(t[0], style), [Paragraph(esc(t[1:]), style)],
                                         imageLeftPadding=0, imageRightPadding=2.5, imageSide="left"))
        else:
            out.append(Paragraph(esc(t), style))
    urls = it.get("urls") or ([it["url"]] if it.get("url") else [])
    if kind == "brief":
        src = "— " + esc(it.get("source", "")) + ("<br/>" if urls else "")
        out.append(Paragraph(src + links_markup(urls), st["link"]))
    elif urls:
        out.append(Paragraph("Full story → " + links_markup(urls), st["link"]))
    return out


def head_flow(it, st, kind):
    hs = {"lead": "h_lead", "wide": "h_wide", "col": "h_col", "brief": "h_brief"}[kind]
    out = []
    if it.get("kicker"):
        out.append(Paragraph(esc(it["kicker"]).upper(), st["kicker"]))
    out.append(Paragraph(esc(it["headline"]), st[hs]))
    if it.get("deck") and kind != "brief":
        out.append(Paragraph(esc(it["deck"]), st["deck_lead" if kind == "lead" else "deck"]))
    if kind != "brief" and it.get("source"):
        out.append(Paragraph("COMPILED FROM " + esc(it["source"]).upper(), st["byline"]))
    return out


def height(flowables, w):
    return sum(f.wrap(w, 9999)[1] + f.getSpaceBefore() + f.getSpaceAfter() for f in flowables)


# ------------------------------------------------------------------ layout engine
def make_cols(x, ytop, w, h, n, gap=G):
    cw = (w - gap * (n - 1)) / n
    return [Frame(x + i * (cw + gap), ytop - h, cw, h, leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0) for i in range(n)]


def scratch():
    return canvas.Canvas(io.BytesIO(), pagesize=A4)


def flow(frames, blocks, c, sep=True, min_lines=3):
    """Pours (head, body) blocks into the frames in order. Heads never sit orphaned at the
    bottom of a column. Returns True if everything fits."""
    fi = 0
    for bi, (head, body) in enumerate(blocks):
        if fi >= len(frames):
            return False
        lead = 11.4
        for f in body:
            if isinstance(f, Paragraph):
                lead = f.style.leading
                break
        need = height(head, frames[0]._aW) + min_lines * lead
        while fi < len(frames) and (frames[fi]._y - frames[fi]._y1p) < need:
            fi += 1
        items = head + body
        if sep and bi < len(blocks) - 1:
            items.append(HRFlowable(width="100%", thickness=.5, color=black, spaceBefore=5, spaceAfter=7))
        while items:
            if fi >= len(frames):
                return False
            f, fr = items.pop(0), frames[fi]
            if fr.add(f, c):
                continue
            parts = fr.split(f, c)
            if parts and len(parts) > 1 and fr.add(parts[0], c):
                items[0:0] = parts[1:]
            elif not isinstance(f, HRFlowable):
                items.insert(0, f)
            fi += 1
    return True


def balanced(x, ytop, w, n, make_body, c, draw):
    """smallest column height that holds the body on n columns; draws it if asked"""
    lo, hi = 6, 900
    if not flow(make_cols(x, ytop, w, hi, n), [([], make_body())], scratch(), sep=False, min_lines=0):
        return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if flow(make_cols(x, ytop, w, mid, n), [([], make_body())], scratch(), sep=False, min_lines=0):
            hi = mid
        else:
            lo = mid
    if draw:
        flow(make_cols(x, ytop, w, hi, n), [([], make_body())], c, sep=False, min_lines=0)
        for i in range(1, n):
            cw = (w - G * (n - 1)) / n
            xl = x + i * cw + (i - .5) * G
            vline(c, xl, ytop, ytop - hi, .3, HAIR)
    return hi


def stack(c, x, ytop, w, n, items, st, kind, draw):
    """stories with a headline across the full width and the body balanced on n columns"""
    y = ytop
    for i, it in enumerate(items):
        head = head_flow(it, st, kind)
        hh = height(head, w)
        if draw:
            Frame(x, y - hh - 2, w, hh + 2, leftPadding=0, rightPadding=0, topPadding=0,
                  bottomPadding=0).addFromList(head, c)
        y -= hh
        bh = balanced(x, y, w, n, lambda it=it: body_flow(it, st, kind), c, draw)
        if bh is None:
            return None
        y -= bh
        if i < len(items) - 1:
            if draw:
                hline(c, x, x + w, y - 6, .5)
            y -= 14
    return y


# ------------------------------------------------------------------ drawing helpers
def hline(c, x1, x2, y, w=.5, col=black):
    c.setStrokeColor(col)
    c.setLineWidth(w)
    c.line(x1, y, x2, y)


def vline(c, x, y1, y2, w=.3, col=HAIR):
    c.setStrokeColor(col)
    c.setLineWidth(w)
    c.line(x, y1, x, y2)


def section_head(c, x, y, w, text, draw=True):
    """newspaper section label: heavy rule, small-caps label, hairline"""
    if draw:
        hline(c, x, x + w, y, 2.2)
        c.setFont("Sans-B", 8.2)
        c.setFillColor(black)
        c.drawString(x, y - 10.5, text.upper())
        hline(c, x, x + w, y - 14, .4)
    return y - 21


def draw_para(c, text, style, x, ytop, w):
    p = Paragraph(text, style)
    _, h = p.wrap(w, 999)
    p.drawOn(c, x, ytop - h)
    return h


# ------------------------------------------------------------------ nameplate, running head, footer
def countdown(content, d):
    """next CFP deadline from the dates list, for the right ear"""
    best = None
    for dd in content.get("dates", []):
        if dd.get("tag", "").upper() == "CFP" and dd.get("date"):
            n = (datetime.date.fromisoformat(dd["date"]) - d).days
            if n >= 0 and (best is None or n < best[0]):
                best = (n, dd.get("short", dd["what"]))
    return best


def nameplate(c, content, d, draw=True):
    """NYT-style ears around a centred nameplate, folio line between thin and double rules"""
    y = H - M
    ear_w, ear_h = 96, 44
    folio_rule = y - ear_h - 8
    if not draw:
        return folio_rule - 24
    # left ear: motto
    c.setStrokeColor(black)
    c.setLineWidth(.5)
    c.rect(M, y - ear_h, ear_w, ear_h)
    p = Paragraph(esc(content.get("motto", "")),
                  ParagraphStyle("motto", fontName="Serif-I", fontSize=8.4, leading=10.2, alignment=TA_CENTER))
    _, ph = p.wrap(ear_w - 12, ear_h)
    p.drawOn(c, M + 6, y - ear_h / 2 - ph / 2)
    # right ear: countdown to the next CFP
    ex = W - M - ear_w
    c.rect(ex, y - ear_h, ear_w, ear_h)
    cd = countdown(content, d)
    if cd:
        n, what = cd
        c.setFont("Sans-B", 6.3)
        c.setFillColor(RED)
        c.drawCentredString(ex + ear_w / 2, y - 10, "COUNTDOWN", charSpace=.8)
        c.setFillColor(black)
        c.setFont("Serif-B", 14)
        c.drawCentredString(ex + ear_w / 2, y - 25, f"{n} day{'s' if n != 1 else ''}")
        c.setFont("Sans", 6.6)
        c.drawCentredString(ex + ear_w / 2, y - 36, f"to the {what}")
    # nameplate: the mark, then the wordmark, the pair centred between the ears
    title = content.get("title", "The Daily Reconcile").rstrip(".") + "."
    avail = W - 2 * M - 2 * ear_w - 30
    mark_r, mark_gap = 17, 13
    size = 54
    while pdfmetrics.stringWidth(title, "Display", size) > avail - 2 * mark_r - mark_gap:
        size -= .5
    base = y - ear_h + 6
    tw = pdfmetrics.stringWidth(title, "Display", size)
    x0 = W / 2 - (2 * mark_r + mark_gap + tw) / 2
    brand.draw(c, x0 + mark_r, base + size * .34, mark_r)
    c.setFillColor(black)
    c.setFont("Display", size)
    c.drawString(x0 + 2 * mark_r + mark_gap, base, title)
    # folio line
    hline(c, M, W - M, folio_rule, .6)
    fy = folio_rule - 9
    datestr = f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}".upper()
    c.setFont("Sans-B", 7.4)
    c.drawString(M, fy, f"VOL. I  ·  NO. {d.timetuple().tm_yday}", charSpace=.5)
    c.drawCentredString(W / 2, fy, datestr, charSpace=.8)
    c.drawRightString(W - M, fy, content.get("edition", "").upper(), charSpace=.5)
    hline(c, M, W - M, fy - 5, 2)
    hline(c, M, W - M, fy - 8, .5)
    return folio_rule - 24


def running_head(c, content, d, page, draw=True):
    y = H - M
    if draw:
        title = content.get("title", "The Daily Reconcile").rstrip(".") + "."
        brand.draw(c, M + 8, y - 7.5, 8)
        c.setFont("Display", 15)
        c.setFillColor(black)
        c.drawString(M + 21, y - 12, title)
        c.setFont("Sans-B", 7.4)
        datestr = f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}".upper()
        c.drawCentredString(W / 2, y - 11, datestr, charSpace=.8)
        c.drawRightString(W - M, y - 11, f"PAGE {page}", charSpace=.5)
        hline(c, M, W - M, y - 17, 2)
        hline(c, M, W - M, y - 20, .5)
    return y - 28


def footer(c, content):
    hline(c, M, W - M, M - 5, .5)
    c.setFont("Sans", 6.4)
    c.setFillColor(GRAY)
    c.drawString(M, M - 13, "Sources: " + content.get("sources_line", ""))
    c.drawRightString(W - M, M - 13, "Curated and summarised by Claude · always check the original sources")
    c.setFillColor(black)


# ------------------------------------------------------------------ page 1 components
def teasers(c, content, y, draw=True):
    """'Inside today' index strip with champagne tint and diamond bullets"""
    picks = content.get("_teaser_items") or [content["briefs"][i] for i in content.get("teasers", [0, 1, 2])][:3]
    label_w = 52
    cw = (W - 2 * M - label_w - 8 - 2 * G) / 3
    hs = ParagraphStyle("t", fontName="Serif-B", fontSize=9, leading=11)
    paras = []
    for it in picks:
        p = Paragraph(f"<font name='Sym' size='6.5' color='{RED_HEX}'>◆</font> "
                      f"<font name='Sans-B' size='6.6' color='{RED_HEX}'>{esc(it['kicker']).upper()}</font><br/>"
                      f"{esc(it['headline'])} <font name='Sans-B' size='6.8' color='#555555'>P.2</font>", hs)
        paras.append((p, p.wrap(cw - 8, 200)[1]))
    bar_h = max(h for _, h in paras) + 12
    if draw:
        c.setFillColor(CHAMPAGNE)
        c.rect(M, y - bar_h, W - 2 * M, bar_h, fill=1, stroke=0)
        c.setFillColor(black)
        c.setFont("Sans-B", 7.6)
        c.drawString(M + 7, y - bar_h / 2 + 2.5, "INSIDE", charSpace=.8)
        c.drawString(M + 7, y - bar_h / 2 - 6.5, "TODAY", charSpace=.8)
        for i, (p, ph) in enumerate(paras):
            x = M + label_w + 8 + i * (cw + G)
            vline(c, x - G / 2 - 1, y - 5, y - bar_h + 5, .5, HAIR)
            p.drawOn(c, x, y - 6 - ph)
    return y - bar_h - 10


def factbox(c, fb, x, ytop, w, draw=True):
    """'by the numbers' graphic, in place of a photo"""
    y = section_head(c, x, ytop, w, fb["title"], draw)
    vmax = max(i["value"] for i in fb["items"]) or 1
    for it in fb["items"]:
        if draw:
            c.setFont("Serif-B", 21)
            c.setFillColor(black)
            c.drawString(x, y - 18, str(it["value"]))
            c.setFont("Sans-B", 7.4)
            c.drawString(x + 32, y - 9, it["label"].upper())
            bw = (w - 32) * it["value"] / vmax
            c.setFillColor(RED)
            c.rect(x + 32, y - 19, max(bw, 1.5), 6.5, fill=1, stroke=0)
            c.setFillColor(black)
        y -= 26
    if fb.get("note"):
        nh = Paragraph(esc(fb["note"]), ParagraphStyle("fn", fontName="Sans-I", fontSize=7, leading=8.4, textColor=GRAY))
        _, h = nh.wrap(w, 200)
        if draw:
            hline(c, x, x + w, y - 1, .4)
            nh.drawOn(c, x, y - 5 - h)
        y -= h + 8
    return ytop - y


def pullquote(c, pq, x, ytop, w, draw=True):
    wide = w > CW + 1
    st = ParagraphStyle("pq", fontName="Serif-BI", fontSize=13.5 if wide else 11.5,
                        leading=17 if wide else 14.5, alignment=TA_LEFT)
    at = ParagraphStyle("pa", fontName="Sans-B", fontSize=7, leading=8.5, textColor=GRAY)
    p1 = Paragraph(f"<font color='{RED_HEX}'>“</font>{esc(pq['text'])}<font color='{RED_HEX}'>”</font>", st)
    p2 = Paragraph("— " + esc(pq["attribution"]).upper(), at)
    _, h1 = p1.wrap(w, 999)
    _, h2 = p2.wrap(w, 999)
    total = h1 + h2 + 22
    if draw:
        hline(c, x, x + w, ytop - 2, 2.2, RED)
        p1.drawOn(c, x, ytop - 9 - h1)
        p2.drawOn(c, x, ytop - 13 - h1 - h2)
        hline(c, x, x + w, ytop - total + 2, .4)
    return total


def statbox(c, sb, x, ytop, w, draw=True):
    """compact 'in numbers' box used as a filler"""
    y = section_head(c, x, ytop, w, sb["title"], draw)
    for it in sb["items"]:
        if draw:
            c.setFont("Serif-B", 17)
            c.setFillColor(RED)
            c.drawString(x, y - 14, it["value"])
            c.setFillColor(black)
            p = Paragraph(esc(it["label"]), ParagraphStyle("sbl", fontName="Sans", fontSize=7.4, leading=8.4))
            vw = pdfmetrics.stringWidth(it["value"], "Serif-B", 17) + 6
            _, ph = p.wrap(w - vw, 40)
            p.drawOn(c, x + vw, y - 8 - ph / 2)
        y -= 23
    return ytop - y + 2


def cartoon(c, ct, x, ytop, w, draw=True):
    y = section_head(c, x, ytop, w, "Cartoon of the day", draw)
    vh = w * 0.74
    if draw:
        c.setStrokeColor(black)
        c.setLineWidth(.8)
        c.rect(x, y - vh, w, vh, fill=0, stroke=1)
        dr = svg2rlg(io.StringIO(ct["svg"]))
        sc = min((w - 6) / dr.width, (vh - 6) / dr.height)
        dr.scale(sc, sc)
        renderPDF.draw(dr, c, x + (w - dr.width * sc) / 2, y - vh + (vh - dr.height * sc) / 2)
        c.setFont("Sans-I", 6)
        c.setFillColor(GRAY)
        c.drawRightString(x + w, y - vh - 7, "Drawing: Claude")
        c.setFillColor(black)
    y -= vh + 10
    cap = Paragraph(esc(ct["caption"]), ParagraphStyle("cap", fontName="Serif-BI", fontSize=10, leading=12, alignment=TA_CENTER))
    _, h = cap.wrap(w, 999)
    if draw:
        cap.drawOn(c, x, y - h)
    y -= h + 5
    ex = Paragraph(f"<font name='Sans-B' color='{RED_HEX}'>WHY IT'S FUNNY</font>  " + esc(ct["explanation"]),
                   ParagraphStyle("ex", fontName="Sans", fontSize=7.6, leading=9.2, textColor=GRAY, alignment=TA_JUSTIFY, **HY))
    _, h = ex.wrap(w, 999)
    if draw:
        ex.drawOn(c, x, y - h)
    y -= h
    return ytop - y


def dates_box(c, dates, x, ytop, bottom, w):
    """events (online or in person) and CFP deadlines"""
    bh = ytop - bottom
    if bh < 60:
        return
    c.setFillColor(TINT)
    c.rect(x, bottom, w, bh, fill=1, stroke=0)
    hline(c, x, x + w, ytop, 2.2)
    c.setFillColor(black)
    c.setFont("Sans-B", 8.2)
    c.drawString(x + 6, ytop - 12, "DATES TO WATCH")
    c.setFont("Sans-I", 6.4)
    c.setFillColor(GRAY)
    c.drawString(x + 6, ytop - 20, "Events and calls for papers")
    y0 = ytop - 28
    st_dd = ParagraphStyle("dd", fontName="Sans", fontSize=7.6, leading=9, **HY)
    entries, used = [], 0
    for dd in dates:                            # how many entries fit
        p = Paragraph(esc(dd["what"]), st_dd)
        _, ph = p.wrap(w - 12, 200)
        h = 13 + ph
        if used + h + (6 if entries else 0) > y0 - bottom - 6:
            break
        used += h + (6 if entries else 0)
        entries.append((dd, p, ph))
    gap = 6
    if len(entries) > 1:                        # spread the leftover space between entries
        gap += min(14, (y0 - bottom - 6 - used) / (len(entries) - 1))
    y = y0
    for dd, p, ph in entries:
        c.setFillColor(black)
        c.setFont("Serif-B", 10.5)
        c.drawString(x + 6, y - 10, dd["when"])
        tag = dd.get("tag", "").upper()
        if tag:
            tw = pdfmetrics.stringWidth(tag, "Sans-B", 5.8) + 6
            tx = x + w - 6 - tw
            if tag == "CFP":
                c.setFillColor(RED)
                c.rect(tx, y - 10.5, tw, 8.5, fill=1, stroke=0)
                c.setFillColor(white)
            else:
                c.setStrokeColor(black)
                c.setLineWidth(.5)
                c.setFillColor(white)
                c.rect(tx, y - 10.5, tw, 8.5, fill=1, stroke=1)
                c.setFillColor(black)
            c.setFont("Sans-B", 5.8)
            c.drawCentredString(tx + tw / 2, y - 8.3, tag)
            c.setFillColor(black)
        p.drawOn(c, x + 6, y - 13 - ph)
        y -= 13 + ph + gap


# ------------------------------------------------------------------ jump engine
JUMP_H = 11


def pour(frames, blocks, c, sep=True, min_lines=3):
    """Pours blocks into frames. Returns (cut_index, leftover_items): cut_index is None when all
    blocks fit; otherwise blocks[cut_index] was cut and leftover_items is what remains of it
    (blocks after cut_index were not started)."""
    fi = 0
    for bi, (head, body) in enumerate(blocks):
        lead = next((f.style.leading for f in body if isinstance(f, Paragraph)), 11.4)
        if fi < len(frames):
            need = height(head, frames[0]._aW) + min_lines * lead
            while fi < len(frames) and (frames[fi]._y - frames[fi]._y1p) < need:
                fi += 1
        if fi >= len(frames):
            return bi, None                          # block not started at all
        items = head + body
        if sep and bi < len(blocks) - 1:
            items.append(HRFlowable(width="100%", thickness=.5, color=black, spaceBefore=5, spaceAfter=7))
        started = False
        while items:
            if fi >= len(frames):
                rest = [f for f in items if not isinstance(f, HRFlowable)]
                return bi, (rest if started else None)
            f, fr = items.pop(0), frames[fi]
            if fr.add(f, c):
                started = True
                continue
            parts = fr.split(f, c)
            if parts and len(parts) > 1 and fr.add(parts[0], c):
                started = True
                items[0:0] = parts[1:]
            elif not isinstance(f, HRFlowable):
                items.insert(0, f)
            fi += 1
    return None, None


def pour_with_jump(make_frames, make_blocks, c, draw):
    """Pours stories; if they overflow, reserves a line and prints 'Continued on page 2'.
    Returns (cut_index, leftover_items, frames)."""
    cut, left = pour(make_frames(0), make_blocks(), scratch())
    if cut is None or left is None:
        frames = make_frames(0)
        cut, left = pour(frames, make_blocks(), c if draw else scratch())
        return cut, left, frames
    frames = make_frames(JUMP_H)
    cut, left = pour(frames, make_blocks(), c if draw else scratch())
    if draw and left:
        last = frames[-1]
        c.setFont("Sans-BI", 7.2)
        c.setFillColor(RED)
        c.drawRightString(last._x1 + last._width, last._y1 - JUMP_H + 3, "Continued on page 2 \u25b8")
        c.setFillColor(black)
    return cut, left, frames


# ------------------------------------------------------------------ page 1
def page1(c, content, d, s, draw=True):
    """Draws the front page. Returns the list of continuations for page 2:
    (story, leftover_items or None for a story that did not start on page 1)."""
    st = styles(s)
    jumps = []
    y = nameplate(c, content, d, draw)
    y = teasers(c, content, y, draw)
    lead = content["lead"]
    bottom = M + 2

    # lead: headline across the page, deck and body on three columns, factbox on the fourth
    head = [Paragraph(esc(lead["kicker"]).upper(), st["kicker"]), Paragraph(esc(lead["headline"]), st["h_lead"])]
    hh = height(head, span(4))
    if draw:
        Frame(M, y - hh - 2, span(4), hh + 2, leftPadding=0, rightPadding=0, topPadding=0,
              bottomPadding=0).addFromList(head, c)
    y -= hh
    ytop_body = y
    sub = [Paragraph(esc(lead["deck"]), st["deck_lead"]),
           Paragraph("COMPILED FROM " + esc(lead["source"]).upper(), st["byline"])]
    sh = height(sub, span(3))
    if draw:
        Frame(M, y - sh - 2, span(3), sh + 2, leftPadding=0, rightPadding=0, topPadding=0,
              bottomPadding=0).addFromList(sub, c)
    fh = factbox(c, content["factbox"], colx(3), ytop_body, CW, draw) if content.get("factbox") else 120
    lead_h = max(fh - sh, 110)
    ybody = y - sh
    full_h = balanced(M, ybody, span(3), 3, lambda: body_flow(lead, st, "lead", dropcap=True), None, False)
    if full_h is not None and full_h <= lead_h:
        balanced(M, ybody, span(3), 3, lambda: body_flow(lead, st, "lead", dropcap=True), c, draw)
        used = full_h
    else:
        cut, left, _ = pour_with_jump(lambda r: make_cols(M, ybody, span(3), lead_h - r, 3),
                                   lambda: [([], body_flow(lead, st, "lead", dropcap=True))], c, draw)
        if left:
            jumps.append((lead, left))
        used = lead_h
        if draw:
            for i in (1, 2):
                vline(c, colx(i) - G / 2, ybody, ybody - lead_h, .3, HAIR)
    if draw and content.get("factbox"):
        vline(c, colx(3) - G / 2, ytop_body, ytop_body - max(fh, sh + used), .3, HAIR)
    y = min(ybody - used, ytop_body - fh) - 7
    if draw:
        hline(c, M, W - M, y, 1.6)
        hline(c, M, W - M, y - 2.6, .4)
    ylow = y - 12

    stories = content["stories"]
    wide, queue = stories[0], list(stories[1:])
    # columns 1-2: second lead (headline across two columns), then more stories in the space left
    wh = head_flow(wide, st, "wide")
    whh = height(wh, span(2))
    if draw:
        Frame(M, ylow - whh - 2, span(2), whh + 2, leftPadding=0, rightPadding=0, topPadding=0,
              bottomPadding=0).addFromList(wh, c)
    yb = ylow - whh
    n_fill = content.get("fill_wide", 1)          # stories allowed to continue under the second lead
    region_a = [wide] + queue[:n_fill]

    def blocks_a():
        out = [([], body_flow(wide, st, "wide"))]
        out += [(head_flow(it, st, "col"), body_flow(it, st, "col")) for it in region_a[1:]]
        return out
    cut, left, fr_a = pour_with_jump(lambda r: make_cols(M, yb, span(2), yb - bottom - r, 2), blocks_a, c, draw)
    rest = []
    if cut is not None:
        if left:
            jumps.append((region_a[cut], left))
            rest = region_a[cut + 1:]
        else:
            rest = region_a[cut:]
    queue = rest + queue[n_fill:]
    # fillers for the space left under the second lead: the first one that fits is used
    last = fr_a[-1]
    slack, ytop_f = last._y - last._y1p, last._y - 6
    fillers = []
    if content.get("pullquote"):
        fillers.append(lambda dr, yt: pullquote(c, content["pullquote"], last._x1, yt, CW, dr))
    if content.get("statbox"):
        fillers.append(lambda dr, yt: statbox(c, content["statbox"], last._x1, yt, CW, dr))
    for fill in fillers:
        fh_ = fill(False, 0)
        if slack >= fh_ + 8:
            if draw:
                fill(True, ytop_f)
            slack -= fh_ + 12
            ytop_f -= fh_ + 12
    if draw:
        vline(c, colx(1) - G / 2, yb, bottom, .3, HAIR)
    # column 3: single-column stories; a tiny jump is avoided by dropping that story's deck
    mk3 = lambda r: make_cols(colx(2), ylow, CW, ylow - bottom - r, 1)
    bl3 = lambda: [(head_flow(it, st, "col"), body_flow(it, st, "col")) for it in queue]
    cut, left, _ = pour_with_jump(mk3, bl3, None, False)
    if left and height(left, CW) < 50 and queue[cut].get("deck"):
        queue[cut] = dict(queue[cut], deck="")
    cut, left, fr_3 = pour_with_jump(mk3, bl3, c, draw)
    if cut is not None:
        if left:
            jumps.append((queue[cut], left))
            jumps += [(it, None) for it in queue[cut + 1:]]
        else:
            jumps += [(it, None) for it in queue[cut:]]
    # column 4: cartoon + dates
    ch = cartoon(c, content["cartoon"], colx(3), ylow, CW, draw)
    if draw:
        vline(c, colx(2) - G / 2, ylow, bottom, .5, black)
        vline(c, colx(3) - G / 2, ylow, bottom, .5, black)
        dates_box(c, content.get("dates", []), colx(3), ylow - ch - 14, bottom, CW)
    return jumps


class SectionLabel(Flowable):
    """column-wide section label inside a flow"""

    def __init__(self, text):
        super().__init__()
        self.text = text

    def wrap(self, aW, aH):
        self.aW = aW
        return aW, 22

    def draw(self):
        c = self.canv
        hline(c, 0, self.aW, 21, 2.2)
        c.setFont("Sans-B", 8.2)
        c.setFillColor(black)
        c.drawString(0, 10.5, self.text.upper())
        hline(c, 0, self.aW, 6, .4)


# ------------------------------------------------------------------ page 2
def wordsearch(words, n, seed):
    rnd = random.Random(seed)
    words = sorted({w.upper() for w in words}, key=len, reverse=True)
    g = [[""] * n for _ in range(n)]
    dirs = [(0, 1), (1, 0), (1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1), (-1, 1)]
    placed = []
    for w in words:
        for _ in range(800):
            dr, dc = rnd.choice(dirs)
            r, k = rnd.randrange(n), rnd.randrange(n)
            if not (0 <= r + dr * (len(w) - 1) < n and 0 <= k + dc * (len(w) - 1) < n):
                continue
            cells = [(r + dr * i, k + dc * i) for i in range(len(w))]
            if all(g[a][b] in ("", w[i]) for i, (a, b) in enumerate(cells)):
                for i, (a, b) in enumerate(cells):
                    g[a][b] = w[i]
                placed.append(w)
                break
    sol = [row[:] for row in g]
    for r in range(n):
        for k in range(n):
            if not g[r][k]:
                g[r][k] = rnd.choice("ABCDEFGHILMNOPRSTUVWY")
    return g, sol, placed


def page2_blocks(content, st, jumps, briefs):
    blocks = []
    for it, left in jumps:
        kick = Paragraph(f"CONTINUED FROM PAGE 1  ·  {esc(it.get('kicker', '')).upper()}", st["kicker"])
        if left:
            jh = it.get("jump_head", it.get("kicker", ""))
            blocks.append(([kick, Paragraph(esc(jh), st["h_col"])], left))
        else:
            hf = head_flow(it, st, "col")
            blocks.append((hf, body_flow(it, st, "col")))
    if briefs:
        first = briefs[0]
        blocks.append(([SectionLabel("News in brief")] + head_flow(first, st, "brief"), body_flow(first, st, "brief")))
        for it in briefs[1:]:
            blocks.append((head_flow(it, st, "brief"), body_flow(it, st, "brief")))
    return blocks


PUZ_N, PUZ_CS = 12, 14.5


def page2_frames(ytop, bottom, puzzle_top):
    frames = []
    for i in range(NCOL):
        y1 = bottom if i < 2 else puzzle_top + 12
        frames.append(Frame(colx(i), y1, CW, ytop - y1, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0))
    return frames


def puzzle_words(content, d):
    g = content["game"]
    _, _, placed = wordsearch(g["words"], PUZ_N, int(d.strftime("%Y%m%d")))
    return Paragraph(f"<font name='Sans-B' color='{RED_HEX}'>FIND</font>  " + "  ·  ".join(sorted(placed)),
                     ParagraphStyle("pw", fontName="Sans-B", fontSize=7.6, leading=9.6))


def puzzle_height(content, d, w):
    return 21 + 11 + puzzle_words(content, d).wrap(w, 200)[1] + 5 + PUZ_N * PUZ_CS


def puzzle_box(c, content, d, x, ytop, w):
    g = content["game"]
    n, cs = PUZ_N, PUZ_CS
    y = section_head(c, x, ytop, w, "Puzzle  ·  Word search")
    c.setFont("Serif-I", 8.6)
    c.setFillColor(black)
    c.drawString(x, y + 2, g["intro"])
    y -= 9
    pw = puzzle_words(content, d)
    _, h = pw.wrap(w, 200)
    pw.drawOn(c, x, y - h)
    gy = y - h - 5
    grid, sol, placed = wordsearch(g["words"], n, int(d.strftime("%Y%m%d")))
    c.setStrokeColor(black)
    c.setLineWidth(.45)
    for r in range(n):
        for k in range(n):
            x0, y0 = x + k * cs, gy - (r + 1) * cs
            c.rect(x0, y0, cs, cs)
            c.setFont("Mono-B", cs * .56)
            c.drawCentredString(x0 + cs / 2, y0 + cs * .28, grid[r][k])
    tx = x + n * cs + 10
    tw = x + w - tx
    cs2 = min(tw / n, 6.4)
    # solution, upside down, bottom-aligned with the grid
    c.saveState()
    c.translate(tx + n * cs2, gy - n * cs + n * cs2)
    c.rotate(180)
    c.setStrokeColor(HAIR)
    c.setLineWidth(.3)
    c.rect(0, 0, n * cs2, n * cs2)
    for r in range(n):
        for k in range(n):
            if sol[r][k]:
                c.setFont("Mono-B", cs2 * .78)
                c.drawCentredString(k * cs2 + cs2 / 2, (n - 1 - r) * cs2 + cs2 * .2, sol[r][k])
    c.setFont("Sans-B", 5)
    c.setFillColor(GRAY)
    c.drawString(0, n * cs2 + 2, "SOLUTION")
    c.restoreState()
    c.setFillColor(GRAY)
    c.setFont("Sans-I", 6.4)
    tip = Paragraph("Words run in every direction, also backwards.",
                    ParagraphStyle("tip", fontName="Sans-I", fontSize=6.6, leading=8, textColor=GRAY))
    _, th = tip.wrap(tw, 100)
    tip.drawOn(c, tx, gy - th)
    c.setFillColor(black)


def newsroom(c, kn, x, ytop, w, d, draw=True):
    """the newsroom press-release panel, built from the release feeds"""
    pad = 8
    iw = w - 2 * pad
    hs = ParagraphStyle("nrh", fontName="Serif-B", fontSize=15, leading=17.5, spaceAfter=3)
    bs = ParagraphStyle("nrb", fontName="Serif", fontSize=8.5, leading=11.4, **HY)
    ps = ParagraphStyle("nrp", fontName="Sans-B", fontSize=7.8, leading=9.5, textColor=RED)
    rs = ParagraphStyle("nrr", fontName="Serif-B", fontSize=9.6, leading=11.5, spaceBefore=4)
    ns = ParagraphStyle("nrn", fontName="Serif", fontSize=8.2, leading=10.4, leftIndent=8, bulletIndent=0, **HY)
    ls = ParagraphStyle("nrl", fontName="Sans-I", fontSize=6.8, leading=8.1, textColor=GRAY, splitLongWords=1)
    date = f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
    top = [Paragraph(esc(kn["headline"]), hs),
           Paragraph(f"<b>{date} —</b> " + esc(kn.get("intro", "")), bs)]
    def make_blocks():
        """one block per release, so a release title never sits orphaned at a column foot;
        the product name travels with its first release"""
        blocks = []
        for prod in kn["products"]:
            ph = [Paragraph(esc(prod["name"]).upper(), ps)]
            if prod.get("subtitle"):
                ph.append(Paragraph(esc(prod["subtitle"]), ls))
            rels = prod.get("releases", [])
            if not rels:
                blocks.append((ph, [Paragraph(esc(prod.get("quiet", "No new releases since the last edition.")), bs)]))
            for i, r in enumerate(rels):
                head = (ph if i == 0 else []) + [Paragraph(
                    f"{esc(r['component'])} {esc(r['version'])} "
                    f"<font name='Sans' size='7' color='#555555'>· {esc(r.get('date', ''))}</font>", rs)]
                body = [Paragraph(esc(n), ns, bulletText="•") for n in r.get("notes", [])]
                if r.get("url"):
                    body.append(Paragraph(links_markup([r["url"]]), ls))
                blocks.append((head + body, []))     # a release never splits across columns
            if prod.get("note"):
                blocks.append(([], [Paragraph(esc(prod["note"]), ParagraphStyle(
                    "nrnote", parent=bs, fontSize=7.8, leading=9.8, textColor=GRAY, spaceBefore=4))]))
            blocks.append(([], [Spacer(1, 8)]))
        return blocks[:-1]

    h_top = height(top, iw)
    lo, hi = 10, 700
    while hi - lo > 1:                          # smallest two-column height that holds everything
        mid = (lo + hi) // 2
        if flow(make_cols(x + pad, 0, iw, mid, 2), make_blocks(), scratch(), sep=False, min_lines=2):
            hi = mid
        else:
            lo = mid
    h_cols = hi
    total = 18 + h_top + 6 + h_cols + pad
    if draw:
        c.setFillColor(TINT)
        c.rect(x, ytop - total, w, total, fill=1, stroke=0)
        hline(c, x, x + w, ytop, 2.4, RED)
        c.setFillColor(RED)
        c.setFont("Sans-B", 8.6)
        c.drawString(x + pad, ytop - 12, kn.get("label", "NEWSROOM").upper(), charSpace=1)
        c.setFillColor(GRAY)
        c.setFont("Sans", 6.6)
        c.drawRightString(x + w - pad, ytop - 12, kn.get("source_label", "PRESS RELEASE").upper(), charSpace=.5)
        c.setFillColor(black)
        y = ytop - 18
        Frame(x + pad, y - h_top - 2, iw, h_top + 2, leftPadding=0, rightPadding=0, topPadding=0,
              bottomPadding=0).addFromList(list(top), c)
        y -= h_top + 6
        flow(make_cols(x + pad, y, iw, h_cols, 2), make_blocks(), c, sep=False, min_lines=2)
        vline(c, x + pad + (iw - G) / 2 + G / 2, y, ytop - total + pad, .4, HAIR)
    return total


def small_filler(c, f, x, ytop, w, draw=True):
    """compact fillers for column ends: number of the day, tip of the day"""
    y = ytop
    if draw:
        hline(c, x, x + w, y, 1.2)
        c.setFont("Sans-B", 6.8)
        c.setFillColor(RED)
        c.drawString(x, y - 9, esc(f.get("title", "")).upper())
        c.setFillColor(black)
    y -= 12
    src = f" <font name='Sans-I' color='#555555'>({esc(f['source'])})</font>" if f.get("source") else ""
    lst = ParagraphStyle("fll", fontName="Sans", fontSize=7.4, leading=8.7, **HY)
    if f["type"] == "number":
        vw = pdfmetrics.stringWidth(f["value"], "Serif-B", 16) + 5
        p = Paragraph(esc(f["label"]) + src, lst)
        _, ph = p.wrap(w - vw, 200)
        h = max(17, ph)
        if draw:
            c.setFont("Serif-B", 16)
            c.drawString(x, y - 14, f["value"])
            p.drawOn(c, x + vw, y - (h + ph) / 2 + (h - ph) / 2 - (h - ph) / 2)
        y -= h
    else:
        code = Paragraph(esc(f["code"]), ParagraphStyle("fc", fontName="Mono-B", fontSize=5.9, leading=7.4, splitLongWords=1))
        p = Paragraph(esc(f["label"]) + src, lst)
        _, ch = code.wrap(w, 200)
        _, ph = p.wrap(w, 200)
        if draw:
            code.drawOn(c, x, y - ch)
            p.drawOn(c, x, y - ch - 2 - ph)
        y -= ch + 2 + ph
    return ytop - y + 2


def fill_gaps(c, frames, fillers, draw=True, margin=5):
    """best fit: each filler (largest first) goes into the tightest column end that still holds it"""
    used = []
    order = sorted(fillers, key=lambda f: -small_filler(c, f, 0, 0, frames[0]._width, False))
    for f in order:
        h = small_filler(c, f, 0, 0, frames[0]._width, False)
        fits = [fr for fr in frames if fr._y - fr._y1p >= h + margin]
        if not fits:
            continue
        best = min(fits, key=lambda fr: fr._y - fr._y1p)
        if draw:
            small_filler(c, f, best._x1, best._y - margin + 2, best._width, True)
        best._y -= h + margin
        used.append(f)
    return used


def split_sentences(text):
    import re
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(])", text.strip())
    return [p for p in parts if p]


def page2(c, content, d, s, jumps, draw=True):
    st = styles(s)
    y = running_head(c, content, d, 2, draw)
    if content.get("krateo"):
        y -= newsroom(c, content["krateo"], M, y, W - 2 * M, d, draw) + 12
    bottom = M + 2
    puzzle_top = bottom + puzzle_height(content, d, span(2)) + 4
    def fits(bs):
        cut, _ = pour(page2_frames(y, bottom, puzzle_top), page2_blocks(content, st, jumps, bs), scratch())
        return cut is None
    if not fits([]):
        raise SystemExit("Page 2 overflow even without briefs: shorten the front-page stories.")
    briefs, dropped = [], []
    for b in content["briefs"]:                 # priority order, greedy: keep what fits
        if fits(briefs + [b]):
            briefs.append(b)
            continue
        sents = split_sentences(b["text"] if isinstance(b["text"], str) else " ".join(b["text"]))
        for k in range(len(sents) - 1, 0, -1):  # shortened at a sentence boundary, never mid-sentence
            short = dict(b, text=" ".join(sents[:k]))
            if fits(briefs + [short]):
                briefs.append(short)
                break
        else:
            dropped.append(b["headline"])
    if draw:
        frames = page2_frames(y, bottom, puzzle_top)
        pour(frames, page2_blocks(content, st, jumps, briefs), c)
        fill_gaps(c, frames, content.get("fillers", []))
        for i in range(1, NCOL):
            vline(c, colx(i) - G / 2, y, (bottom if i < 3 else puzzle_top + 10), .3, HAIR)
        puzzle_box(c, content, d, colx(2), puzzle_top, span(2))
        footer(c, content)
    return dropped


# ------------------------------------------------------------------ main
def build(content, out, s=1.0):
    d = datetime.date.fromisoformat(content["date"])
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle(f"{content.get('title', 'The Daily Reconcile')} — {d.isoformat()}")
    c.setAuthor("Claude")
    # dry run: find which briefs fit on page 2, then keep teasers on printed briefs only
    dry_jumps = page1(scratch(), json.loads(json.dumps(content)), d, s)
    dropped = set(page2(None, content, d, s, dry_jumps, draw=False))
    kept = [i for i, b in enumerate(content["briefs"]) if b["headline"] not in dropped]
    wanted = [i for i in content.get("teasers", [0, 1, 2]) if i in kept]
    content["teasers"] = (wanted + [i for i in kept if i not in wanted])[:3]
    items = [content["briefs"][i] for i in content["teasers"]]
    for it, left in dry_jumps:                   # top up with stories printed in full on page 2
        if len(items) >= 3:
            break
        if left is None:
            items.append(it)
    content["_teaser_items"] = items[:3]
    jumps = page1(c, content, d, s)
    c.showPage()
    dropped = page2(c, content, d, s, jumps)
    c.showPage()
    c.save()
    print(f"OK: {len(jumps)} stories continue on page 2; briefs dropped for space: {dropped or 'none'}")


def public_edition(content):
    """Copy of the issue that is safe to share publicly: no personal edition label. Newsroom
    products built from private sources ("private": true) stay in, but without links that only
    work inside the organisation, and with their public subtitle."""
    pub = json.loads(json.dumps(content))
    pub["edition"] = content.get("public_edition", "Daily edition")
    kn = pub.get("krateo")
    if kn:
        for p in kn.get("products", []):
            if p.get("private"):
                p["subtitle"] = p.get("public_subtitle", "Merged into main this week")
                for r in p.get("releases", []):
                    r.pop("url", None)
        if kn.get("public_headline"):
            kn["headline"] = kn["public_headline"]
        if kn.get("public_intro"):
            kn["intro"] = kn["public_intro"]
    return pub


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data = json.load(open(args[0] if args else "content.json"))
    if "--public" in sys.argv:
        data = public_edition(data)
    build(data, args[1] if len(args) > 1 else "daily-reconcile.pdf")
