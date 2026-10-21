"""Merge data/gold/gold_v3_prefill_part*.jsonl into a copy of the empty data/gold/gold_v3_template.jsonl, written to data/gold/gold_v3_labelled.jsonl.
The template itself stays empty (tests/evaluate/test_gold_v3_template.py).
Also writes data/gold/gold_v3_review.csv (one row per key, CHECK rows first) for Akshat's review.
label_source = claude_chat_prefill; change it to claude_chat_prefill+akshat_verified once each row is checked."""
import json, csv, shutil, datetime, pathlib
D = pathlib.Path(__file__).resolve().parent
T = D / 'gold_v3_template.jsonl'
OUT = D / 'gold_v3_labelled.jsonl'
PS = sorted(D.glob('gold_v3_prefill_part*.jsonl'))
pre = {}
for l in (x for P in PS for x in P.read_text(encoding='utf-8').splitlines()):
    if l.strip():
        r = json.loads(l); pre[(r['ipo_id'], r['key'], r['period'])] = r
rows = [json.loads(l) for l in T.read_text(encoding='utf-8').splitlines() if l.strip()]
now = datetime.date.today().isoformat(); hit = 0
for r in rows:
    p = pre.get((r['ipo_id'], r['key'], r['period']))
    if not p: continue
    hit += 1
    for f in ['value_raw', 'unit', 'page', 'quote', 'status', 'notes']: r[f] = p[f]
    if p.get('doc'): r['doc'] = p['doc']
    r['label_source'] = 'claude_chat_prefill'; r['labelled_at'] = now
    if r['changed_by_akshat'] is None: r['changed_by_akshat'] = False
OUT.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
cols = ['ipo_id', 'key', 'period', 'doc', 'value_raw', 'unit', 'page', 'status', 'quote', 'notes']
srt = sorted(rows, key=lambda r: ('CHECK' not in r['notes'], r['ipo_id']))
with open(D / 'gold_v3_review.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(srt)
print(f'filled {hit}/{len(rows)} rows; missing prefill for {len(rows)-hit}; review sheet: gold_v3_review.csv')
