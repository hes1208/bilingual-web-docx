# -*- coding: utf-8 -*-
"""合并英文原文与中文译文 -> bilingual.json

同时清理导航残留块与源页面的格式噪声。
"""
import json, os, glob, re

CFG = {}
if os.path.exists('pipeline.json'):
    CFG = json.load(open('pipeline.json', encoding='utf-8'))

DROP_PATTERNS = [re.compile(p, re.I) for p in CFG.get('drop_text_patterns', [
    r'^\s*top of page', r'^\s*back to top', r'^\s*skip to',
    r'^\s*on this page\s*$', r'^\s*share this', r'^\s*download\s*$',
    r'^\s*返回页首', r'^\s*回到顶部',
])]
# "On this page" 后面紧跟的目录列表整块丢弃
NAV_HEADER = re.compile(r'^\s*(on this page|本页内容|目录)\s*$', re.I)

docs = json.load(open('extracted.json', encoding='utf-8'))

# ---- 收集译文 ----
zh_map = {}
for f in sorted(glob.glob('chunks/c*.zh.json')):
    t = json.load(open(f, encoding='utf-8'))
    cid = t.get('chunk')
    src_p = 'chunks/c%03d.json' % cid
    if not os.path.exists(src_p):
        continue
    src = json.load(open(src_p, encoding='utf-8'))
    di = src['doc']
    if len(t['zh']) != len(src['items']):
        raise SystemExit('项数不符 c%03d: %d vs %d' % (cid, len(t['zh']), len(src['items'])))
    zh_map.setdefault(di, {})
    for it, zh in zip(src['items'], t['zh']):
        zh_map[di][it['i']] = zh

# ---- 标题中文映射（可选文件，缺失则从首个标题块推导）----
titles_zh = {}
if os.path.exists('titles_zh.json'):
    titles_zh = json.load(open('titles_zh.json', encoding='utf-8'))


def kind_of(b):
    if re.match(r'^#{1,6} ', b):
        return 'heading'
    if b.strip().startswith('|'):
        return 'table'
    if re.match(r'^\s*(- |\d+\. )', b):
        return 'list'
    if set(b.strip()) <= set('_ '):
        return 'rule'
    return 'para'


def clean_md(s):
    """修源页面的零散星号：*X** -> *X*"""
    return re.sub(r'\*([^*\n]+)\*\*', r'*\1*', s)


def derive_title_zh(d, di):
    """优先取 titles_zh.json；否则找与英文标题同名的标题块取译文；
    都找不到就退回英文标题 —— 不要用"第一个标题块"，那常常是 On this page 之类的导航。"""
    if d['title'] in titles_zh:
        return titles_zh[d['title']]
    m = zh_map.get(di, {})
    tk = re.sub(r'\s+', ' ', d['title']).strip().lower()
    for bi, b in enumerate(d['blocks']):
        if kind_of(b) != 'heading':
            continue
        bare = re.sub(r'^#{1,6}\s*', '', b).strip()
        if re.sub(r'\s+', ' ', bare).strip().lower() != tk:
            continue
        z = re.sub(r'^#{1,6}\s*', '', m.get(bi, '')).strip()
        if z:
            return z
        break
    return d['title']


out_docs, dropped = [], 0
for di, d in enumerate(docs):
    items, skip_list = [], False
    m = zh_map.get(di, {})
    for bi, b in enumerate(d['blocks']):
        k = kind_of(b)
        # 导航判断要剥掉标题井号，否则 "## On this page" 会漏网
        bare = re.sub(r'^#{1,6}\s*', '', b).strip()
        if k == 'rule':
            dropped += 1
            continue
        if any(p.match(bare) for p in DROP_PATTERNS):
            dropped += 1
            continue
        if NAV_HEADER.match(bare):
            skip_list = True
            dropped += 1
            continue
        if skip_list and k == 'list':
            skip_list = False
            dropped += 1
            continue
        skip_list = False
        zh = m.get(bi, '')
        if not zh:
            dropped += 1
            continue
        items.append({'en': clean_md(b), 'zh': clean_md(zh), 'kind': k})

    out_docs.append({
        'url': d['url'],
        'title': d['title'],
        'title_zh': derive_title_zh(d, di),
        'items': items,
    })

json.dump(out_docs, open('bilingual.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

rep = ['idx\ttitle\titems\tdropped', '---\t-----\t-----\t-------']
for i, d in enumerate(out_docs):
    rep.append('%d\t%s\t%d\t%d' % (i, d['title'][:52], len(d['items']),
                                   len(docs[i]['blocks']) - len(d['items'])))
rep += ['', 'TOTAL docs=%d items=%d dropped=%d' % (
    len(out_docs), sum(len(d['items']) for d in out_docs), dropped)]
open('_merge_report.txt', 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep[-3:]))

empty = [d['title'] for d in out_docs if not d['items']]
if empty:
    print('WARN 以下篇目没有内容，检查提取或翻译：')
    for t in empty:
        print('  -', t)
