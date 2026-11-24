# chaoxing-grind

超星/学习通课程任务点自动完成工具包 —— 文档秒过、视频真实播放、章节测验解码提交、讨论题复制发布、反爬验证码 OCR 自解。

给一个能用浏览器登录学习通的 agent（或人）即可直接使用。

## 功能

| 任务点类型 | 处理方式 |
|---|---|
| 文档/图文 | 单次 GET `ananas/job/document` 直接完成 |
| 视频/音频 | CDP 控制 Chrome 真实播放 ×2 速（只能真看，拖动/报进度不计） |
| 章节测验 | 抓取 iframe 内题目 → cxsecret 混淆字体解码 → 按答案 JSON 提交 |
| 讨论题 | 复制最顶上回复发布 |
| 反爬验证码 | ddddocr 自动识别 + POST `/html/processVerify.ac` 解封 |

## 环境要求

- Python 3.10+，`pip install -r requirements.txt`
- 一台跑着 Chrome 且带 `--remote-debugging-port=29229` 的机器（视频、题目抓取需要）
- 已登录学习通的浏览器会话 → 导出 cookies JSON

## 快速开始

```bash
# 1. 登录后导出 cookies（CDP Storage.getCookies 或 devtools 复制）
# 2. 课程状态扫描
python -m chaoxing_grind.cli scan --cookies ck.json --courses courses.json
# 3. 文档任务点
python -m chaoxing_grind.cli docs --cookies ck.json --jobs jobs.json
# 4. 章节测验（works/ 下放抓取到的题目 HTML，answers.json 给答案）
python -m chaoxing_grind.cli works --cookies ck.json --dir works/ --answers ans.json
# 5. 视频研磨（4 个标签并行）
python -m chaoxing_grind.cli grind --jobs jobs.json --tabs 4
# 6. 验证码自解自检
python -m chaoxing_grind.cli verify --cookies ck.json
```

## 给 agent 用

读 `SKILL.md` —— 里面有每种任务点的确切打法、反爬规避节奏、踩过的坑。

## 结构

```
chaoxing_grind/
  session.py    cookies -> requests.Session + Resilient(自动解封重试)
  antispider.py ddddocr 验证码解封 (POST /html/processVerify.ac)
  courses.py    课程列表 + 章节任务点计数
  cards.py      卡片页 mArg 解析 -> job 列表
  docs.py       文档任务点
  works.py      章节测验解析/提交 + cxsecret 字体解码 (fontdec.py)
  video.py      CDP 视频研磨器 (VideoGrinder)
  cdp.py        Chrome DevTools 协议助手
  discuss.py    讨论题
  cli.py        命令行入口
  data/sig2char.json  字形签名->字符映射 (~1100 glyphs)
```

## 免责声明

仅供学习交流/自动化测试使用。请在符合学校规定的前提下使用。
