"""Knowledge-card page parsing: extract mArg attachments + job ids."""
import json
import re

from .session import CPI

CARD_URL = ("https://mooc1.chaoxing.com/mooc-ans/knowledge/cards"
            "?clazzid={cl}&courseid={cid}&knowledgeid={kid}&num={num}"
            "&ut=s&cpi=" + CPI)


def card_url(cid, cl, kid, num=0):
    return CARD_URL.format(cl=cl, cid=cid, kid=kid, num=num)


def parse_marg(html: str) -> dict | None:
    """Extract the mArg JSON embedded in a card page."""
    m = re.search(r"mArg\s*=\s*(\{.*?\})\s*;", html, re.S)
    if not m:
        m = re.search(r"window\.mArg\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        # tolerate trailing commas
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(1)))
        except Exception:
            return None


def jobs_from_marg(marg: dict):
    """Yield job dicts: {module, jobid, kid, num, jtoken, objectid, ...}"""
    for att in (marg or {}).get("attachments", []):
        if not att.get("job"):
            continue
        prop = att.get("property") or {}
        yield {
            "module": att.get("module") or att.get("type"),
            "jobid": att.get("jobid"),
            "kid": (marg.get("defaults") or {}).get("knowledgeid") or prop.get("knowledgeid"),
            "num": (marg.get("defaults") or {}).get("knumid") or 0,
            "jtoken": att.get("jtoken"),
            "objectid": prop.get("objectid") or att.get("objectid"),
            "name": prop.get("name") or att.get("name"),
            "raw": att,
        }
