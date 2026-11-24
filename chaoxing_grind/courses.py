"""Course listing + chapter task-point counting."""
import re

from .session import CPI

MOOC1 = "https://mooc1.chaoxing.com"
MOOC2 = "https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse"


def list_courses(s):
    """Return [(courseid, clazzid, name)] from the user's course index."""
    r = s.get("https://mooc2-ans.chaoxing.com/mooc2-ans/visit/courses/list?rss=1&start=0&size=500",
              timeout=30)
    # rows look like: courseid=xxx&clazzid=yyy ... <h3 ...>NAME</h3> - markup varies;
    # fall back to the manage page if empty.
    out = re.findall(
        r'courseid=(\d+)&clazzid=(\d+)[^>]*>.{0,4000}?class="course-name[^>]*>(.*?)</',
        r.text, re.S)
    if not out:
        r = s.get("https://mooc2-ans.chaoxing.com/mooc2-ans/visit/courses/list", timeout=30)
    return out


def stuenc(s, courseid, clazzid):
    """Visit stucoursemiddle to obtain the enc token needed by studentcourse."""
    u = (f"{MOOC1}/visit/stucoursemiddle?courseid={courseid}&clazzid={clazzid}"
         f"&cpi={CPI}&ismooc2=1")
    r = s.get(u, allow_redirects=False, timeout=30)
    loc = (r.headers.get("Location") or "") + r.text
    m = re.search(r"enc=([0-9a-f]{32})", loc)
    if not m:
        # sometimes the page itself carries it
        m = re.search(r"stuenc=([0-9a-f]{32})", loc)
    return m.group(1) if m else None


DONE_RE = re.compile(r"已完成任务点.{0,150}?(\d+)\s*</span>\s*/\s*(\d+)", re.S)


def chapter_status(s, courseid, clazzid):
    """-> dict(done,total,kids). kids = list of knowledge ids (chapter items)."""
    enc = stuenc(s, courseid, clazzid)
    if not enc:
        return None
    r = s.get(f"{MOOC2}/studentcourse?courseid={courseid}&clazzid={clazzid}"
              f"&cpi={CPI}&ut=s&t=1&stuenc={enc}", timeout=30)
    mm = DONE_RE.search(r.text)
    kids = re.findall(r'id="cur(\d+)"', r.text)
    return {
        "done": int(mm.group(1)) if mm else None,
        "total": int(mm.group(2)) if mm else None,
        "kids": kids,
        "html_len": len(r.text),
    }
