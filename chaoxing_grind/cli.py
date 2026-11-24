"""cx CLI: scan / docs / works / grind / verify.

  python -m chaoxing_grind.cli scan    --cookies ck.json
  python -m chaoxing_grind.cli docs    --cookies ck.json --jobs jobs.json
  python -m chaoxing_grind.cli works   --cookies ck.json --dir works/ --answers ans.json
  python -m chaoxing_grind.cli grind   --jobs jobs.json [--tabs 4] [--port 29229]
  python -m chaoxing_grind.cli verify  --cookies ck.json      # captcha self-test
"""
import argparse
import asyncio
import json
import sys

from .session import load_session, Resilient
from .antispider import CaptchaSolver
from . import courses, docs, works as works_mod, video


def cmd_scan(a):
    s = Resilient(load_session(a.cookies), verbose=True).s
    for cid, v in json.load(open(a.courses)).items():
        st = courses.chapter_status(s, cid, v["clazzid"])
        if st:
            flag = "" if st["done"] == st["total"] else f"  PENDING {st['total'] - (st['done'] or 0)}"
            print(f"{v.get('name', cid)}: {st['done']}/{st['total']}{flag}", flush=True)
        else:
            print(v.get("name", cid), "no enc", flush=True)


def cmd_docs(a):
    r = Resilient(load_session(a.cookies), verbose=True)
    jobs = json.load(open(a.jobs))
    ok = fail = 0
    for cid, d in jobs.items():
        for j in d["jobs"]:
            if j["module"] != "insertdoc" or not j.get("jobid"):
                continue
            j = dict(j, cid=cid, cl=d["cl"])
            good = r.s and docs.complete_document(r.s, j)
            ok += good
            fail += not good
            print(cid, j["jobid"], "OK" if good else "FAIL", flush=True)
    print("docs done:", ok, "fail:", fail)


def cmd_works(a):
    import os
    r = Resilient(load_session(a.cookies), verbose=True)
    ans = json.load(open(a.answers))
    done = set(json.load(open(a.done))) if os.path.exists(a.done) else set()
    ok = fail = 0
    for fn in sorted(os.listdir(a.dir)):
        if not fn.endswith(".html") or fn in done or fn not in ans:
            continue
        h = open(os.path.join(a.dir, fn)).read()
        try:
            code, txt = r.s and works_mod.submit_work(r.s, h, ans[fn])
            good = works_mod.submitted(txt)
            print(fn, code, "OK" if good else "CHECK", flush=True)
            if good:
                done.add(fn)
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(fn, "ERR", str(e)[:80], flush=True)
            fail += 1
        json.dump(list(done), open(a.done, "w"))
    print("works done:", ok, "fail:", fail)


def cmd_grind(a):
    jobs = json.load(open(a.jobs))
    cards = video.collect_media_cards(jobs)
    g = video.VideoGrinder(max_tabs=a.tabs, port=a.port, done_path=a.done)
    asyncio.run(g.grind(cards))


def cmd_verify(a):
    s = load_session(a.cookies)
    solver = CaptchaSolver()
    print("solve result:", solver.solve(s, verbose=True))


def main():
    p = argparse.ArgumentParser(prog="cx")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "docs", "works", "verify"):
        sp = sub.add_parser(name)
        sp.add_argument("--cookies", required=True)
        if name == "scan":
            sp.add_argument("--courses", required=True, help="json {cid:{clazzid,name}}")
        if name == "docs":
            sp.add_argument("--jobs", required=True)
        if name == "works":
            sp.add_argument("--dir", default="works")
            sp.add_argument("--answers", required=True)
            sp.add_argument("--done", default="work_done.json")
        sp.set_defaults(fn=globals()["cmd_" + name])
    sp = sub.add_parser("grind")
    sp.add_argument("--jobs", required=True)
    sp.add_argument("--tabs", type=int, default=4)
    sp.add_argument("--port", type=int, default=29229)
    sp.add_argument("--done", default="grind_done.json")
    sp.set_defaults(fn=cmd_grind)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
