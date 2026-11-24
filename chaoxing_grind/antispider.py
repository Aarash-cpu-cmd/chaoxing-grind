"""Antispider (验证码墙) handling for Chaoxing.

When Chaoxing rate-limits a session, requests redirect to
https://mooc1.chaoxing.com/antispiderShowVerify.ac and every API call returns
the "【9010】操作异常" verify page (HTML containing 'yzmTips'). To clear it:

  GET  /processVerifyPng.ac?t=<rand>     -> 104x44 PNG, 4 chars
  POST /html/processVerify.ac  app=0&ucode=<4 chars>

POST success = HTTP 302 (redirect to the originally-blocked URL).
Failure = 202/404 with the verify page again. The lift is per-cookie-session
(server-side flag on the JSESSIONID-ish identity), and it is GLOBAL for that
session: once cleared, normal calls work again until the next burst.

ddddocr reads the PNG reliably; manual reading is error-prone (7/T, Y/X).
"""
import time

VERIFY_IMG = "https://mooc1.chaoxing.com/processVerifyPng.ac"
VERIFY_SUB = "https://mooc1.chaoxing.com/html/processVerify.ac"


def is_blocked(text_or_response) -> bool:
    """True when a response body is the 9010 verify page."""
    if text_or_response is None:
        return False
    txt = getattr(text_or_response, "text", text_or_response) or ""
    head = txt[:8000]
    return "yzmTips" in head or "antispiderShowVerify" in head or "【9010】" in head


class CaptchaSolver:
    def __init__(self):
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            import ddddocr
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr

    def read_code(self, png_bytes: bytes) -> str:
        return self._get_ocr().classification(png_bytes)

    def solve(self, session, tries: int = 10, verbose: bool = False) -> bool:
        """Fetch + read + submit captchas until the block lifts. Returns True on success."""
        for i in range(tries):
            try:
                r = session.get(f"{VERIFY_IMG}?t={int(time.time() * 1000)}", timeout=30)
            except Exception:
                time.sleep(2)
                continue
            if "image" not in (r.headers.get("Content-Type") or ""):
                time.sleep(2)
                continue
            code = self.read_code(r.content)
            try:
                resp = session.post(VERIFY_SUB, data={"app": "0", "ucode": code},
                                    allow_redirects=False, timeout=30)
            except Exception:
                time.sleep(1)
                continue
            if verbose:
                print(f"  captcha try {i}: {code!r} -> {resp.status_code}", flush=True)
            if resp.status_code in (301, 302):
                return True
            time.sleep(1)
        return False
