"""Prepare review-page documents for one run.
usage: [BATCH=<tag>] [RUN_EXISTS=1] publish_review.py RUN_ID "LABEL" START END LOG_CSV[:TAG] [LOG_CSV[:TAG] ...]
Writes <workspace>/out/<RUN_ID>/<BATCH>/{run.json, rows/*.json, auto/*.json, writes-N.json}. Each writes-N.json is a
list of <=50 ArtifactData batch entries using file_path, ready to pass as `writes`."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk

run, label, start, end = sys.argv[1:5]; logs = sys.argv[5:]
OUT = os.path.join(bk.OUTDIR, run, os.environ.get('BATCH', 'all'))
os.makedirs(OUT + '/rows', exist_ok=True); os.makedirs(OUT + '/auto', exist_ok=True)
AF = bk.EL + 'added.csv'
added = {(a['id'], a['date']): a for a in csv.DictReader(open(AF))} if os.path.exists(AF) else {}
writes, nrows, nauto = [], 0, 0
for spec in logs:
    path, _, tag = spec.partition(':'); tag = tag or os.path.basename(path).replace('log-', '').replace('.csv', '')
    for r in csv.DictReader(open(path)):
        key = f"{tag}__{r['id']}"
        a = added.get((r['id'], r['date'])); sid = r.get('splitwise_expense_id') or (a or {}).get('splitwise_expense_id', '')
        if r.get('auto') and r['tag'] == 'shared' and not sid:  # auto row that add.py did not get to (failed or stopped)
            r['tag'] = 'likely shared'; r['reason'] = r['reason'].replace('AUTO-ADDED', 'Held back from auto-add')
        if r.get('auto') and r['tag'] == 'shared':
            cost = bk.parse_split(r['split'], r['amount'])[0]; owe = bk.they_owe(r['amount'], r['split'])
            doc = dict(date=r['date'], desc=r['sw_description'], rule=r['auto'], amount=float(r['amount']), cost=cost,
                       they_owe=owe, splitwise_id=sid, log=tag, id=r['id'], undo=False)
            p = f'{OUT}/auto/{key}.json'; json.dump(doc, open(p, 'w'), ensure_ascii=False)
            writes.append(dict(op='set', collection=f'runs/{run}/auto', doc_id=key, file_path=p)); nauto += 1
        elif r['tag'] in ('uncertain', 'likely shared') and not sid:
            doc = dict(log=tag, id=r['id'], date=r['date'], source=r['source'], merchant=r['merchant'], detail=r['detail'][:400], amount=float(r['amount']),
                       reason=r['reason'], suggestion=r['tag'], desc=r['sw_description'], cat=r['sw_category'] or 'General', split=r['split'] or '50/50', decision=None)
            p = f'{OUT}/rows/{key}.json'; json.dump(doc, open(p, 'w'), ensure_ascii=False)
            writes.append(dict(op='set', collection=f'runs/{run}/rows', doc_id=key, file_path=p)); nrows += 1
p = f'{OUT}/run.json'; json.dump(dict(label=label, start=start, end=end, status='review', rows=nrows, auto=nauto), open(p, 'w'))
if os.environ.get('RUN_EXISTS') != '1':  # a weekly run collects several daily fetches: create its doc only once
    writes.append(dict(op='set', collection='runs', doc_id=run, file_path=p))
else:
    print('run doc exists: update its end/rows/auto counts with ArtifactData update instead')
for i in range(0, len(writes), 50): json.dump(writes[i:i + 50], open(f'{OUT}/writes-{i // 50 + 1}.json', 'w'))
print(run, 'rows', nrows, 'auto', nauto, 'batches', (len(writes) + 49) // 50, OUT)
