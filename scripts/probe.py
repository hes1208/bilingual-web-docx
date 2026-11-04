# -*- coding: utf-8 -*-
"""单页试提取：打印定位策略、块数与全部块内容，用于确认正文抓取是否正确。

用法:
    python probe.py html/xxx.html https://example.com/page [--all] [--n 40]
"""
import os, re, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import htmltree as H
import extract as E

path = sys.argv[1]
url = sys.argv[2] if len(sys.argv) > 2 else 'http://localhost/'
show_all = '--all' in sys.argv
limit = 40
if '--n' in sys.argv:
    limit = int(sys.argv[sys.argv.index('--n') + 1])

cfg = E.load_cfg() if os.path.exists('pipeline.json') else {}
root, raw = H.parse_file(path)
title = E.find_title(root, raw, cfg)
ba = cfg.get('body_attr')
body, strategy = H.locate_body(root, ba[0] if ba else None, ba[1] if ba else None)

blocks = H.render_block(body, url)
blocks = [H.fix_bold_space(b) for b in blocks]

# 与整页文本对比，判断定位是否抓到了主体
whole = H.norm(H.text_of(root))
got = sum(len(b) for b in blocks)
cover = (got / len(whole) * 100) if whole else 0

lines = [
    'file     : %s (%d bytes)' % (os.path.basename(path), os.path.getsize(path)),
    'url      : %s' % url,
    'title    : %s' % title,
    'strategy : %s' % strategy,
    'blocks   : %d' % len(blocks),
    'chars    : %d / 全页 %d  (覆盖率 %.1f%%)' % (got, len(whole), cover),
    '',
]
if cover > 95:
    lines.append('!! 覆盖率接近 100%%，可能定位到了整个页面而非正文容器，请检查 pipeline.json 的 body_attr')
if cover < 25:
    lines.append('!! 覆盖率过低，正文容器可能定位过深或过浅')

show = blocks if show_all else blocks[:limit]
for i, b in enumerate(show):
    lines.append('%03d| %s' % (i, b[:300].replace('\n', '\n     | ')))
if not show_all and len(blocks) > limit:
    lines.append('... 还有 %d 块（--all 查看全部）' % (len(blocks) - limit))

txt = '\n'.join(lines)
open('_probe.txt', 'w', encoding='utf-8').write(txt)
print(txt[:4000])
