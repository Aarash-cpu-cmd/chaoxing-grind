<div align="center">

# ⚡ Chaoxing Autopilot 超星刷课引擎

**全自动刷课：视频、文档、作业、讨论、验证码一体化**

*为 AI Agent 设计的超星/学习通任务点自动完成工具包*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](requirements.txt)
[![Chrome DevTools](https://img.shields.io/badge/Chrome-CDP-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)](SKILL.md)
[![OCR](https://img.shields.io/badge/OCR-ddddocr-FF6F00?style=for-the-badge)](chaoxing_grind/antispider.py)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Benchmark](https://img.shields.io/badge/Benchmark-6%2F6%20PASS-brightgreen?style=for-the-badge)](tests/benchmark.py)

</div>

---

## 🎯 这是什么

一个可以直接交给 **AI Agent** 使用的超星（学习通）刷课引擎。不是油猴脚本，不是 demo——是跑通**真实学生账号 12 门课、500+ 任务点**后沉淀下来的工程化工具包。

给 Agent 一个登录了学习通的 Chrome（CDP 端口）+ 一份 cookies，它自己扫课、自己刷、自己解验证码，你睡觉它干活。

## ✨ 五大能力

| 🎬 视频/音频 | 📄 文档/图文 | 📝 章节测验 | 💬 讨论题 | 🛡️ 反爬验证码 |
|---|---|---|---|---|
| CDP 真实播放 ×2 | 一次 GET 秒过 | 混淆字体解码答题 | 复制顶楼回复发布 | ddddocr 全自动解封 |

- **视频研磨**：焦点模拟 + `pause()` 劫持 + 卡死自动踢醒 + 超时重试队列。超星只认真播放，伪造进度全部无效——所以我们真的在"看"
- **测验答题**：超星用 cxsecret 动态字体混淆选项文本，内置 ~1100 字形签名映射，本地解码，**不依赖任何第三方题库 API**
- **验证码自解**：触发 9010 反爬墙后自动截验证码图 → OCR → POST `processVerify.ac` 解封，302 即全局放行
- **弹性会话**：`Resilient` 会话包装器，任何请求撞上反爬自动解封重试

## 🚀 快速开始

```bash
pip install -r requirements.txt

# 1️⃣ Chrome 带调试端口登录学习通（扫码即可）
google-chrome --remote-debugging-port=29229 https://v8.chaoxing.com/

# 2️⃣ 导出 cookies（仓库自带脚本）
python scripts/dump_cookies_cdp.py > ck.json

# 3️⃣ 全课程任务点扫描
python -m chaoxing_grind.cli scan --cookies ck.json --courses courses.json

# 4️⃣ 刷起来
python -m chaoxing_grind.cli docs  --cookies ck.json --jobs jobs.json   # 文档秒过
python -m chaoxing_grind.cli works --cookies ck.json --dir works/ --answers ans.json  # 测验
python -m chaoxing_grind.cli grind --jobs jobs.json --tabs 4            # 视频研磨
python -m chaoxing_grind.cli verify --cookies ck.json                   # 自检
```

## 🤖 给 Agent 用

直接读 [`SKILL.md`](SKILL.md) —— 每种任务点的确切打法、反爬规避节奏、踩过的坑，全部写明。任何能跑 Python + CDP 的 agent 照着做就能复现。

**血泪规则**（违反就触发 9010 验证码墙）：

- 页面打开/提交间隔 **≥20–60 秒**，反爬盯的是突发频率不是总量
- 任何响应先查 `antispider.is_blocked()`，撞墙就 `CaptchaSolver().solve()`
- 视频只看真播放：`currentTime >= duration` 才算数，拖进度条无效

## 🧪 Benchmark

`tests/benchmark.py` 跑通 6/6：登录识别、章节计数、验证码解封链路（含真实解封）、卡片页解析、字体解码（10题/113字形）、CDP 视频检测。

```bash
python tests/benchmark.py --cookies ck.json
```

## 📦 结构

```
chaoxing_grind/
  session.py     cookies → requests.Session + Resilient(自动解封重试)
  antispider.py  ddddocr 验证码解封
  courses.py     课程列表 + 章节任务点计数
  cards.py       卡片页 mArg → job 列表
  docs.py        文档任务点
  works.py       章节测验解析/提交
  fontdec.py     cxsecret 字体解码器
  video.py       CDP 视频研磨器
  discuss.py     讨论题
  cdp.py         Chrome DevTools 协议助手
  cli.py         命令行入口
  data/sig2char.json  字形签名→字符映射
scripts/dump_cookies_cdp.py   cookies 导出
tests/benchmark.py            端到端自检
```

## ⚠️ 免责声明

仅供学习交流与自动化技术研究使用。请在符合所在学校教学管理规定的前提下使用，使用本工具产生的一切后果由使用者自行承担。

---

<div align="center">
Made with ☕ by <a href="https://devin.ai">Devin</a> · 跑在真实课程上验证过的刷课引擎
</div>
