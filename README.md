# bilingual-web-docx

> Turn a documentation site into a bilingual Word document — paragraph by paragraph.
> 把网站文档变成中英对照 Word 文档，逐段对齐。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](#requirements)

---

## English

### What it does

Given a URL — a journal's submission guidelines, a developer docs site, a regulatory policy page — this pipeline:

1. **Crawls** the page *and every linked sub-page*, using headless Chromium to get past JavaScript bot challenges.
2. **Extracts** clean structure: headings, paragraphs, ordered/unordered lists, tables (with in-cell line breaks), links, bold and italic.
3. **Translates** every text block into Chinese, one block in, one block out — never merged, split, or reordered.
4. **Typesets** a `.docx` with a cover page, auto-generated table of contents, part dividers, running headers, and clickable links.

Every block is rendered twice: the English original on top in grey with a grey rule on the left, the Chinese translation below in black with a green rule. The pairing is at paragraph level, so you can compare sentence by sentence instead of scrolling between two documents.

### Why not just "translate the page"

Because prose-level translation loses the thing that matters in a policy document: *exact wording*. When a journal says "manuscripts exceeding 2,500 words will be returned without review", you need the sentence in front of you next to its translation. Machine translation of a whole page gives you a readable approximation; block-level alignment gives you a checkable one.

The output is also **offline and searchable** — one file, no network, works in a review meeting.

### Verified output

Nature Sustainability — 34 documents, 842 aligned blocks, 151 pages:

- Part I — Submission Guidelines (14 docs, including per-article-type formatting rules)
- Part II — Editorial Policies (20 docs, including AI policy, authorship, ethics, peer review, reporting standards)

Cover, TOC, part dividers with per-part contents, bilingual side-by-side tables, no blank pages.

### Install

Clone or copy the folder into your WorkBuddy skills directory:

```bash
git clone https://github.com/hes1208/bilingual-web-docx.git \
  ~/.workbuddy/skills/bilingual-web-docx
```

The skill folder must keep `SKILL.md` at its root. Scripts are plain Python and can also be used standalone without WorkBuddy — just set up `pipeline.json` and run them in order.

### Requirements

| Component | Needed for | Notes |
|---|---|---|
| Python 3.9+ | everything | `python-docx`, `pypdfium2` are the only non-stdlib imports |
| Headless Chromium | step 1 (crawl) | Any `chrome`/`chromium` binary; Playwright's build works |
| Microsoft Word (Windows) | step 6 (TOC + PDF) | Uses COM to refresh fields and export PDF. Without Word, skip to a manual PDF export |

There are **no** `requests`, `beautifulsoup4`, `lxml`, or `pdfplumber` dependencies — the HTML parser and the PDF renderer are both hand-rolled on the stdlib plus `pypdfium2`.

### Quickstart

```bash
mkdir work && cd work
cp ../pipeline.example.json pipeline.json   # edit: output, cover, parts, body_attr
```

```bash
# 1. crawl (writes html/)
bash ../scripts/fetch_pages.sh urls.txt html

# 2. discover candidate sub-pages, then spot-check one page
python ../scripts/discover.py html https://example.com/base/
python ../scripts/probe.py html/example.com__page.html https://example.com/page

# 3. extract all pages into extracted.json
python ../scripts/extract.py

# 4. write glossary.md, split into chunks, dispatch to sub-agents
python ../scripts/chunk.py          # -> chunks/ + _batches.json
python ../scripts/verify.py         # after translation

# 5. merge bilingual content
python ../scripts/merge.py

# 6. typeset
python ../scripts/build_docx.py

# 7. visual check
powershell -NoProfile -ExecutionPolicy Bypass -File ../scripts/export_pdf.ps1 \
  -Src out.docx -Pdf preview.pdf
python ../scripts/render.py preview.pdf prev/
```

### Three rules that decide whether this takes one hour or five

These are not style preferences. They came out of a run that cost roughly 4× the estimate.

**1. Fix the scope before crawling.**
A site's home page links to part of its own content; policy pages and per-format sub-pages hide in the body text. Run `discover.py`, count the candidates, and ask the user to choose *core N₁* vs *everything N*. Expanding scope mid-run invalidates every chunk, translation, and page already produced.

**2. One sub-agent per batch of 4–5 chunks — not per chunk.**
Each sub-agent re-reads the glossary and the prompt template from scratch. At 65 chunks that fixed overhead was more than half the total cost. `chunk.py` emits `_batches.json` already grouped; dispatch by batch.

**3. Collect all layout defects, fix them in one pass.**
`edit script → rebuild docx → Word COM export → render PNG → look at it` is a two-minute loop. Run it once, list *every* problem you can see, fix them together, then verify. Fixing one defect per iteration is the second-largest cost sink.

### The Word traps worth knowing

Documented in [`references/docx-pitfalls.md`](references/docx-pitfalls.md). The four that cost the most:

- A table of contents needs a **four-part `fldChar` field**, and still shows nothing until Word refreshes it: `TablesOfContents.Item(1).Update()`.
- Use `paragraph_format.page_break_before = True`, **not** `add_page_break()`. The latter adds a paragraph *containing* a break, which is pushed to a new page when the previous one is already full — producing a blank page.
- For vertical positioning, add empty paragraphs. A `space_before` of 190pt or more pushes the whole paragraph onto the next page.
- Multiple `<p>` inside one table cell collapse into a single run unless you split them into `<br>` placeholders and restore them as in-cell line breaks.

### Repo layout

```
SKILL.md                        skill definition and 6-step workflow
pipeline.example.json           single config entry point
scripts/
  fetch_pages.sh                headless Chromium batch crawl, bot-challenge detection
  discover.py                   candidate sub-page links from crawled HTML
  probe.py                      single-page extraction preview
  extract.py                    HTML -> structured Markdown blocks
  htmltree.py                   minimal HTML tree builder (stdlib only)
  chunk.py                      split into translation chunks + dispatch batches
  verify.py                     translation completeness checks
  merge.py                      merge bilingual + strip navigation residue
  build_docx.py                 Word typesetting engine
  export_pdf.ps1                Word COM: refresh fields/TOC, export PDF
  render.py                     PDF -> PNG pages + blank-page report
references/
  translation-protocol.md       sub-agent prompt template and quality rules
  glossary-template.md          academic-publishing glossary, ready to adapt
  docx-pitfalls.md              15 python-docx / Word field traps
```

### Limitations

- Tuned for **article-style documentation**: sequential headings, paragraphs, lists, tables. Not for dashboards, interactive widgets, or content behind a login.
- Tables with `rowspan`/`colspan` are flattened — the Markdown table model has no such concept.
- The English column is always left, the translation always right; RTL languages would need a mirrored layout.
- Translation quality is only as good as the glossary. Spend the 20 minutes on `glossary.md`.

### License

MIT — see [LICENSE](LICENSE).

---

## 中文

### 它做什么

给它一个网址——期刊投稿指南、开发者文档站、法规政策页——这条流水线会：

1. **抓取**该页面*以及它链接到的每一个子页面*，用无头 Chromium 绕过 JavaScript 反爬校验。
2. **提取**干净的结构：标题、段落、有序/无序列表、表格（含单元格内换行）、链接、粗体与斜体。
3. **翻译**每一个文本块，一块进、一块出——绝不合并、拆分或重排。
4. **排版**成 `.docx`：封面、自动目录、分部扉页、页眉页脚、可点击链接。

每个块都呈现两次：上方英文原文，灰字＋左侧灰线；下方中文译文，黑字＋左侧绿线。对照发生在**段落级**，你可以逐句比对，而不是在两个文档之间来回滚动。

### 为什么不直接把整页翻译一遍

因为篇章级翻译恰好弄丢了政策文件里最重要的东西：**确切措辞**。当期刊写着 "manuscripts exceeding 2,500 words will be returned without review"，你需要这句话和它的译文同时出现在视野里。整页机翻给你一个可读的近似版本；逐块对照给你一个可核对的版本。

产物同时是**离线的、可检索的**——一个文件，不联网，评审会上直接翻。

### 已验证的成品

Nature Sustainability 投稿指南——34 篇、842 组对照、151 页：

- 第一部分 投稿指南（14 篇，含各类文章的逐项格式规范）
- 第二部分 编辑政策（20 篇，含 AI 政策、作者身份、研究伦理、同行评议、报告规范）

封面、目录、带本篇目次的分部扉页、中英并置表格，无空白页。

### 安装

克隆或复制到 WorkBuddy 的技能目录：

```bash
git clone https://github.com/hes1208/bilingual-web-docx.git \
  ~/.workbuddy/skills/bilingual-web-docx
```

技能目录根部必须保留 `SKILL.md`。脚本本身是纯 Python，**也可以脱离 WorkBuddy 独立使用**——配好 `pipeline.json` 按顺序执行即可。

### 环境要求

| 组件 | 用途 | 说明 |
|---|---|---|
| Python 3.9+ | 全部 | 第三方依赖只有 `python-docx` 与 `pypdfium2` |
| 无头 Chromium | 步骤 1 抓取 | 任意 `chrome`/`chromium` 可执行文件，Playwright 自带的即可 |
| Microsoft Word（Windows） | 步骤 6 目录与 PDF | 通过 COM 刷新域并导出 PDF；无 Word 时改用其他方式导出 PDF |

**不需要** `requests`、`beautifulsoup4`、`lxml`、`pdfplumber`——HTML 解析器和 PDF 渲染都在标准库（加 `pypdfium2`）上手写完成。

### 快速开始

```bash
mkdir work && cd work
cp ../pipeline.example.json pipeline.json   # 修改 output / cover / parts / body_attr
```

```bash
# 1. 抓取（写入 html/）
bash ../scripts/fetch_pages.sh urls.txt html

# 2. 摸清候选子页，再抽查单页
python ../scripts/discover.py html https://example.com/base/
python ../scripts/probe.py html/example.com__page.html https://example.com/page

# 3. 全量提取
python ../scripts/extract.py

# 4. 写 glossary.md，切块，派发给子 agent
python ../scripts/chunk.py          # 生成 chunks/ 与 _batches.json
python ../scripts/verify.py         # 翻译完成后校验

# 5. 合并双语
python ../scripts/merge.py

# 6. 排版
python ../scripts/build_docx.py

# 7. 视觉检查
powershell -NoProfile -ExecutionPolicy Bypass -File ../scripts/export_pdf.ps1 \
  -Src out.docx -Pdf preview.pdf
python ../scripts/render.py preview.pdf prev/
```

### 三条纪律：决定这件事花一小时还是五小时

这不是风格偏好，是从一次实际消耗约为预估四倍的运行里总结出来的。

**一、抓之前先定范围。**
站点首页只链出自己的一部分内容，政策页、分格式的子页藏在正文里。先跑 `discover.py` 数清候选页，再让用户二选一：*核心 N₁ 篇* 还是 *全量 N 篇*。中途扩范围会推翻已经做好的分块、翻译和排版。

**二、一个子 agent 处理 4–5 块，而不是一块一个 agent。**
每个子 agent 都要从零重读术语表和提示词模板。65 个块时，这部分固定开销超过了总成本的一半。`chunk.py` 已按批分好写入 `_batches.json`，照批派发。

**三、把版面缺陷一次性列全，一次改完。**
`改脚本 → 重建 docx → Word COM 导出 → 渲染 PNG → 看图` 是个两分钟的循环。跑一次，把所有能看到的问题列成清单，一起改，再验一轮。一次只修一个缺陷，是第二大成本来源。

### 值得先知道的 Word 坑

完整清单见 [`references/docx-pitfalls.md`](references/docx-pitfalls.md)。代价最大的四条：

- 目录必须用**四段式 `fldChar` 域**，而且保存后不刷新依然是一片空白：得调 `TablesOfContents.Item(1).Update()`。
- 分页用 `paragraph_format.page_break_before = True`，**不要**用 `add_page_break()`。后者会新增一个*含*分页符的段落，当上一页正好排满时它被挤到新页再分页，于是多出一张空白页。
- 垂直定位用若干空段落。`space_before` 设到 190pt 以上会把整个段落推到下一页。
- 表格单元格内的多个 `<p>` 会被压成一段，必须先切段用 `<br>` 占位，再还原为单元格内换行。

### 仓库结构

```
SKILL.md                        技能定义与六步工作流
pipeline.example.json           唯一配置入口
scripts/
  fetch_pages.sh                无头 Chromium 批量抓取，含反爬检测
  discover.py                   从已抓 HTML 提取候选子页链接
  probe.py                      单页试提取预览
  extract.py                    HTML → 结构化 Markdown 块
  htmltree.py                   极简 HTML 树构建（纯标准库）
  chunk.py                      切分翻译块并生成分批派发计划
  verify.py                     翻译完整性校验
  merge.py                      合并双语 + 清理导航残留
  build_docx.py                 Word 排版引擎
  export_pdf.ps1                Word COM：刷新域与目录，导出 PDF
  render.py                     PDF → PNG 逐页渲染 + 空白页报告
references/
  translation-protocol.md       子 agent 翻译提示词模板与质量规则
  glossary-template.md          学术出版术语表，可直接改用
  docx-pitfalls.md              15 条 python-docx / Word 域陷阱
```

### 适用范围与限制

- 面向**文章型文档**：顺序的标题、段落、列表、表格。不适合仪表盘、交互组件、登录后的内容。
- 带 `rowspan`/`colspan` 的表格会被拍平——Markdown 表格模型没有这个概念。
- 英文恒在左、译文恒在右；阿拉伯语等从右向左的语言需要镜像版式。
- 译文质量的上限就是术语表的质量。那 20 分钟花在 `glossary.md` 上很值。

### 许可

MIT，见 [LICENSE](LICENSE)。

---

<p align="center"><sub>Built from a real job: 34 pages of journal submission guidelines → one 151-page bilingual document.</sub></p>
