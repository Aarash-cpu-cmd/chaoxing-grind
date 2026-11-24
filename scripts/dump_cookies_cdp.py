"""Dump chaoxing.com cookies from a running Chrome (CDP :29229) to JSON.

Usage: python scripts/dump_cookies_cdp.py [port] > ck.json
Chrome must be running with --remote-debugging-port=<port> and logged in
at v8.chaoxing.com.
"""
import asyncio
import json
import sys

sys.path.insert(0, ".")
from chaoxing_grind import cdp


async def main(port):
    async def f(ws, cmd):
        res = await cmd("Storage.getCookies")
        return res.get("result", {}).get("cookies", [])

    cks = await cdp.with_page(None, f, port=port)
    cks = [c for c in cks if "chaoxing" in c.get("domain", "")]
    print(json.dumps(cks, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 29229))
