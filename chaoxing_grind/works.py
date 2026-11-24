"""Chapter work (章节测验) pages: fetch, decode, submit answers.

Page structure (inside the work iframe):
  <div class="TiMu singleQuesId" data="<qid>"> ... question body
  options: <li aria-label="A <text>选择">  (both ' and " quoting seen)
  T/F: radios value "true"/"false"
  multiple choice: concatenate letters, e.g. "ABDE"

Submission: POST the form's action under /mooc-ans/work/ with hidden fields +
  answerwqbid=<qids>&answer<qid>=<letter(s) or true/false>
Success body: {"msg":"success!","stuStatus":4}
"已批阅作业，不允许重复提交" means already graded — treat as done.
"""
import html as ihtml
import re

from .fontdec import decode_html_text

WORK_BASE = "https://mooc1.chaoxing.com/mooc-ans/work/"


def parse_questions(html_text: str):
    """-> [{'qid','title','opts':[(letter,text)]}] with decoded text."""
    dec, fmap = decode_html_text(html_text)
    qs = []
    for qid, body in re.findall(
            r'<div class="TiMu singleQuesId" data="(\d+)">(.*?)'
            r'(?=<div class="TiMu singleQuesId"|$)', html_text, re.S):
        t = re.search(r"fontLabel[^>]*>(.*?)</div>", body, re.S)
        opts = re.findall(r'aria-label="([A-E]) (.*?)选择"', body)
        if not opts:
            opts = re.findall(r"aria-label='([A-E]) (.*?)选择'", body)
        qs.append({
            "qid": qid,
            "title": dec(t.group(1)).strip() if t else "",
            "opts": [(l, dec(o).strip()) for l, o in opts],
        })
    return qs, fmap


def parse_form(html_text: str):
    m = re.search(r'<form[^>]*action="([^"]*)"', html_text)
    action = ihtml.unescape(m.group(1)) if m else None
    fields = {}
    for mm in re.finditer(r'<input[^>]*type="hidden"[^>]*>', html_text):
        t = mm.group(0)
        n = re.search(r'name="([^"]+)"', t)
        if not n:
            continue
        v = re.search(r'value="([^"]*)"', t)
        fields[n.group(1)] = ihtml.unescape(v.group(1)) if v else ""
    atypes = {}
    for mm in re.finditer(r'name="answertype(\d+)"[^>]*value="(\d+)"', html_text):
        atypes[mm.group(1)] = mm.group(2)
    return action, fields, atypes


def submit_work(s, html_text: str, answers: dict):
    """answers: {qid: 'A'|'ABDE'|'true'|'false'}. Returns (code, body)."""
    action, fields, atypes = parse_form(html_text)
    if not action or not atypes:
        raise ValueError("no form/question types found")
    data = dict(fields)
    data["answerwqbid"] = ",".join(atypes.keys())
    for qid, ty in atypes.items():
        data["answertype" + qid] = ty
        data["answer" + qid] = answers.get(qid, "")
    url = (WORK_BASE + action +
           "&pyFlag=&ua=pc&formType=post&saveStatus=1&version=1")
    r = s.post(url, data=data, timeout=30)
    return r.status_code, r.text


def submitted(resp_text: str) -> bool:
    t = (resp_text or "")[:300].lower()
    return "success" in t or "不允许重复提交" in t or "已批阅" in t


DUMP_WORK_JS = r"""
(()=>{let found=null;
 const walk=(d)=>{if(found)return;
   if(d.querySelector&&d.querySelector('.TiMu')){found=d.documentElement.outerHTML;return;}
   for(const f of d.querySelectorAll('iframe')){try{if(f.contentDocument)walk(f.contentDocument)}catch(e){}}};
 walk(document);return found||'NONE'})()
"""
