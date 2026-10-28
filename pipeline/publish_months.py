"""Build calendar month documents for the review page.
usage: publish_months.py [YYYY-MM ...]   (default: every month with data)
Writes <workspace>/out/months/<YYYY-MM>.json and writes.json (ArtifactData batch entries, collection "months").
Each day: shared, logged, pending, them, and items [[kind, label, amount, status]] with status
L=logged in Splitwise, P=to review, K=the flatmate's entry. Your personal spending is never published."""
import csv, json, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk

state = bk.load_state()
AF = bk.EL + 'added.csv'
added = list(csv.DictReader(open(AF))) if os.path.exists(AF) else []
added_ids = {a['splitwise_expense_id'] for a in added}
added_key = {(a['date'], round(float(a['amount']), 2), a['merchant']) for a in added}
RULES = json.load(open(os.path.join(bk.WS, 'rules.json')))
SKIP = bk.rx(RULES.get('never_expenses', []) + [r'add money', r'card bill'])
days = defaultdict(lambda: dict(shared=0.0, logged=0.0, pending=0.0, them=0.0, items=[]))
def short(s, n=34): s = re.sub(r'\s+', ' ', s or '').strip(); return s if len(s) <= n else s[:n - 1] + '…'

# 1. my payments from every period log
for p in state['periods'].values():
    f = bk.EL + p['log']
    if not os.path.exists(f): continue
    for r in csv.DictReader(open(f)):
        a = float(r['amount'] or 0); txt = ' '.join([r['merchant'], r['paid_via'], r['reason']])
        if a <= 0 or SKIP.search(txt) or bk.PEOPLE_RX.search(txt) or 'Already in Splitwise' in r['reason']: continue
        d = days[r['date']]; label = short(r['sw_description'] or r['merchant']); sp = r.get('split') or ''
        portion = float(sp.split('@')[1]) if '@' in sp and not sp.upper().startswith('RENT') else a
        if r['tag'] == 'shared' and (r.get('splitwise_expense_id') or (r['date'], round(a, 2), r['merchant']) in added_key):
            d['shared'] += portion; d['logged'] += portion; d['items'].append(['me', label, round(portion, 2), 'L'])
        elif r['tag'] in ('shared', 'uncertain', 'likely shared'):
            d['pending'] += portion; d['items'].append(['me', label, round(portion, 2), 'P'])
            if r['tag'] == 'shared': d['shared'] += portion

# 2. Splitwise: the flatmate's entries, and mine the pipeline didn't add
SWF = bk.RAW0 + 'splitwise_all.json'
for e in (json.load(open(SWF)) if os.path.exists(SWF) else []):
    if e.get('deleted_at') or e.get('payment'): continue
    payer = [int(u.get('user_id') or u['user']['id']) for u in e['users'] if float(u['paid_share']) > 0]
    dt = e['date'][:10]; c = float(e['cost'])
    if payer == [bk.THEM_ID]:
        d = days[dt]; d['them'] += c; d['items'].append(['them', short(e['description']), round(c, 2), 'K'])
    elif payer == [bk.ME_ID] and str(e['id']) not in added_ids:
        d = days[dt]; d['shared'] += c; d['logged'] += c; d['items'].append(['me', short(e['description']), round(c, 2), 'L'])

months = defaultdict(dict)
order = {'P': 0, 'L': 1, 'K': 2}
for dt, d in days.items():
    for k in ('shared', 'logged', 'pending', 'them'): d[k] = round(d[k], 2)
    d['items'].sort(key=lambda x: (order[x[3]], -x[2])); months[dt[:7]][dt] = d
want = set(sys.argv[1:]) or set(months)
OUT = os.path.join(bk.OUTDIR, 'months'); os.makedirs(OUT, exist_ok=True)
FIRST = bk.CFG.get('history_start', '0000-00')[:7]
writes = []
for m in sorted(want):
    if m not in months or m < FIRST: continue
    ds = months[m]
    tot = {k: round(sum(x[k] for x in ds.values()), 2) for k in ('shared', 'logged', 'pending', 'them')}
    p = f'{OUT}/{m}.json'; json.dump(dict(month=m, totals=tot, days=ds), open(p, 'w'), ensure_ascii=False)
    writes.append(dict(op='set', collection='months', doc_id=m, file_path=p))
    print(m, tot, f'{os.path.getsize(p) // 1024}KB')
json.dump(writes, open(f'{OUT}/writes.json', 'w'))
