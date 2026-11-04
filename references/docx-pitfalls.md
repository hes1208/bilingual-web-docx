# docx / Word 域的坑与正确写法

按「症状 → 原因 → 正确做法」组织。这些都是实测踩过的，不是理论推测。

---

## 1. 目录是空的，或只显示"正在生成目录……"

**原因**：`w:fldSimple` 对 TOC 域不生效；或用了三段式域缺 `separate`；
或生成后没有让 Word 真正更新域。

**正确做法**：四段式 `fldChar`（begin → instrText → separate → end），保存为 .docx 后
用 Word COM 打开并调用 `TablesOfContents.Item(1).Update()`，**然后必须 Save()**
才能把更新后的目录内容写回文件。

```python
r1 = p.add_run(); e = OxmlElement('w:fldChar')
e.set(qn('w:fldCharType'), 'begin'); e.set(qn('w:dirty'), 'true'); r1._r.append(e)

r2 = p.add_run(); it = OxmlElement('w:instrText')
it.set(qn('xml:space'), 'preserve')
it.text = ' TOC \\o "1-2" \\h \\z \\u '; r2._r.append(it)

r3 = p.add_run(); e = OxmlElement('w:fldChar')
e.set(qn('w:fldCharType'), 'separate'); r3._r.append(e)

p.add_run('正在生成目录……')          # 占位文字

r5 = p.add_run(); e = OxmlElement('w:fldChar')
e.set(qn('w:fldCharType'), 'end'); r5._r.append(e)
```

前提：正文标题必须真正使用 `Heading 1` / `Heading 2` 样式，否则目录里没有条目。
注意 `p.style = doc.styles['Heading 1']` 会覆盖段落格式，**赋值之后**再设
`paragraph_format`。

---

## 2. 文档中多出空白页

**原因**：`doc.add_page_break()` 会新增一个**含分页符的空段落**。当上一页正好排满时，
该段落先被挤到新页，再执行分页 —— 于是产生一张纯空白页。目录页排满时最容易触发。

**正确做法**：一律用 `paragraph.page_break_before = True` 让目标段落自己从新页开始，
不要插入独立的分页符段落。

```python
p = para(doc, ...)
p.paragraph_format.page_break_before = True   # ✅
# doc.add_page_break()                        # ❌
```

若确实需要"先空一段再分页"（扉页垂直定位），把 `page_break_before` 设在**第一个**
占位空段落上。

---

## 3. 扉页标题跑到下一页，或整块内容消失

**原因**：用大 `space_before`（≥190pt）做垂直定位。Word 把"段前间距"算进本段高度，
当一段的段前间距超过剩余页高时，整段被推到下一页。

**正确做法**：用若干固定空段落（`space_before=0, space_after=0, line=1.0`）堆出留白，
每段约 14–16pt，7 段 ≈ 页面四分之一。

```python
for k in range(4):
    sp = para(doc, space_before=0, space_after=0, line=1.0)
    if k == 0:
        sp.paragraph_format.page_break_before = True   # 分页锚点
```

---

## 4. 表格单元格里多个段落被挤成一段

**原因**：`<td>` 内有多个 `<p>`、`<div>`，提取时用 `' '.join()` 归一化，
段与段的边界丢失，所有内容变成一行，可读性极差。

**正确做法**：提取阶段按块级元素切段，用 `<br>` 占位；排版阶段把 `<br>` 还原为段内换行。

```python
# 提取：cell_text() 返回 "第一段<br>第二段"
# 排版：
for k, seg in enumerate(txt.split('<br>')):
    if k:
        p.add_run().add_break()      # 段内换行，不是新段落
    if seg.strip():
        emit_inline(p, seg.strip(), size, DARK)
```

翻译时提示词里必须写明"`<br>` 标记原样保留"，否则 agent 会删掉它。

---

## 5. 表格行被拦腰截断到两页

**原因**：Word 默认允许表格行跨页断裂。

**正确做法**：给每一行加 `w:cantSplit`。

```python
for row in t.rows:
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:cantSplit'))
```

---

## 6. Word 打开提示"内容有问题，是否修复"

**原因**：手工 append 的 XML 元素不满足 schema 规定的**子元素顺序**。
`w:tblPr` 的顺序是 `tblStyle → tblpPr → tblOverlap → bidiVisual → tblStyleRowBandSize
→ tblStyleColBandSize → tblW → jc → tblCellSpacing → tblInd → tblBorders → shd
→ tblLayout → tblCellMar → tblLook`。把 `tblLayout` 追加在末尾就违规。

**正确做法**：优先用 python-docx 的现成属性（`t.autofit = False`、`t.columns[i].width`、
`cell.width`），不要手工拼 `tblW` / `tblLayout`。确需手写时用
`tblPr.insert_element_before(el, *successors)` 插到正确位置。

注：`w:pPr` 的 `w:pBdr` 顺序同样敏感，但 Word 对段落级容忍度较高；
表格级几乎零容忍。

---

## 7. 中文字体不生效，或中英混排字号不一致

**原因**：只设了 `run.font.name`，它只改 `w:ascii` 与 `w:hAnsi`，不影响东亚字体。

**正确做法**：显式设置 `w:rFonts` 的 `w:eastAsia`。

```python
rPr = run._element.get_or_add_rPr()
rf = rPr.find(qn('w:rFonts')) or OxmlElement('w:rFonts')
rf.set(qn('w:ascii'), 'Times New Roman')
rf.set(qn('w:hAnsi'), 'Times New Roman')
rf.set(qn('w:eastAsia'), '宋体')
```

`Normal` 样式也要设一次：`doc.styles['Normal'].element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')`。

---

## 8. 超链接点了没反应

**原因**：直接把 text 塞进 `w:hyperlink` 而没建立关系；或用了普通 run。

**正确做法**：先用 `part.relate_to(url, RT.HYPERLINK, is_external=True)` 建关系，
把返回的 `r_id` 写进 `w:hyperlink` 的 `r:id`，内部再放 `w:r`。

---

## 9. 目录样式太松，把目录撑成两页

**原因**：Word 内置 `TOC 1` / `TOC 2` 样式段前段后间距大、行距宽。

**正确做法**：在 COM 里压紧（脚本已内置），并设 `RightIndent` 给页码留位置：

```powershell
$s = $doc.Styles.Item('TOC 1')
$s.ParagraphFormat.SpaceBefore = 5
$s.ParagraphFormat.SpaceAfter = 2
$s.ParagraphFormat.LineSpacingRule = 0   # 单倍
$s.Font.Size = 10.5
$s.ParagraphFormat.RightIndent = 16
```

压紧后目录重新排布，**要重新确认没有出现空白页**（见第 2 条）。

---

## 10. 封面信息表的左右列不对齐

**原因**：只设了 `column.width` 或只设了 `cell.width`，两者不一致；或者标签后跟了
一个全角空格抵消了右对齐效果。

**正确做法**：`t.autofit = False` + 同时设 `t.columns[i].width` 与每个 `cell.width`；
标签单元格 `alignment = RIGHT`，且 run 文本**不要**带尾部空格。

---

## 11. 页眉左中右错位

**原因**：用 `\t\t` 分隔但页眉没有可用制表位。

**正确做法**：默认页眉段落自带居中 + 右对齐两个制表位（位置约在版心半宽与右边界），
`'左文字\t\t右文字'` 即可。若版心宽度改过，需重新设 `paragraph_format.tab_stops`。

---

## 12. 怎么知道做出来到底几页、有没有空白页

**做法**：
1. 用 Word COM 导出 PDF，同时取 `ComputeStatistics(2)`（页数）、`(0)`（字数）。
2. 用 `pypdfium2` 逐页 `get_textpage().get_text_range()`，**文本长度 < 70 字符的页判为空白页**。
3. 逐页 `render(scale=1.55).to_pil().save(...)`，用视觉检查版面。

没有 Word 时可用 LibreOffice 兜底：
`soffice --headless --convert-to pdf --outdir . out.docx`（目录不会自动更新，需前置换算）。

---

## 13. 反复改文档时的时间成本

每次改动都要「重新生成 docx → COM 打开 → 更新域 → 导出 PDF → 渲染 → 看图」，
一轮几十秒到几分钟。

**因此必须批处理**：先把所有缺陷列成清单（封面留白、目录跨页、表格粘连、空白页……），
一次改完，验一轮。不要发现一个改一个 —— 实测单缺陷循环会把排版阶段的时间放大数倍。

---

## 14. PowerShell 脚本报"Try 语句缺少自己的 Catch 或 Finally 块"

**原因**：`.ps1` 存成了 UTF-8 无 BOM + LF 换行。Windows PowerShell 5.1 解析器对
LF-only 的脚本会在 `try/catch` 处报语法错误，报错行号还指向 `}`，极具误导性。

**正确做法**：`.ps1` 一律写成 **UTF-8 with BOM + CRLF**。

```python
s = open(p, encoding='utf-8').read().replace('\r\n', '\n').replace('\n', '\r\n')
open(p, 'w', encoding='utf-8-sig', newline='').write(s)
```

另：本机未安装 PowerShell 7，**没有 `pwsh`**，只能用
`powershell -NoProfile -ExecutionPolicy Bypass -File script.ps1` 调用。
写进 SKILL.md 的命令行必须是 `powershell`，不要写 `pwsh`。

---

## 15. 篇目标题译成了"On this page"

**原因**：用"正文第一个标题块的译文"当篇目标题。而页面首个标题往往是
`## On this page` 这类导航标题。

**正确做法**：优先用 `titles_zh.json` 显式映射；否则找**与英文标题同名**的标题块
取其译文；仍找不到就退回英文标题。不要用"第一个标题块"。

另外，导航词匹配前要先剥掉 `#` 标题符，否则 `## On this page` 不会被
`^\s*on this page\s*$` 命中，会一路漏到成品里。

