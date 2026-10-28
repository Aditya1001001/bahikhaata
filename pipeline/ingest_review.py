"""Turn decisions made on the review page into decisions.csv entries.
usage: ingest_review.py DUMP_DIR RUN_ID
DUMP_DIR is an ArtifactData out_dir dump of runs/<RUN_ID>/rows (and /auto). Prints what it records; skips rows already
recorded. Lists auto-added entries marked Undo."""
import csv, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk

dump, run = sys.argv[1], sys.argv[2]
DECF = bk.EL + 'decisions.csv'
COLS = ['date', 'amount', 'merchant', 'tag', 'sw_description', 'sw_category', 'split', 'old_id', 'note']
if not os.path.exists(DECF): csv.writer(open(DECF, 'w', newline='')).writerow(COLS)
logs = {}
def logrow(tag, rid):
    f = bk.EL + f'log-{tag}.csv'
    if f not in logs: logs[f] = {r['id']: r for r in csv.DictReader(open(f))} if os.path.exists(f) else {}
    return logs[f].get(rid)
have = {(r['date'], r['amount'], r['merchant'][:8].lower(), r['old_id']) for r in csv.DictReader(open(DECF))}
out, undo = [], []
for p in sorted(glob.glob(f'{dump}/runs/{run}/rows/*.json')):
    j = json.load(open(p)); d = j.get('data', j)
    if d.get('decision') not in ('shared', 'personal'): continue
    L = logrow(d['log'], d['id'])
    if not L: print('NO LOG ROW', d['log'], d['id']); continue
    if (L['date'], L['amount'], L['merchant'][:8].lower(), L['id']) in have: continue
    split = (d.get('d_split') or d.get('split') or '50/50').strip()
    out.append([L['date'], L['amount'], L['merchant'], d['decision'], d.get('d_desc') or d.get('desc') or '', d.get('d_cat') or d.get('cat') or '', split, L['id'], 'from review page'])
for p in sorted(glob.glob(f'{dump}/runs/{run}/auto/*.json')):
    j = json.load(open(p)); d = j.get('data', j)
    if d.get('undo'): undo.append(d)
if out: csv.writer(open(DECF, 'a', newline='')).writerows(out)
for o in out: print(f"{o[7]:6} {o[0]} {float(o[1]):>9.2f} {o[2][:24]:24} {o[3]:8} | {o[4]} | {o[6]}")
print(len(out), 'new decisions recorded;', len(undo), 'auto-added entries marked for undo:', [(u['id'], u['date'], u['desc'], u.get('splitwise_id')) for u in undo])
