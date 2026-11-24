"""chaoxing-grind: grind Chaoxing (超星/学习通) course task points programmatically.

Modules:
  session   - cookie file -> requests.Session with retry + antispider auto-solve
  antispider- ddddocr-based captcha solver for the 9010 verify wall
  courses   - list courses, chapter task-point counts
  cards     - knowledge card page: parse mArg attachments/jobs
  docs      - document task points (one-shot completion)
  video     - real playback grinding via CDP-attached Chrome tabs
  works     - chapter work pages: fetch, decode (cxsecret font), submit answers
  cdp       - minimal Chrome DevTools Protocol helpers
"""
__version__ = "0.1.0"
