"""Minimal Chrome DevTools Protocol helpers (websockets only).

Attach to a running Chrome started with --remote-debugging-port=<port>.
"""
import asyncio
import json
import urllib.request
import urllib.parse

import websockets

DEFAULT_PORT = 29229


async def targets(port=DEFAULT_PORT):
    return json.load(urllib.request.urlopen(f"http://localhost:{port}/json/list"))


async def new_tab(url, port=DEFAULT_PORT):
    req = urllib.request.Request(
        f"http://localhost:{port}/json/new?{urllib.parse.quote(url, safe='')}",
        method="PUT")
    return json.load(urllib.request.urlopen(req))


async def close_tab(tab_id, port=DEFAULT_PORT):
    try:
        req = urllib.request.Request(f"http://localhost:{port}/json/close/{tab_id}")
        return json.load(urllib.request.urlopen(req))
    except Exception:
        return None


def _find(pages, match):
    if match is None:
        return pages[0]
    hits = [p for p in pages if match in p["url"]]
    if not hits:
        raise IndexError(f"no page matching {match!r}")
    return hits[0]


async def with_page(match, fn, timeout=60, port=DEFAULT_PORT):
    """fn(ws, cmd) -> value. cmd(method, params) is a CDP call helper."""
    pages = [t for t in await targets(port) if t["type"] == "page"]
    t = _find(pages, match)
    async with websockets.connect(t["webSocketDebuggerUrl"], open_timeout=15,
                                  max_size=200 * 1024 * 1024) as ws:
        mid = [0]

        async def cmd(method, params=None):
            mid[0] += 1
            i = mid[0]
            await ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
            while True:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout))
                if m.get("id") == i:
                    return m
        return await fn(ws, cmd)


async def eval_on(match, expr, timeout=60, port=DEFAULT_PORT):
    async def f(ws, cmd):
        r = await cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "awaitPromise": True, "timeout": timeout * 1000})
        res = r.get("result", {})
        if "exceptionDetails" in res or "exceptionDetails" in r:
            return {"error": (r.get("result", {}).get("exceptionDetails")
                              or res.get("exceptionDetails"))}
        return res.get("result", {}).get("value")
    return await with_page(match, f, timeout, port)


async def navigate(match, url, port=DEFAULT_PORT):
    async def f(ws, cmd):
        return await cmd("Page.navigate", {"url": url})
    return await with_page(match, f, port=port)


def run(coro):
    return asyncio.run(coro)
