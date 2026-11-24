"""Discussion-task (讨论题) grinding: copy the top reply and post it.

Each topic page lists replies; copying the top one and publishing it marks
the task point complete. Keep >=20s between topic opens to stay under
antispider radar.

Endpoints (groupweb host):
  GET  groupweb.chaoxing.com/course/topic/v3/bbs/<groupid>/<topicid>?...  (HTML)
  POST groupweb.../coursedata/web/v3/topic/reply  (form-encoded reply)
Markup varies by theme; treat the regexes as starting points.
"""
import re

GROUPWEB = "https://groupweb.chaoxing.com"

TOPIC_URL = GROUPWEB + "/course/topic/v3/bbs/{gid}/{tid}"


def top_reply(html: str) -> str | None:
    """Extract the first reply's text from a topic page."""
    m = re.search(
        r'class="(?:bbs_reply|reply_content|con)[^"]*"[^>]*>(.*?)</div>', html, re.S)
    if not m:
        return None
    txt = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt or None


def reply_topic(s, gid, tid, content):
    """POST a reply. Adjust field names to the current form if needed."""
    r = s.post(GROUPWEB + "/coursedata/web/v3/topic/reply", data={
        "groupid": gid, "topicid": tid, "content": content,
        "anonymous": "0", "attInfo": "[]", "uuid": "",
    }, timeout=30)
    return r.status_code, r.text
