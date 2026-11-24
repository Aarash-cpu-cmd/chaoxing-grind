---
name: chaoxing-grind
description: Grind Chaoxing (超星/学习通) course task points — videos, documents, chapter works, discussions — using exported login cookies and CDP-attached Chrome. Use when asked to complete 刷课/任务点/章节测验 on mooc1.chaoxing.com.
---

# chaoxing-grind

Programmatic Chaoxing course grinding. Verified on mooc1/mooc2-ans hosts against
a live student account (Nov 2026).

## Setup

1. `pip install -r requirements.txt` (requests, ddddocr, websockets, fonttools, Pillow)
2. Log the account into Chrome on this machine (QR scan at https://v8.chaoxing.com),
   Chrome must run with `--remote-debugging-port=29229`.
3. Dump cookies: `python -m chaoxing_grind.cli` expects a JSON list of
   `{"name","value","domain","path"}` — pull from CDP `Storage.getCookies` or
   export from DevTools.

## The five task-point types

| Type | Method | Speed |
|---|---|---|
| 文档/图文 (insertdoc) | `docs.complete_document` — one GET to `/ananas/job/document` | instant |
| 章节测验 (work) | dump work iframe HTML → `works.parse_questions` (cxsecret font decode) → `works.submit_work` | ~20s each, pace them |
| 视频/音频 (insertvideo/insertaudio) | `video.VideoGrinder` — real playback ×2 in CDP tabs | realtime ÷2 per card, N tabs parallel |
| 讨论题 (bbs) | `discuss.top_reply` + `reply_topic` — copy top answer, publish | ~20s each |
| 知识图谱/其他 | usually auto-completed when the card opens | — |

## Hard-won rules (violating them trips the 9010 captcha wall)

- **Pace everything ≥20–25s** between page opens / submissions. The antispider
  fires on bursts, not on total volume.
- On ANY response, check `antispider.is_blocked(body)`; when True run
  `CaptchaSolver().solve(session)` — POST `/html/processVerify.ac` with an
  OCR-read `ucode`, success = 302, and it lifts the block for the whole
  cookie session. Never GET that endpoint (404 trap).
- Videos only count while *actually playing*: focus-emulate the tab, patch
  `pause()` to noop in every realm, keep a re-play watchdog, then poll
  `currentTime >= duration` via CDP. Seeking/reporting progress does NOT count.
- Work pages sit inside iframes — dump `documentElement.outerHTML` of the
  iframe that contains `.TiMu`, not the outer page.
- Obfuscated text: decode via `fontdec.decode_html_text` (per-file subset
  fonts; glyph-shape signatures in `data/sig2char.json`). Missing glyphs →
  render them and extend the JSON.
- Verify completion on the **course homepage count** (`courses.chapter_status`),
  not in-section indicators — the latter lie (known display bug).
- Works already graded return `已批阅作业，不允许重复提交` — count as done,
  do not retry.

## CLI

```
python -m chaoxing_grind.cli scan   --cookies ck.json --courses courses.json
python -m chaoxing_grind.cli docs   --cookies ck.json --jobs jobs.json
python -m chaoxing_grind.cli works  --cookies ck.json --dir works/ --answers ans.json
python -m chaoxing_grind.cli grind  --jobs jobs.json --tabs 4 --port 29229
python -m chaoxing_grind.cli verify --cookies ck.json      # captcha solver self-test
```

`jobs.json`: `{courseid: {"cl": clazzid, "name": str, "jobs": [job,...]}}` where
each job comes from `cards.jobs_from_marg` — scan every chapter kid's card page
to collect them. `courses.json`: `{courseid: {"clazzid": ..., "name": ...}}`.

## Benchmark

`tests/benchmark.py` exercises: cookie session → course list → chapter scan →
document job → captcha OCR → work parse/decode → (optional) video card smoke
test. Run it against a real account before trusting a refactor.
