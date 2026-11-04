---
name: bilingual-web-docx
description: 把网站/文档站（期刊投稿指南、编辑政策、开发者文档、法规政策页等）抓取下来逐段译为中文，产出排版精美的中英对照 Word 文档。当用户给出一个网页或站点链接，要求"提取全部下级页面内容并翻译成中文""做成中英对照版""整理成 Word"时使用此技能。内含绕 JS 反爬的无头浏览器抓取、正文容器自动识别、分批并行翻译协议、docx 排版引擎与 PDF 视觉验证闭环。
agent_created: true
---

# 网页文档 → 中英对照 Word

## 用途

把一个页面及其全部下级页面（多级导航、政策子页、格式规范页）抓成结构化文本，逐段对照翻译，
产出带封面、自动目录、分部扉页、可点击链接的中英对照 Word 文档。

已验证案例：Nature Sustainability 投稿指南（34 篇 / 842 组对照 / 151 页 Word）。

## 何时使用

- 「把这个投稿指南页面和它下面的所有子页面提取到 word，翻译成中文」
- 「这份开发者文档 / 政策文件，做成中英对照的 word 给我」
- 「这些页面内容整理成一份可检索的离线文档」

不适用：只要摘要、只要单页内容、只要纯中文改写（无需原文对照）。

## 铁律：先定范围再动手

**开工前必须先向用户确认抓取范围，并给出篇数 / 字数 / 成本估算。** 这一步能省掉一半成本。

站点首页往往只链出一部分导航，正文里还藏着大量子页（政策页、格式页、内容类型页）。
先跑 `scripts/discover.py` 摸清候选页数量，再给用户二选一：

> 实测该站共有 N 个相关子页（约 X 万字）。
> A. 核心 N₁ 篇（只含主链路）—— 预计 Y
> B. 全量 N 篇（含全部政策 / 附录子页）—— 预计 Z

**不要边抓边扩。** 范围中途扩张会推翻已有的分块、翻译与排版，是最大的成本黑洞。

## 工作流

工作目录约定（所有脚本读取同目录下的 `pipeline.json`）：

```
work/
├── pipeline.json      ← 唯一配置入口（从 pipeline.example.json 复制后改）
├── glossary.md        ← 术语表（翻译前手工整理，模板见 references/）
├── urls.txt           ← 待抓 URL 清单
├── html/              ← 抓取的 DOM
├── extracted.json     ← 结构化块
├── chunks/            ← 翻译任务块 + 译文
├── titles_zh.json     ← 篇目标题中文映射（可选，缺失则自动推导）
└── bilingual.json     ← 合并结果
```

开工第一步永远是：`cp pipeline.example.json pipeline.json`，改 `output` / `cover` / `parts` / `body_attr`。

### 步骤 1 — 抓取

```bash
bash scripts/fetch_pages.sh urls.txt html
```

用无头 Chromium 绕过 JS 反爬。普通 `requests` / `urllib` 对 nature.com、Cloudflare 站点
一律只能拿到约 3KB 的占位页 —— **拿到一次占位页就判定为 JS 校验，不要重复试同一路径。**

脚本内置：占位页检测、失败重试、限流。

### 步骤 2 — 摸清结构 + 提取

```bash
python scripts/discover.py html https://example.com/base/   # 输出候选内链清单
python scripts/probe.py html/xxx.html https://example.com/page   # 单页试提取
python scripts/extract.py                                    # 全量提取
```

`extract.py` 按三级策略定位正文容器：

1. `pipeline.json` 显式指定的属性选择器（最稳，如 `data-container-type=body-content`）
2. 语义标签 `main` / `article` / `[role=main]`
3. 文本密度自动打分（自身文本量 × 段落数，取深度最大的高分节点）

先 probe 确认标题、列表、表格、链接都提出来了，再全量跑。

### 步骤 3 — 分块与翻译

```bash
python scripts/chunk.py      # 产出 chunks/ 与 _batches.json
python scripts/verify.py     # 翻译完成后校验
```

**关键成本约束：一个子 agent 处理一批（4–5 块），不要一块一个 agent。**
每块约 6500 字符，一批约 2.5–3 万字。`chunk.py` 已按批分好写入 `_batches.json`，照批派发。
一块一个 agent 会让固定开销（读术语表、读提示词、跑校验）重复几十遍，实测占掉总成本一半以上。

翻译提示词模板见 `references/translation-protocol.md`，直接引用，不要临场重写。
术语表模板见 `references/glossary-template.md`。

`verify.py` 逐块检查：文件缺失、JSON 非法、项数不符、空译文、与原文完全相同的未译项。
连续两轮仍有 BAD 才手工介入。

### 步骤 4 — 合并

```bash
python scripts/merge.py
```

合并双语、清理导航残留（`On this page` / `Top of page ⤴` 等）、修正零散星号标记。
导航词表在 `pipeline.json` 的 `drop_text_patterns`，按目标站点补充。

### 步骤 5 — 生成 Word

```bash
python scripts/build_docx.py
```

封面、自动目录、分部分扉页、页眉页脚、表格双语并置均已内置。只需在 `pipeline.json`
填 `cover`（期刊名 / 主标题 / 元信息表）与 `parts`（分部标题 + 归属篇目）。
分部归属用**英文标题匹配**，不用索引 —— 站点增删页面时不会错位。

### 步骤 6 — 视觉验证（必做，但必须批处理）

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/export_pdf.ps1 -Src out.docx -Pdf preview.pdf
python scripts/render.py preview.pdf prev/                   # 逐页渲染 PNG，并报告空白页
```

用 ViewImage 检查：封面、目录、扉页、正文首页、含表格页。

**一次列全缺陷，一次改完，再验一轮。** 不要"发现一个改一个"地反复跑 Word 导出 ——
每次 COM 导出 + 渲染 + 视觉检查都要几十秒到几分钟，单缺陷循环是第二大成本来源。

## 排版与域陷阱

Word 文档的坑集中在 `references/docx-pitfalls.md`，动手前读一遍。最关键的几条：

- 目录必须用四段式 `fldChar` 域，保存后再用 COM 调 `TablesOfContents.Update()` 才出内容
- 分页用 `paragraph_format.page_break_before = True`，**不要** `add_page_break()`
- 垂直定位用固定空段落，**不要**大 `space_before`（≥190pt 会把整段推到下一页）
- 表格单元格内多段内容用 `<br>` 占位再还原为段内换行，否则全挤成一段
- 表格行加 `w:cantSplit` 防止跨页断裂

## 交付前自检

- [ ] 原文块数 = 译文块数，`verify.py` 零 BAD
- [ ] 无小于 70 字符的空白页（`render.py` 会打印清单）
- [ ] 目录条目数与实际篇数一致
- [ ] 抽查 3 个不同页面：标题 / 列表 / 表格 / 链接渲染正常
- [ ] 封面元信息（篇数、字数、日期）与实际一致 —— 删减内容后最容易忘记同步
- [ ] 封面或文末含免责声明：机翻仅供参考，以英文原文为准

## 资源

| 文件 | 用途 |
|---|---|
| `scripts/fetch_pages.sh` | 无头 Chromium 批量抓取，含反爬检测与重试 |
| `scripts/discover.py` | 从已抓 HTML 提取候选内链，辅助定范围 |
| `scripts/probe.py` | 单页试提取，打印块数与首几块内容 |
| `scripts/extract.py` | HTML → 结构化 Markdown 块（标题/列表/表格/链接/粗斜体） |
| `scripts/chunk.py` | 切分翻译块 + 生成分批派发计划 |
| `scripts/verify.py` | 翻译完整性校验 |
| `scripts/merge.py` | 合并双语 + 导航清理 |
| `scripts/build_docx.py` | Word 排版引擎 |
| `scripts/export_pdf.ps1` | Word COM 更新域/目录并导出 PDF |
| `scripts/render.py` | PDF 逐页渲染 + 空白页检测 |
| `references/translation-protocol.md` | 子 agent 分批翻译提示词模板与质量规则 |
| `references/glossary-template.md` | 学术出版类术语表（可直接改用） |
| `references/docx-pitfalls.md` | python-docx / Word 域的坑与正确写法 |
