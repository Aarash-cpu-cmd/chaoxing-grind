"""Video/audio task points: real playback in CDP-attached Chrome tabs.

Progress only counts while the <video>/<audio> actually plays. What the
grinder does per card:

  * open the card URL in a new tab (paced, >=25s between opens — bursts trip
    antispider)
  * Emulation.setFocusEmulationEnabled so the page thinks it's focused
  * patch HTMLMediaElement.prototype.pause = noop in every realm (the player
    JS tries to pause videos it thinks are off-screen)
  * in-page watchdog re-plays muted videos every 1.5s and clicks
    "继续观看"-style prompts
  * playbackRate = 2
  * poll media state until ct >= dur (or ended)

Detecting antispider mid-run: the tab url flips to antispiderShowVerify.ac —
solve the captcha (browser-side POST /html/processVerify.ac, or share the
requests solver) then navigate the tab back to its card URL.
"""
import asyncio
import json
import time
import urllib.request

from .cdp import (DEFAULT_PORT, close_tab, eval_on, new_tab, targets, with_page)
from .cards import card_url

PLAY_JS = r"""
(async()=>{
  let vids=[]; let docs=[document];
  const seen=new Set();
  const walk=(doc)=>{
    if(seen.has(doc))return; seen.add(doc);
    try{
      const w=doc.defaultView;
      if(w&&w.HTMLMediaElement)w.HTMLMediaElement.prototype.pause=function(){};
    }catch(e){}
    for(const v of doc.querySelectorAll('video,audio')) vids.push(v);
    for(const f of doc.querySelectorAll('iframe')){
      try{if(f.contentDocument){docs.push(f.contentDocument);walk(f.contentDocument);}}catch(e){}
    }
  };
  walk(document);
  for(const d of docs){
    const w=d.defaultView;
    if(w&&!w.__cx_watch){
      w.__cx_watch=true;
      try{
        w.HTMLMediaElement.prototype.pause=function(){};
        w.setInterval(()=>{for(const v of d.querySelectorAll('video,audio')){v.muted=true;if(v.paused){const p=v.play();if(p&&p.catch)p.catch(e=>{})}}},1500);
      }catch(e){}
    }
  }
  let ready=0;
  for(const v of vids){v.muted=true; v.playbackRate=2; const p=v.play(); if(p&&p.catch)p.catch(e=>{}); if(v.duration>0)ready++;}
  for(const d of docs){
    for(const b of d.querySelectorAll('button,.vjs-button,[role=button],.btn,.layui-layer-btn a,.el-button')){
      const t=(b.textContent||'').trim();
      if(/继续|仍在观看|我知道了|确定|好的/.test(t) && b.offsetParent!==null){b.click();}
    }
  }
  return {n:vids.length,ready:ready};
})()
"""

STATE_JS = r"""
(()=>{
  let out=[];
  const walk=(doc)=>{
    for(const v of doc.querySelectorAll('video,audio'))
      out.push({ct:v.currentTime,dur:v.duration,ended:v.ended,paused:v.paused});
    for(const f of doc.querySelectorAll('iframe')){
      try{if(f.contentDocument)walk(f.contentDocument)}catch(e){}
    }
  };
  walk(document); return out;
})()
"""


class Retry(Exception):
    pass


class VideoGrinder:
    """Queue-driven grinder over (cid, cl, kid, num) cards containing media."""

    def __init__(self, max_tabs=4, port=DEFAULT_PORT, open_gap=25,
                 card_timeout=900, stall_kick=45, max_kicks=3, max_attempts=6,
                 done_path="grind_done.json", verbose=True):
        self.max_tabs = max_tabs
        self.port = port
        self.open_gap = open_gap
        self.card_timeout = card_timeout
        self.stall_kick = stall_kick
        self.max_kicks = max_kicks
        self.max_attempts = max_attempts
        self.done_path = done_path
        self.verbose = verbose
        self.done = set()
        self.block_until = 0.0
        self.last_open = 0.0
        try:
            self.done = set(json.load(open(done_path)))
        except Exception:
            pass

    def log(self, *a):
        if self.verbose:
            print(*a, flush=True)

    def save_done(self):
        json.dump(list(self.done), open(self.done_path, "w"))

    async def _tab_url(self, tid):
        for t in await targets(self.port):
            if t["id"] == tid:
                return t.get("url", "")
        return ""

    async def _paced_new_tab(self, url):
        dt = time.time() - self.last_open
        if dt < self.open_gap:
            await asyncio.sleep(self.open_gap - dt)
        t = await new_tab(url, self.port)
        self.last_open = time.time()
        return t

    async def grind_card(self, cid, cl, kid, num=0):
        key = f"{cid}:{kid}:{num}"
        if key in self.done:
            return "done"
        url = card_url(cid, cl, kid, num)
        tab = await self._paced_new_tab(url)
        tid = tab["id"]
        match = f"knowledgeid={kid}"
        try:
            await asyncio.sleep(10)
            u = await self._tab_url(tid)
            if "antispider" in u or "processVerify" in u:
                self.block_until = time.time() + 120
                self.log("ANTISPIDER cooldown 120s", key)
                raise Retry(key)

            async def foc(ws, cmd):
                try:
                    await cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})
                except Exception:
                    pass
            await with_page(match, foc, port=self.port)
            await asyncio.sleep(8)
            for _ in range(20):
                r = await eval_on(match, PLAY_JS, port=self.port)
                if isinstance(r, dict) and r.get("n", 0) > 0 and r.get("ready", 0) >= r.get("n", 1):
                    break
                await asyncio.sleep(7)
            t0 = time.time()
            last_sig = None
            last_prog = t0
            kicks = 0
            while time.time() - t0 < self.card_timeout:
                st = await eval_on(match, STATE_JS, port=self.port)
                if not st:
                    await asyncio.sleep(8)
                    continue
                sig = tuple(round(v["ct"]) for v in st)
                if sig != last_sig:
                    last_sig = sig
                    last_prog = time.time()
                if time.time() - last_prog > self.stall_kick:
                    if kicks >= self.max_kicks:
                        self.log("CARD STALL-RETRY", key, st)
                        raise Retry(key)
                    await eval_on(match, PLAY_JS, port=self.port)
                    last_prog = time.time()
                    kicks += 1
                    self.log("KICK", key)
                if st and all(v["dur"] > 0 and (v["ended"] or v["ct"] >= v["dur"] - 0.6) for v in st):
                    self.done.add(key)
                    self.save_done()
                    self.log("CARD DONE", key)
                    return "ok"
                await asyncio.sleep(15)
            self.log("CARD TIMEOUT", key)
            raise Retry(key)
        finally:
            await close_tab(tid, self.port)

    async def _worker(self, q):
        attempts = {}
        while True:
            item = await q.get()
            if item is None:
                q.task_done()
                return
            try:
                if time.time() < self.block_until:
                    raise Retry(item)
                await self.grind_card(*item)
            except Retry:
                attempts[item] = attempts.get(item, 0) + 1
                if attempts[item] < self.max_attempts:
                    q.put_nowait(item)
                else:
                    self.log("GIVEUP", item)
            except Exception as e:
                self.log("ERR", item, str(e)[:120])
                if "index out of range" in str(e):
                    self.block_until = time.time() + 120
                attempts[item] = attempts.get(item, 0) + 1
                if attempts[item] < self.max_attempts:
                    q.put_nowait(item)
                else:
                    self.log("GIVEUP", item)
            q.task_done()

    async def grind(self, cards):
        """cards: iterable of (cid, cl, kid, num)."""
        cards = [c for c in cards if f"{c[0]}:{c[2]}:{c[3]}" not in self.done]
        self.log("cards to grind:", len(cards))
        q = asyncio.Queue()
        for c in cards:
            q.put_nowait(c)
        for _ in range(self.max_tabs):
            q.put_nowait(None)
        ws = [asyncio.create_task(self._worker(q)) for _ in range(self.max_tabs)]
        await q.join()
        for w in ws:
            w.cancel()


def collect_media_cards(jobs_by_course):
    """jobs_by_course: {cid:{'cl':cl,'jobs':[...]}} -> deduped card list for media jobs."""
    out = []
    for cid, d in jobs_by_course.items():
        seen = set()
        for j in d["jobs"]:
            if j["module"] in ("insertvideo", "insertaudio"):
                k = (cid, d["cl"], j["kid"], j.get("num", 0))
                if k not in seen:
                    seen.add(k)
                    out.append(k)
    return out
