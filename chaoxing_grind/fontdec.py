"""Decode Chaoxing's cxsecret obfuscated font.

Work pages embed a per-file subset TTF (`font-ttf;charset=utf-8;base64,...`).
The subset's cmap maps real CJK codepoints to glyphs drawn as *different*
characters, so raw text looks garbled. Glyph outline = identity: we normalize
each glyph's recording to a shape signature and look it up in sig2char.json
(~1100 known glyphs harvested from real fonts).

sig2char.json maps repr(signature) -> true character. If a glyph is missing
you can extend it: render the unknown glyphs to an image, read the shapes,
add the mappings.
"""
import base64
import io
import json
import re
from importlib import resources

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen


def _sig2char():
    with resources.files(__package__).joinpath("data/sig2char.json").open() as f:
        return json.load(f)


SIG2CHAR = _sig2char()


def glyph_sig(font, gname):
    gs = font.getGlyphSet()[gname]
    pen = RecordingPen()
    gs.draw(pen)
    pts = [p for op in pen.value for p in op[1]]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = min(xs), min(ys)
    s = 1000 / max(max(xs) - x0, max(ys) - y0, 1)
    return tuple((n, tuple((round((a - x0) * s), round((b - y0) * s)) for a, b in p))
                 for n, p in pen.value)


def decode_font(ttf_bytes: bytes) -> dict:
    """-> {codepoint: true_char}"""
    f = TTFont(io.BytesIO(ttf_bytes))
    out = {}
    for t in f["cmap"].tables:
        if t.format in (4, 12):
            for cp, gn in t.cmap.items():
                s = glyph_sig(f, gn)
                if not s:
                    continue
                ch = SIG2CHAR.get(repr(s))
                if ch:
                    out[cp] = ch
    return out


def decode_html_text(html: str):
    """-> (decode_fn, fmap). decode_fn strips tags + maps obfuscated chars."""
    fmap = {}
    mm = re.search(r"font-ttf;charset=utf-8;base64,([A-Za-z0-9+/=]+)", html)
    if mm:
        fmap = decode_font(base64.b64decode(mm.group(1)))

    def dec(s):
        s = re.sub(r"<[^>]+>", "", s).replace("&nbsp;", " ")
        return "".join(fmap.get(ord(c), c) for c in s)

    return dec, fmap
