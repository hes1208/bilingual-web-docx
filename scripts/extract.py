# -*- coding: utf-8 -*-
"""HTML 批量提取为结构化 Markdown 块 -> extracted.json

读取同目录 pipeline.json 与 urls.txt。文件名规则必须与 fetch_pages.sh 一致。
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import htmltree as H


def fname(url):
    """URL -> 文件名（与 fetch_pages.sh 的 fname 完全相同）"""
    s = re.sub(r'^https?://', '', url)
    s = re.sub(r'[/?=&#]', '__', s)
    s = re.sub(r'_{3,}', '__', s)
    return s.rstrip('_')


def load_cfg():
    p = 'pipeline.json'
    if not os.path.exists(p):
        raise SystemExit('缺少 pipeline.json')
    return json.load(open(p, encoding='utf-8'))


def read_urls():
    if os.path.exists('urls.json'):
        return json.load(open('urls.json', encoding='utf-8'))
    lines = open('urls.txt', encoding='utf-8').read().split('\n')
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]


def find_title(root, raw, cfg):
    ta = cfg.get('title_attr')
    if ta:
        hits = H.find(root, lambda n: n.attrs.get(ta[0]) == ta[1])
        if hits:
            t = H.norm(H.text_of(hits[0]))
            if t:
                return t
    for tag in ('h1', ):
        hits = H.find(root, lambda n: n.tag == tag)
        if hits:
            t = H.norm(H.text_of(hits[0]))
            if t:
                return t
    m = re.search(r'<title[^>]*>(.*?)</title>', raw, re.S | re.I)
    return H.norm(m.group(1)) if m else ''


def extract(path, url, cfg):
    root, raw = H.parse_file(path)
    title = find_title(root, raw, cfg)
    ba = cfg.get('body_attr')
    body, strategy = H.locate_body(
        root, ba[0] if ba else None, ba[1] if ba else None)
    blocks = H.render_block(body, url)
    blocks = [H.fix_bold_space(b) for b in blocks]
    return {'url': url, 'title': title or url, 'blocks': blocks,
            'strategy': strategy}


def main():
    cfg = load_cfg()
    html_dir = cfg.get('html_dir', 'html')
    min_bytes = cfg.get('min_html_bytes', 20000)
    urls = read_urls()

    docs, rows = [], []
    for url in urls:
        p = os.path.join(html_dir, fname(url) + '.html')
        if not os.path.exists(p):
            docs.append({'url': url, 'title': 'MISSING-FILE', 'blocks': [],
                         'strategy': 'none'})
            rows.append('MISS  %s' % url)
            continue
        if os.path.getsize(p) < min_bytes:
            docs.append({'url': url, 'title': 'BLOCKED', 'blocks': [],
                         'strategy': 'none'})
            rows.append('BLOCK %6d  %s' % (os.path.getsize(p), url))
            continue
        d = extract(p, url, cfg)
        docs.append(d)
        rows.append('OK %-18s %3d blocks %7d chars  %-28s %s' % (
            d['strategy'][:18], len(d['blocks']),
            sum(len(b) for b in d['blocks']), d['title'][:28], url))

    json.dump(docs, open('extracted.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    report = rows + [
        '',
        'TOTAL docs=%d  blocks=%d  chars=%d' % (
            len(docs), sum(len(d['blocks']) for d in docs),
            sum(len(b) for d in docs for b in d['blocks'])),
    ]
    open('_extract_report.txt', 'w', encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report[-6:]))


if __name__ == '__main__':
    main()
