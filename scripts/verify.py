# -*- coding: utf-8 -*-
"""校验翻译完整性。

用法:
    python verify.py            # 校验全部块
    python verify.py 3          # 只校验第 3 批（子 agent 自检用）
    python verify.py c007       # 只校验某一块
"""
import json, os, sys, glob, re

only = sys.argv[1] if len(sys.argv) > 1 else None

if only and only.isdigit():
    batches = json.load(open('_batches.json', encoding='utf-8'))
    want = set()
    for b in batches:
        if b['batch'] == int(only):
            want = set(b['chunks'])
    files = ['chunks/c%03d.json' % c for c in sorted(want)]
elif only:
    files = ['chunks/%s.json' % only]
else:
    files = [f for f in sorted(glob.glob('chunks/c*.json'))
             if not f.endswith('.zh.json')]

rows, bad = [], []
for f in files:
    if not os.path.exists(f):
        rows.append('MISSING FILE %s' % f)
        bad.append(f)
        continue
    t = json.load(open(f, encoding='utf-8'))
    cid, n = t['chunk'], len(t['items'])
    zhp = f[:-5] + '.zh.json'
    if not os.path.exists(zhp):
        rows.append('MISS  c%03d  need=%d  (无译文文件)' % (cid, n))
        bad.append(cid)
        continue
    try:
        z = json.load(open(zhp, encoding='utf-8'))
    except Exception as e:
        rows.append('BADJS c%03d  %s' % (cid, repr(e)[:70]))
        bad.append(cid)
        continue
    zh = z.get('zh') or []
    if len(zh) != n:
        rows.append('COUNT c%03d  need=%d got=%d' % (cid, n, len(zh)))
        bad.append(cid)
        continue

    empty = [i for i, s in enumerate(zh) if not str(s).strip()]
    same = [i for i, s in enumerate(zh)
            if re.sub(r'\s+', '', str(s)) == re.sub(r'\s+', '', t['items'][i]['en'])]
    flag = ''
    if empty:
        flag += '  EMPTY:%s' % empty
    if same:
        # 纯符号/纯 URL/纯数字的块未翻译是正常的
        real = [i for i in same
                if re.search(r'[A-Za-z]{3,}', t['items'][i]['en'])]
        if real:
            flag += '  UNTRANSLATED:%s' % real
    rows.append('OK    c%03d  n=%d%s' % (cid, n, flag))
    if empty:
        bad.append(cid)

txt = '\n'.join(rows) + '\n\nBAD=%s\nTOTAL=%d\n' % (bad, len(files))
open('_verify.txt', 'w', encoding='utf-8').write(txt)
print(txt[-1500:])

if bad:
    sys.exit(1)
