"""Session factory for Chaoxing.

Cookie source: a JSON list of {"name","value","domain","path"} entries, e.g.
exported via Chrome DevTools "Copy as fetch/curl" or CDP Storage.getCookies.
See scripts/dump_cookies_cdp.py to pull them straight out of a running,
logged-in Chrome.

The returned session self-heals antispider blocks via CaptchaSolver when you
call session.get() through `resilient_get` / set `session.auto_solve=True`.
"""
import json
import time

import requests

from .antispider import CaptchaSolver, is_blocked

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

CPI = "336582683"  # partner id seen on all student course pages; constant across accounts


def load_session(cookie_path: str, ua: str = UA) -> requests.Session:
    cks = json.load(open(cookie_path))
    s = requests.Session()
    for c in cks:
        s.cookies.set(c["name"], c["value"],
                      domain=c.get("domain", ".chaoxing.com").lstrip("."),
                      path=c.get("path", "/"))
    s.headers.update({"User-Agent": ua, "Referer": "https://mooc1.chaoxing.com/"})
    return s


class Resilient:
    """Wrap a session so antispider hits auto-solve and retry."""

    def __init__(self, session: requests.Session, solver: CaptchaSolver | None = None,
                 max_retries: int = 3, pause: float = 0.0, verbose: bool = False):
        self.s = session
        self.solver = solver or CaptchaSolver()
        self.max_retries = max_retries
        self.pause = pause
        self.verbose = verbose

    def get(self, url, **kw):
        kw.setdefault("timeout", 30)
        for attempt in range(self.max_retries):
            r = self.s.get(url, **kw)
            loc = (r.headers.get("Location") or "") + r.url
            if "antispiderShowVerify" in loc or is_blocked(r.text):
                if self.verbose:
                    print(f"  blocked by antispider, solving ({attempt + 1})", flush=True)
                if not self.solver.solve(self.s, verbose=self.verbose):
                    return r
                continue
            if self.pause:
                time.sleep(self.pause)
            return r
        return r

    def post(self, url, **kw):
        kw.setdefault("timeout", 30)
        for attempt in range(self.max_retries):
            r = self.s.post(url, **kw)
            if is_blocked(r.text):
                if self.verbose:
                    print(f"  blocked by antispider, solving ({attempt + 1})", flush=True)
                if not self.solver.solve(self.s, verbose=self.verbose):
                    return r
                continue
            if self.pause:
                time.sleep(self.pause)
            return r
        return r


def whoami(session: requests.Session):
    """Best-effort identity probe. Returns (uid, name) or raises."""
    r = session.get("https://i.chaoxing.com/base", timeout=30)
    import re
    uid = re.search(r'uid[=: ]+["\']?(\d+)', r.text) or re.search(r"puid[=: ]+(\d+)", r.text)
    name = re.search(r'userName["\']?\s*[:=]\s*["\']([^"\']+)', r.text)
    return (uid.group(1) if uid else None, name.group(1) if name else None)
