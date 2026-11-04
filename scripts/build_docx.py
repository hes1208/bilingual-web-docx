# -*- coding: utf-8 -*-
"""生成中英对照 Word 文档。读取 bilingual.json + pipeline.json。"""
import json, re, os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT

# ---------------- 配色与字体 ----------------
NAVY = RGBColor(0x1F, 0x38, 0x64)
BLUE = RGBColor(0x2E, 0x5C, 0x8A)
GREY = RGBColor(0x55, 0x55, 0x55)
LGREY = RGBColor(0x80, 0x80, 0x80)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x0B, 0x6E, 0x4F)

EA = '宋体'
EA_TITLE = '微软雅黑'
LATIN = 'Times New Roman'
LATIN_EN = 'Georgia'

CFG = json.load(open('pipeline.json', encoding='utf-8'))
docs = json.load(open('bilingual.json', encoding='utf-8'))

SIZES = {'h_top': 12.2, 'h_sub': 11.0, 'en_para': 9.2, 'zh_para': 10.3,
         'en_list': 9.0, 'zh_list': 10.0, 'table': 8.3, 'doc_title': 16.5,
         'part_title': 25.0, 'cover_title': 40.0}
SIZES.update(CFG.get('sizes', {}))


# ---------------- 底层 ----------------
def set_font(run, size=None, bold=None, italic=None, color=None,
             latin=LATIN, ea=EA):
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run.font.name = latin
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rPr.append(rf)
    rf.set(qn('w:ascii'), latin)
    rf.set(qn('w:hAnsi'), latin)
    rf.set(qn('w:eastAsia'), ea)


def p_border(paragraph, side='left', color='DCDCDC', sz=14, space=6):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = pPr.find(qn('w:pBdr'))
    if pbdr is None:
        pbdr = OxmlElement('w:pBdr')
        pPr.append(pbdr)
    el = OxmlElement('w:' + side)
    el.set(qn('w:val'), 'single')
    el.set(qn('w:sz'), str(sz))
    el.set(qn('w:space'), str(space))
    el.set(qn('w:color'), color)
    pbdr.append(el)


def add_hyperlink(paragraph, url, text, size=10, color='1F5C99'):
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    hl = OxmlElement('w:hyperlink')
    hl.set(qn('r:id'), r_id)
    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), LATIN)
    rf.set(qn('w:hAnsi'), LATIN)
    rf.set(qn('w:eastAsia'), EA)
    rPr.append(rf)
    c = OxmlElement('w:color')
    c.set(qn('w:val'), color)
    rPr.append(c)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(size * 2)))
    rPr.append(sz)
    run.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    t.set(qn('xml:space'), 'preserve')
    run.append(t)
    hl.append(run)
    paragraph._p.append(hl)


LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
ITAL_RE = re.compile(r'\*(.+?)\*')


def emit_inline(paragraph, text, size, color, latin=LATIN, bold=False,
                italic=False, ea=EA):
    pos = 0
    for m in LINK_RE.finditer(text):
        _emit_plain(paragraph, text[pos:m.start()], size, color, latin, bold, italic, ea)
        add_hyperlink(paragraph, m.group(2), m.group(1), size=size)
        pos = m.end()
    _emit_plain(paragraph, text[pos:], size, color, latin, bold, italic, ea)


def _emit_plain(paragraph, text, size, color, latin, bold, italic, ea=EA):
    if not text:
        return
    tokens, pos = [], 0
    for m in BOLD_RE.finditer(text):
        if m.start() > pos:
            tokens.append((text[pos:m.start()], False, italic))
        tokens.append((m.group(1), True, italic))
        pos = m.end()
    if pos < len(text):
        tokens.append((text[pos:], False, italic))
    final = []
    for seg, b, it in tokens:
        p2 = 0
        for m in ITAL_RE.finditer(seg):
            if m.start() > p2:
                final.append((seg[p2:m.start()], b, it))
            final.append((m.group(1), b, True))
            p2 = m.end()
        if p2 < len(seg):
            final.append((seg[p2:], b, it))
    for seg, b, it in final:
        seg = seg.replace('\u200b', '').replace('*', '')
        if not seg:
            continue
        r = paragraph.add_run(seg)
        set_font(r, size, bold=b or bold, italic=it, color=color, latin=latin, ea=ea)


def para(doc, space_before=0, space_after=0, line=1.4, indent=0,
         align=None, keep=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent:
        pf.left_indent = Cm(indent)
    if align is not None:
        p.alignment = align
    if keep:
        pf.keep_with_next = True
    return p


# ---------------- 表格 ----------------
def parse_md_table(block):
    rows = []
    for line in block.strip().split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            continue
        if re.fullmatch(r'\|[\s\-:|]+\|', line):
            continue
        rows.append([c.strip() for c in line.strip('|').split('|')])
    return rows


def render_table(doc, rows, size=8.3, header_fill='DCE6F1', widths=None):
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncol)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    if widths is None:
        widths = [0.30, 0.70] if ncol == 2 else [1.0 / ncol] * ncol
    total = 15.2
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci in range(ncol):
            txt = row[ci] if ci < len(row) else ''
            cell = cells[ci]
            cell.width = Cm(total * widths[ci])
            cell.text = ''
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.18
            # <br> 占位必须还原成段内换行，否则多段会挤成一段
            for k, seg in enumerate(txt.split('<br>')):
                if k:
                    p.add_run().add_break()
                if seg.strip():
                    emit_inline(p, seg.strip(), size, DARK)
            if ri == 0 and header_fill:
                tcPr = cell._tc.get_or_add_tcPr()
                sh = OxmlElement('w:shd')
                sh.set(qn('w:val'), 'clear')
                sh.set(qn('w:color'), 'auto')
                sh.set(qn('w:fill'), header_fill)
                tcPr.append(sh)
                for r in p.runs:
                    r.bold = True
    # 行不跨页断裂
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))


# ---------------- 内容块 ----------------
def render_block(doc, item):
    en, zh, kind = item['en'], item['zh'], item['kind']

    if kind == 'heading':
        m = re.match(r'^(#{1,6})\s*(.*)$', en, re.S)
        lvl = len(m.group(1))
        en_t = m.group(2).strip()
        mz = re.match(r'^(#{1,6})\s*(.*)$', zh, re.S)
        zh_t = mz.group(2).strip() if mz else zh
        size = SIZES['h_top'] if lvl <= 2 else SIZES['h_sub']
        p = para(doc, space_before=13 if lvl <= 2 else 9, space_after=1,
                 line=1.25, keep=True)
        emit_inline(p, zh_t, size, NAVY if lvl <= 2 else BLUE, ea=EA_TITLE, bold=True)
        p2 = para(doc, space_before=0, space_after=5, line=1.2, keep=True)
        emit_inline(p2, en_t, size - 2.0, LGREY, latin=LATIN_EN, italic=True)
        p_border(p2, 'bottom', 'DCE3EC', 6, 3)
        return

    if kind == 'table':
        p = para(doc, space_before=9, space_after=3, line=1.2, keep=True)
        r = p.add_run('EN 原文')
        set_font(r, 7.5, bold=True, color=LGREY, latin=LATIN_EN)
        render_table(doc, parse_md_table(en), SIZES['table'])
        p = para(doc, space_before=7, space_after=3, line=1.2, keep=True)
        r = p.add_run('ZH 中文')
        set_font(r, 7.5, bold=True, color=ACCENT, latin=LATIN_EN)
        render_table(doc, parse_md_table(zh), SIZES['table'], header_fill='E4EFE9')
        para(doc, space_before=0, space_after=2, line=1.0)
        return

    if kind == 'list':
        en_lines, zh_lines = en.split('\n'), zh.split('\n')
        n = max(len(en_lines), len(zh_lines))
        for i in range(n):
            e = en_lines[i] if i < len(en_lines) else ''
            z = zh_lines[i] if i < len(zh_lines) else ''
            mm = re.match(r'^(\s*)', e)
            lvl = min(len(mm.group(1)) // 2, 2) if mm else 0
            e2 = re.sub(r'^\s*-\s+', '•  ', e)
            z2 = re.sub(r'^\s*-\s+', '•  ', z)
            e2 = re.sub(r'^\s*(\d+)\.\s+', r'\1.  ', e2)
            z2 = re.sub(r'^\s*(\d+)\.\s+', r'\1.  ', z2)
            pe = para(doc, space_before=4, space_after=0, line=1.3,
                      indent=0.5 + 0.6 * lvl, keep=True)
            emit_inline(pe, e2, SIZES['en_list'], GREY, latin=LATIN_EN)
            pz = para(doc, space_before=1, space_after=4, line=1.32,
                      indent=0.5 + 0.6 * lvl)
            emit_inline(pz, z2, SIZES['zh_list'], DARK)
        return

    pe = para(doc, space_before=7, space_after=0, line=1.38, indent=0.2, keep=True)
    emit_inline(pe, en, SIZES['en_para'], GREY, latin=LATIN_EN)
    p_border(pe, 'left', 'DCDCDC', 14, 6)
    pz = para(doc, space_before=2, space_after=7, line=1.42, indent=0.2)
    emit_inline(pz, zh, SIZES['zh_para'], DARK)
    p_border(pz, 'left', '9CC3B2', 14, 6)


# ---------------- 目录域（四段式，必须） ----------------
def add_toc(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run()
    b = OxmlElement('w:fldChar')
    b.set(qn('w:fldCharType'), 'begin')
    b.set(qn('w:dirty'), 'true')
    r._r.append(b)

    r2 = p.add_run()
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' TOC \\o "1-2" \\h \\z \\u '
    r2._r.append(instr)

    r3 = p.add_run()
    sep = OxmlElement('w:fldChar')
    sep.set(qn('w:fldCharType'), 'separate')
    r3._r.append(sep)

    r4 = p.add_run('正在生成目录……')
    set_font(r4, 9, color=LGREY)

    r5 = p.add_run()
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    r5._r.append(end)
    return p


# ---------------- 分部归属 ----------------
def attach_parts():
    """按英文标题把 docs 分到各 part，未归属的进最后一部分。"""
    def key(s):
        return re.sub(r'\s+', ' ', s).strip().lower()

    idx_of = {}
    for i, d in enumerate(docs):
        idx_of[key(d['title'])] = i

    parts, used = [], set()
    for pt in CFG.get('parts', []):
        idxs = []
        for t in pt.get('docs', []):
            i = idx_of.get(key(t))
            if i is None:
                print('WARN 未匹配到篇目: %s' % t)
                continue
            if i in used:
                continue
            idxs.append(i)
            used.add(i)
        parts.append({**pt, 'idxs': idxs})

    rest = [i for i in range(len(docs)) if i not in used]
    if rest:
        parts.append({
            'title_zh': '其他', 'title_en': 'Others',
            'desc': '未归属到上述分部的篇目。',
            'idxs': rest,
        })
    return parts


# ---------------- 主构建 ----------------
def build():
    cover = CFG.get('cover', {})
    sec_cfg = CFG.get('section', {})

    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = Cm(2.3)
    s.top_margin = Cm(2.1)
    s.bottom_margin = Cm(1.9)
    s.header_distance = Cm(1.0)
    s.footer_distance = Cm(0.9)

    st = doc.styles['Normal']
    st.font.name = LATIN
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), EA)

    for hs, sz in (('Heading 1', 25), ('Heading 2', 16.5)):
        sty = doc.styles[hs]
        sty.font.name = LATIN
        sty.font.size = Pt(sz)
        sty.font.bold = True
        sty.font.color.rgb = NAVY
        sty.element.rPr.rFonts.set(qn('w:eastAsia'), EA_TITLE)

    # ===== 封面 =====
    p = para(doc, space_before=168, space_after=0, line=1.0,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    set_font(p.add_run(cover.get('kicker', '')), 12.5, bold=True,
             color=ACCENT, latin=LATIN)

    p = para(doc, space_before=26, space_after=8, line=1.15,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    set_font(p.add_run(cover.get('title_zh', '文档')), SIZES['cover_title'],
             bold=True, color=NAVY, ea=EA_TITLE)

    p = para(doc, space_before=0, space_after=4, line=1.15,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    set_font(p.add_run(cover.get('subtitle_zh', '中 英 对 照 版')), 19,
             bold=True, color=BLUE, ea=EA_TITLE)

    if cover.get('subtitle_en'):
        p = para(doc, space_before=6, space_after=0, line=1.3,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        set_font(p.add_run(cover['subtitle_en']), 11.5, color=LGREY,
                 latin=LATIN_EN, italic=True)

    para(doc, space_before=22, space_after=0, line=1.0)

    meta = cover.get('meta', [])
    if meta:
        t = doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        t.columns[0].width = Cm(3.8)
        t.columns[1].width = Cm(9.6)
        for k, v in meta:
            cells = t.add_row().cells
            cells[0].width = Cm(3.8)
            cells[1].width = Cm(9.6)
            p0 = cells[0].paragraphs[0]
            p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p0.paragraph_format.space_before = Pt(3)
            p0.paragraph_format.space_after = Pt(3)
            set_font(p0.add_run(k), 9, color=LGREY, ea=EA_TITLE, bold=True)
            p1 = cells[1].paragraphs[0]
            p1.paragraph_format.space_before = Pt(3)
            p1.paragraph_format.space_after = Pt(3)
            set_font(p1.add_run(v), 9, color=GREY)

    if cover.get('footnote'):
        p = para(doc, space_before=112, space_after=0, line=1.4,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        set_font(p.add_run(cover['footnote']), 8.5, color=LGREY, italic=True)

    # ===== 目录 =====
    p = para(doc, space_before=0, space_after=4, line=1.2)
    p.paragraph_format.page_break_before = True    # 不要用 add_page_break()
    set_font(p.add_run(cover.get('toc_title', '目　录')), 22, bold=True,
             color=NAVY, ea=EA_TITLE)
    p = para(doc, space_before=0, space_after=12, line=1.0)
    p_border(p, 'bottom', 'C9D3E0', 8, 4)
    add_toc(doc)

    # ===== 正文 =====
    for part in attach_parts():
        idxs = part['idxs']
        if not idxs:
            continue
        many = len(idxs) > 15
        top_pad = 2 if many else 4
        gap = 1.5 if many else 3

        # 用固定空段落做垂直定位；不要把大 space_before 用在标题上（会被推到下一页）
        for k in range(top_pad):
            sp = para(doc, space_before=0, space_after=0, line=1.0)
            if k == 0:
                sp.paragraph_format.page_break_before = True

        p = para(doc, space_before=0, space_after=6, line=1.2)
        set_font(p.add_run(part['title_zh']), SIZES['part_title'], bold=True,
                 color=NAVY, ea=EA_TITLE)
        p.style = doc.styles['Heading 1']
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)

        p = para(doc, space_before=2, space_after=10, line=1.2)
        set_font(p.add_run(part.get('title_en', '')), 12.5, color=BLUE,
                 latin=LATIN_EN, italic=True)

        if part.get('desc'):
            p = para(doc, space_before=0, space_after=8, line=1.55)
            set_font(p.add_run(part['desc']), 10, color=GREY)

        p = para(doc, space_before=0, space_after=20, line=1.0)
        p_border(p, 'bottom', 'C9D3E0', 8, 4)

        # 本篇目次
        p = para(doc, space_before=0, space_after=7, line=1.2)
        set_font(p.add_run(cover.get('part_toc_label', '本篇目次  CONTENTS')),
                 7.8, bold=True, color=LGREY, ea=EA_TITLE)
        for k, di in enumerate(idxs, 1):
            dd = docs[di]
            pl = para(doc, space_before=gap, space_after=gap, line=1.2)
            pl.paragraph_format.left_indent = Cm(0.2)
            set_font(pl.add_run('%02d  ' % k), 8.5,
                     color=RGBColor(0xB0, 0xBD, 0xCB), latin=LATIN)
            set_font(pl.add_run(dd['title_zh']), 9.5, color=GREY, ea=EA_TITLE)
            set_font(pl.add_run('   ' + dd['title']), 7.6,
                     color=RGBColor(0xA6, 0xA6, 0xA6), latin=LATIN_EN, italic=True)
        p = para(doc, space_before=0, space_after=0, line=1.0)
        p_border(p, 'bottom', 'E6EBF2', 6, 2)

        # 各篇正文
        for k, di in enumerate(idxs, 1):
            d = docs[di]
            long_doc = len(d['items']) >= 9
            p = para(doc, space_before=0 if long_doc else 26,
                     space_after=2, line=1.15)
            set_font(p.add_run('%02d' % k), 19, bold=True,
                     color=RGBColor(0xC3, 0xD0, 0xE0), latin=LATIN)
            set_font(p.add_run('  '), 19, color=RGBColor(0xC3, 0xD0, 0xE0), latin=LATIN)
            set_font(p.add_run(d['title_zh']), SIZES['doc_title'], bold=True,
                     color=NAVY, ea=EA_TITLE)
            p.style = doc.styles['Heading 2']
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            if long_doc:
                p.paragraph_format.page_break_before = True

            p2 = para(doc, space_before=1, space_after=3, line=1.2)
            set_font(p2.add_run(d['title']), 10.5, color=BLUE,
                     latin=LATIN_EN, italic=True)

            p3 = para(doc, space_before=0, space_after=10, line=1.15)
            set_font(p3.add_run(cover.get('url_label', '源链接  ')), 7.5,
                     color=LGREY, ea=EA_TITLE)
            add_hyperlink(p3, d['url'], d['url'], size=7.5)
            p_border(p3, 'bottom', 'C9D3E0', 8, 4)

            for it in d['items']:
                render_block(doc, it)

    # ===== 页眉页脚 =====
    for section in doc.sections:
        hp = section.header.paragraphs[0]
        hp.text = ''
        hp.paragraph_format.space_after = Pt(3)
        set_font(hp.add_run(sec_cfg.get('header_left', '')), 7.6,
                 color=LGREY, latin=LATIN_EN)
        set_font(hp.add_run('\t\t' + sec_cfg.get('header_right', '中英对照版')),
                 7.6, color=LGREY, ea=EA_TITLE)
        p_border(hp, 'bottom', 'D9D9D9', 6, 4)

        fp = section.footer.paragraphs[0]
        fp.text = ''
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(fp.add_run('—  '), 8, color=LGREY)
        fld = OxmlElement('w:fldSimple')
        fld.set(qn('w:instr'), 'PAGE')
        rr = OxmlElement('w:r')
        tt = OxmlElement('w:t')
        tt.text = '1'
        rr.append(tt)
        fld.append(rr)
        fp._p.append(fld)
        set_font(fp.add_run('  —'), 8, color=LGREY)

    cp = doc.core_properties
    cp.title = (cover.get('title_zh', '') + ' 中英对照版').strip()
    cp.subject = cover.get('subtitle_en', '')
    cp.author = 'WorkBuddy'
    cp.comments = cover.get('source', CFG.get('source_url', ''))

    out = CFG.get('output', 'bilingual.docx')
    doc.save(out)
    print('saved %s  %.0f KB' % (out, os.path.getsize(out) / 1024))
    print('docs=%d  items=%d' % (len(docs), sum(len(d['items']) for d in docs)))


if __name__ == '__main__':
    build()
