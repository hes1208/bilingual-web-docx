# -*- coding: utf-8 -*-
"""从已抓取的 HTML 中提取候选内链，帮助确定抓取范围。

用法:
    python discover.py html https://www.nature.com/natsustain/
    python discover.py html https://www.nature.com/natsustain/ --write urls_candidate.txt
"""
import os, re, sys, json
from collections import Counter
from urllib.parse import urljoin, urldefrag, urlparse

SKIP_EXT = re.compile(
    r'\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|zip|gz|woff2?|ttf|mp4|mp3)$', re.I)
# 明显不属于正文内容的路径片段
SKIP_HINT = re.compile(
    r'/(login|signin|signup|register|cart|search|tag|tags|author|authors|'
    r'about|contact|privacy|cookies|terms|advertise|subscribe|careers)(/|$)', re.I)


def links_in(raw):
    out = []
    for m in re.finditer(r'<a\b[^>]*?\bhref\s*=\s*["\']([^"\']+)["\']', raw, re.I):
        out.append(m.group(1))
    return out


def main():
    html_dir = sys.argv[1] if len(sys.argv) > 1 else 'html'
    prefix = sys.argv[2] if len(sys.argv) > 2 else ''
    out_file = None
    if '--write' in sys.argv:
        out_file = sys.argv[sys.argv.index('--write') + 1]

    host = urlparse(prefix).netloc if prefix else ''
    cnt = Counter()

    for fn in sorted(os.listdir(html_dir)):
        if not fn.endswith('.html'):
            continue
        raw = open(os.path.join(html_dir, fn), encoding='utf-8', errors='replace').read()
        for href in links_in(raw):
            if href.startswith(('mailto:', 'javascript:', 'tel:', '#')):
                continue
            u = urldefrag(urljoin(prefix or 'http://x/', href))[0]
            p = urlparse(u)
            if host and p.netloc and p.netloc != host:
                continue
            if SKIP_EXT.search(p.path) or SKIP_HINT.search(p.path):
                continue
            if len(p.path) < 2:
                continue
            cnt[u] += 1

    # 按路径分组输出，便于人眼判断层级
    grouped = {}
    for u, c in cnt.items():
        path = urlparse(u).path.rstrip('/')
        depth = path.count('/')
        grouped.setdefault(depth, []).append((path, u, c))

    lines = ['# 候选内链 (共 %d 个唯一 URL)' % len(cnt),
             '# depth | 出现次数 | URL', '']
    for d in sorted(grouped):
        lines.append('--- depth %d (%d 个) ---' % (d, len(grouped[d])))
        for path, u, c in sorted(grouped[d], key=lambda x: -x[2]):
            lines.append('%d | %3d | %s' % (d, c, u))
        lines.append('')

    txt = '\n'.join(lines)
    open('_links.txt', 'w', encoding='utf-8').write(txt)
    print(txt[:3000])
    print('\n... 完整清单见 _links.txt')

    if out_file:
        # 只写与 prefix 同路径前缀的链接
        pre_path = urlparse(prefix).path.rstrip('/') if prefix else ''
        sel = [u for u in sorted(cnt)
               if not pre_path or urlparse(u).path.startswith(pre_path)]
        open(out_file, 'w', encoding='utf-8').write('\n'.join(sel) + '\n')
        print('已写入 %s（%d 条）' % (out_file, len(sel)))


if __name__ == '__main__':
    main()
