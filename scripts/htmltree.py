# -*- coding: utf-8 -*-
"""轻量 HTML 解析与正文渲染：把 DOM 转成结构化 Markdown 块。

被 extract.py / probe.py / discover.py 共用。
不依赖 bs4 / lxml，只用标准库 HTMLParser。
"""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

VOID = {'br', 'img', 'meta', 'link', 'input', 'hr', 'source', 'col', 'base',
        'area', 'embed', 'param', 'track', 'wbr'}

# 提取正文前整体丢弃的噪声容器
DROP_TAGS = {'script', 'style', 'noscript', 'svg', 'canvas', 'iframe',
             'nav', 'header', 'footer', 'aside', 'form', 'button', 'select',
             'template', 'figure'}

# 这些 class/id 片段命中的容器也丢弃
DROP_ATTR_HINTS = (
    'nav', 'navbar', 'menu', 'breadcrumb', 'sidebar', 'share', 'social',
    'cookie', 'banner', 'footer', 'header', 'toolbar', 'pagination',
    'related', 'promo', 'newsletter', 'skip-link', 'modal', 'popup',
)


class Node:
    __slots__ = ('tag', 'attrs', 'children', 'parent')

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    def get(self, key, default=''):
        return self.attrs.get(key, default)

    @property
    def cls(self):
        return (self.attrs.get('class') or '') + ' ' + (self.attrs.get('id') or '')


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root')
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root:
            if node.tag == tag:
                self.cur = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_file(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    tb = TreeBuilder()
    tb.feed(raw)
    return tb.root, raw


def walk(node, acc=None):
    if acc is None:
        acc = []
    for c in node.children:
        if isinstance(c, Node):
            acc.append(c)
            walk(c, acc)
    return acc


def find(node, pred):
    return [n for n in walk(node) if pred(n)]


def text_of(node):
    if isinstance(node, str):
        return node
    if node.tag in ('script', 'style'):
        return ''
    return ''.join(text_of(c) for c in node.children)


def norm(s):
    s = s.replace('\xa0', ' ').replace('\u200b', '').replace('\u2060', '')
    s = re.sub(r'[ \t\r\n]+', ' ', s)
    return s.strip()


# ---------------- 行内渲染 ----------------

def inline(node, base):
    if isinstance(node, str):
        return node
    t = node.tag
    if t in ('script', 'style'):
        return ''
    if t == 'br':
        return '  \n'
    if t in ('strong', 'b'):
        inner = inner_text(node, base).strip()
        return '**%s**' % inner if inner else ''
    if t in ('em', 'i'):
        inner = inner_text(node, base).strip()
        return '*%s*' % inner if inner else ''
    if t == 'sup':
        inner = inner_text(node, base).strip()
        return '^%s^' % inner if inner else ''
    if t == 'sub':
        inner = inner_text(node, base).strip()
        return '~%s~' % inner if inner else ''
    if t == 'a':
        inner = inner_text(node, base).strip()
        href = node.attrs.get('href', '')
        if href and not href.startswith('#') and not href.startswith('mailto:'):
            return '[%s](%s)' % (inner, urljoin(base, href))
        return inner
    if t == 'img':
        return ''
    return inner_text(node, base)


def inner_text(node, base):
    return ''.join(inline(c, base) for c in node.children)


def cell_text(node, base):
    """单元格：按块级元素切段，段间用 <br> 占位，避免多段被压成一段。"""
    segs, buf = [], []

    def flush():
        if buf:
            t = norm(''.join(buf))
            if t:
                segs.append(t)
            buf.clear()

    for c in node.children:
        if isinstance(c, Node) and c.tag in ('p', 'div', 'ul', 'ol'):
            flush()
            if c.tag in ('ul', 'ol'):
                for li in c.children:
                    if isinstance(li, Node) and li.tag == 'li':
                        t = norm(inner_text(li, base))
                        if t:
                            segs.append(t)
            else:
                t = norm(inner_text(c, base))
                if t:
                    segs.append(t)
        else:
            buf.append(inline(c, base))
    flush()
    return '<br>'.join(segs) if segs else ''


def render_table(node, base):
    rows = []
    for tr in find(node, lambda n: n.tag == 'tr'):
        cells = [x for x in tr.children if isinstance(x, Node) and x.tag in ('td', 'th')]
        if cells:
            rows.append([cell_text(x, base).replace('|', '\\|') for x in cells])
    if not rows:
        return ''
    width = max(len(r) for r in rows)
    rows = [r + [''] * (width - len(r)) for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * width]
    for r in rows[1:]:
        out.append('| ' + ' | '.join(r) + ' |')
    return '\n'.join(out)


def render_block(node, base, depth=0):
    blocks = []
    for c in node.children:
        if isinstance(c, str):
            if c.strip():
                blocks.append(norm(c))
            continue
        t = c.tag
        if t in ('script', 'style', 'noscript'):
            continue
        if c.cls and any(h in c.cls.lower() for h in DROP_ATTR_HINTS):
            continue
        if re.fullmatch(r'h[1-6]', t):
            txt = norm(inner_text(c, base))
            if txt:
                blocks.append('#' * int(t[1]) + ' ' + txt)
        elif t == 'p':
            txt = norm(inner_text(c, base))
            if txt:
                blocks.append(txt)
        elif t in ('ul', 'ol'):
            items, n = [], 0
            for li in [x for x in c.children if isinstance(x, Node) and x.tag == 'li']:
                n += 1
                sub, parts = [], []
                for ch in li.children:
                    if isinstance(ch, Node) and ch.tag in ('ul', 'ol'):
                        sub = render_block(ch, base, depth + 1)
                    else:
                        parts.append(inline(ch, base))
                txt = norm(''.join(parts))
                marker = '- ' if t == 'ul' else '%d. ' % n
                if txt:
                    items.append('  ' * depth + marker + txt)
                for s in sub:
                    items.append('  ' * (depth + 1) + s.lstrip())
            if items:
                blocks.append('\n'.join(items))
        elif t == 'table':
            tb = render_table(c, base)
            if tb:
                blocks.append(tb)
        elif t == 'blockquote':
            inner = render_block(c, base)
            if inner:
                blocks.append('\n'.join('> ' + x for x in inner))
        elif t in ('div', 'section', 'article', 'main'):
            blocks.extend(render_block(c, base, depth))
        else:
            raw = inner_text(c, base)
            if raw.strip():
                txt = norm(raw)
                if txt:
                    blocks.append(('*' + txt + '*') if t == 'figcaption' else txt)
    return [b for b in blocks if b]


def fix_bold_space(s):
    """修复 **粗体** 紧贴相邻单词导致的空格丢失。"""
    out, last = [], 0
    for m in re.finditer(r'\*\*(.+?)\*\*', s):
        st, en = m.span()
        out.append(s[last:st])
        if st > 0 and (s[st - 1].isalnum() or s[st - 1] in '.,;:'):
            out.append(' ')
        out.append(m.group(0))
        if en < len(s) and s[en].isalnum():
            out.append(' ')
        last = en
    out.append(s[last:])
    return re.sub(r' {2,}', ' ', ''.join(out))


# ---------------- 正文容器定位 ----------------

def score_container(node, base):
    """文本密度打分：自身文本量 × log(段落数)，偏向内容多的容器。"""
    txt = norm(text_of(node))
    paras = len(find(node, lambda n: n.tag == 'p'))
    if len(txt) < 200:
        return 0
    return len(txt) * (1 + min(paras, 40) ** 0.5)


def locate_body(root, attr_key=None, attr_val=None):
    """三级策略定位正文容器。

    1. 显式属性选择器（attr_key/attr_val）
    2. 语义标签 main / article / [role=main]
    3. 文本密度打分
    返回 (node, strategy_name)
    """
    if attr_key and attr_val:
        hits = find(root, lambda n: n.attrs.get(attr_key) == attr_val)
        if hits:
            return hits[0], 'attr:%s=%s' % (attr_key, attr_val)

    for tag in ('main', 'article'):
        hits = find(root, lambda n: n.tag == tag)
        if hits:
            best = max(hits, key=lambda n: score_container(n, ''))
            if score_container(best, '') > 0:
                return best, 'tag:' + tag

    hits = find(root, lambda n: n.attrs.get('role') == 'main')
    if hits:
        return hits[0], 'role:main'

    cands = [n for n in walk(root) if n.tag in ('div', 'section', 'article', 'main', 'td')]
    if not cands:
        return root, 'root'
    best = max(cands, key=lambda n: score_container(n, ''))
    return best, 'density'
