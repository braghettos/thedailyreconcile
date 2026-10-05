"""The Daily Reconcile: the paper's mark, drawn once and used everywhere.

A reconciliation loop - two arrows chasing each other inside a printer's seal - for the
GitOps idea the paper is named after: desired state and actual state, converging.
Pure geometry, so the same mark serves the printed nameplate (small, black, line art),
the LinkedIn page avatar and the GitHub social preview without redrawing.
"""
import math

# proportions, as multiples of the outer radius
RING_OUT_LW = .085
RING_IN_R, RING_IN_LW = .86, .028
ARC_R, ARC_LW = .55, .125
HEAD_L, HEAD_W = .30, .175
DOT_R = .11
SPAN = 126
STARTS = (16, 196)


def _arrowhead(cx, cy, r, a_deg):
    """triangle at the leading end of an arc, pointing along the tangent"""
    a = math.radians(a_deg)
    ex, ey = cx + r * ARC_R * math.cos(a), cy + r * ARC_R * math.sin(a)
    tx, ty = -math.sin(a), math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    hl, hw = r * HEAD_L, r * HEAD_W
    return ((ex + tx * hl, ey + ty * hl), (ex - nx * hw, ey - ny * hw), (ex + nx * hw, ey + ny * hw))


def draw(c, cx, cy, r, colour=None):
    """draw the mark on a reportlab canvas, centred on (cx, cy)"""
    from reportlab.lib.colors import black
    col = colour or black
    c.saveState()
    c.setStrokeColor(col)
    c.setFillColor(col)
    c.setLineWidth(max(.7, r * RING_OUT_LW)); c.circle(cx, cy, r)
    if r >= 11:                     # below that the hairline ring fills in and the seal goes muddy
        c.setLineWidth(max(.35, r * RING_IN_LW)); c.circle(cx, cy, r * RING_IN_R)
    c.setLineWidth(max(.8, r * ARC_LW))
    c.setLineCap(1)
    ar = r * ARC_R
    for a0 in STARTS:
        p = c.beginPath()
        p.arc(cx - ar, cy - ar, cx + ar, cy + ar, a0, SPAN)
        c.drawPath(p, stroke=1, fill=0)
        q = c.beginPath()
        pts = _arrowhead(cx, cy, r, a0 + SPAN)
        q.moveTo(*pts[0]); q.lineTo(*pts[1]); q.lineTo(*pts[2]); q.close()
        c.drawPath(q, stroke=0, fill=1)
    if r >= 8:
        c.circle(cx, cy, r * DOT_R, stroke=0, fill=1)
    c.restoreState()


def svg(size=512, colour="#000000", bg=None, pad=.10):
    """the same mark as a standalone SVG string

    Everything is worked out in canvas space (y up, the geometry above) and mirrored on the way
    out, so the SVG and the PDF can never drift apart. Mirroring reverses the sense of rotation,
    hence sweep-flag 1 for an arc the canvas draws counter-clockwise.
    """
    r = size / 2 * (1 - pad)
    cx = cy = size / 2
    ar = r * ARC_R
    f = lambda x, y: (x, size - y)          # canvas (y up) -> svg (y down)

    def on_arc(a_deg):
        a = math.radians(a_deg)
        return cx + ar * math.cos(a), cy + ar * math.sin(a)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
           f'width="{size}" height="{size}" role="img" aria-label="The Daily Reconcile">']
    if bg:
        out.append(f'<rect width="{size}" height="{size}" fill="{bg}"/>')
    out.append(f'<g fill="none" stroke="{colour}">')
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" stroke-width="{r*RING_OUT_LW:.2f}"/>')
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r*RING_IN_R:.2f}" '
               f'stroke-width="{r*RING_IN_LW:.2f}"/>')
    for a0 in STARTS:
        x0, y0 = f(*on_arc(a0))
        x1, y1 = f(*on_arc(a0 + SPAN))
        large = 1 if SPAN > 180 else 0
        out.append(f'<path d="M {x0:.2f} {y0:.2f} A {ar:.2f} {ar:.2f} 0 {large} 0 {x1:.2f} {y1:.2f}" '
                   f'stroke-width="{r*ARC_LW:.2f}" stroke-linecap="round"/>')
        tri = [f(x, y) for x, y in _arrowhead(cx, cy, r, a0 + SPAN)]
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in tri)
        out.append(f'<polygon points="{pts}" fill="{colour}" stroke="none"/>')
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r*DOT_R:.2f}" fill="{colour}" stroke="none"/>')
    out.append('</g></svg>')
    return "\n".join(out)
