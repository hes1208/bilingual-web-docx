# -*- coding: utf-8 -*-
"""把 extracted.json 切成翻译任务块，并按「每批 N 块」生成派发计划。

分批的意义：一个子 agent 处理一批，摊薄固定开销（读术语表/读提示词/校验）。
一块一个 agent 会让成本成倍上升。
"""
import json, os

CFG = {}
if os.path.exists('pipeline.json'):
    CFG = json.load(open('pipeline.json', encoding='utf-8'))

MAXCH = CFG.get('chunk_chars', 6500)        # 单块累计字符上限
BATCH = CFG.get('batch_chunks', 5)          # 每个子 agent 处理的块数
OUT = 'chunks'

os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith('.json'):
        os.remove(os.path.join(OUT, f))

docs = json.load(open('extracted.json', encoding='utf-8'))

manifest, cid = [], 0
for di, d in enumerate(docs):
    if not d['blocks']:
        continue
    cur, curlen, groups = [], 0, []
    for bi, b in enumerate(d['blocks']):
        L = len(b)
        if cur and (curlen + L > MAXCH):
            groups.append(cur)
            cur, curlen = [], 0
        cur.append({'i': bi, 'en': b})
        curlen += L
        if L > MAXCH:                        # 超长单块独占一块
            groups.append(cur)
            cur, curlen = [], 0
    if cur:
        groups.append(cur)

    for g in groups:
        cid += 1
        task = {'chunk': cid, 'doc': di, 'url': d['url'],
                'title': d['title'], 'items': g}
        json.dump(task, open('%s/c%03d.json' % (OUT, cid), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        manifest.append({'chunk': cid, 'doc': di, 'title': d['title'],
                         'n': len(g), 'chars': sum(len(x['en']) for x in g)})

json.dump(manifest, open('%s/_manifest.json' % OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---- 分批派发计划 ----
batches, bi = [], 0
for start in range(0, len(manifest), BATCH):
    bi += 1
    grp = manifest[start:start + BATCH]
    batches.append({
        'batch': bi,
        'chunks': [m['chunk'] for m in grp],
        'total_items': sum(m['n'] for m in grp),
        'total_chars': sum(m['chars'] for m in grp),
        'files': ['chunks/c%03d.json' % m['chunk'] for m in grp],
    })

json.dump(batches, open('_batches.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

rep = ['批次\t块\t项数\t字符数\t文件',
       '----\t--\t----\t------\t----']
for b in batches:
    rep.append('%02d\t%d\t%d\t%d\t%s' % (
        b['batch'], len(b['chunks']), b['total_items'],
        b['total_chars'], ','.join('c%03d' % c for c in b['chunks'])))
rep += [
    '',
    'TOTAL chunks=%d batches=%d docs=%d chars=%d' % (
        len(manifest), len(batches), len(docs),
        sum(m['chars'] for m in manifest)),
    '',
    '派发方式：按批次并行，一个子 agent 一批（%d 块）。' % BATCH,
    '提示词见 references/translation-protocol.md',
]
open('_chunks_report.txt', 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep))
