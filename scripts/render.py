# -*- coding: utf-8 -*-
"""PDF 逐页渲染为 PNG，并报告空白页，供视觉验证。

用法:
    python render.py preview.pdf prev/
    python render.py preview.pdf prev/ --pages 0,1,2,3
    python render.py preview.pdf prev/ --find "同行评议"   # 渲染含该词的页
    python render.py preview.pdf prev/ --scale 1.55
"""
import os, sys


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else 'preview.pdf'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'prev'
    scale = 1.55
    pages = None
    find = None

    if '--scale' in sys.argv:
        scale = float(sys.argv[sys.argv.index('--scale') + 1])
    if '--pages' in sys.argv:
        pages = [int(x) for x in sys.argv[sys.argv.index('--pages') + 1].split(',')]
    if '--find' in sys.argv:
        find = sys.argv[sys.argv.index('--find') + 1]

    try:
        import pypdfium2 as pdfium
    except ImportError:
        sys.exit('缺少 pypdfium2，请先 pip install pypdfium2')

    os.makedirs(out_dir, exist_ok=True)
    pdf = pdfium.PdfDocument(pdf_path)
    n = len(pdf)
    print('pages=%d' % n)

    texts = [pdf[i].get_textpage().get_text_range() for i in range(n)]

    # 空白页检测（页码域占 1-2 字符，正常页首也要有几十字符）
    empty = [i + 1 for i, t in enumerate(texts) if len(t.strip()) < 70]
    if empty:
        print('!! 疑似空白页: %s' % empty)
    else:
        print('OK 无空白页')

    # 首页文本摘要，便于确认封面与目录位置
    for i in range(min(4, n)):
        head = texts[i].replace('\n', ' | ')[:110]
        print('  p%d len=%-5d %s' % (i + 1, len(texts[i]), head))

    targets = set()
    if pages:
        targets |= {p - 1 for p in pages if 0 < p <= n}
    else:
        targets |= set(range(min(5, n)))

    if find:
        hits = [i for i, t in enumerate(texts) if find in t]
        print('--find "%s" -> 页 %s' % (find, [h + 1 for h in hits[:5]]))
        targets |= set(hits[:3])

    for i in sorted(targets):
        if 0 <= i < n:
            pdf[i].render(scale=scale).to_pil().save(
                os.path.join(out_dir, 'p%03d.png' % (i + 1)))
    print('rendered %d pages -> %s/' % (len(targets), out_dir))


if __name__ == '__main__':
    main()
