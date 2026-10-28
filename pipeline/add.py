"""Add approved rows to Splitwise.
usage: LOG=expense-log/log-<tag>.csv add.py [ID,ID,...] [--preview] [--decided-only]
Adds every row tagged `shared` that is not already in expense-log/added.csv (optionally only the listed IDs).
--preview prints what would be added and exits; always preview and get approval for non-auto rows first.
--decided-only skips auto rows (used on the first run, so the user sees everything before anything is auto-added)."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk
from sw import Session

CAT = {'Groceries': 12, 'Dining out': 13, 'Household supplies': 14, 'Cleaning': 48, 'Maintenance': 17, 'Furniture': 16,
       'Rent': 3, 'Electricity': 5, 'Utilities': 5, 'TV/Phone/Internet': 8, 'General': 18}
args = [a for a in sys.argv[1:] if not a.startswith('--')]; preview = '--preview' in sys.argv; decided_only = '--decided-only' in sys.argv
LOG = os.environ.get('LOG') or sys.exit('set LOG=<path to log csv>')
ADDED = bk.EL + 'added.csv'
only = set(args[0].split(',')) if args and args[0] else None
done = {(r['id'], r['date']) for r in csv.DictReader(open(ADDED))} if os.path.exists(ADDED) else set()
rows = [r for r in csv.DictReader(open(LOG)) if r['tag'] == 'shared' and not r.get('splitwise_expense_id')
        and (r['id'], r['date']) not in done and (not only or r['id'] in only) and not (decided_only and r.get('auto'))]

if preview:
    for r in rows:
        print(f"{r['id']:6} {r['date']} {float(r['amount']):>9.2f}  {r['sw_description'][:40]:40} split {r['split'] or '50/50':12} "
              f"{bk.THEM['name']} owes {bk.they_owe(r['amount'], r['split']):.2f}  {'AUTO ' + r['auto'] if r.get('auto') else 'decided'}")
    print(len(rows), 'rows would be added', '(dry run)' if bk.DRY else ''); sys.exit()

new = not os.path.exists(ADDED)
out = open(ADDED, 'a', newline=''); w = csv.writer(out)
if new: w.writerow(['id', 'date', 'amount', 'merchant', 'description', 'split', 'they_owe', 'splitwise_expense_id'])
s = Session() if rows else None
for r in rows:
    cost, k, paid_me, paid_k = bk.parse_split(r['split'], r['amount']); mine = round(cost - k, 2)
    a = {"cost": f"{cost:.2f}", "description": r['sw_description'], "group_id": bk.GROUP_ID, "currency_code": bk.CURRENCY,
         "date": r['date'] + "T12:00:00Z", "category_id": CAT.get(r['sw_category'], 18), "split_equally": False,
         "users": [{"user_id": bk.ME_ID, "paid_share": f"{paid_me:.2f}", "owed_share": f"{mine:.2f}"},
                   {"user_id": bk.THEM_ID, "paid_share": f"{paid_k:.2f}", "owed_share": f"{k:.2f}"}]}
    txt = s.call('create_expense', a)
    try:
        j = json.loads(txt); e = (j.get('expenses') or [j.get('expense') or j])[0]; eid = e.get('id'); errs = j.get('errors')
    except Exception: eid = None; errs = txt[:300]
    if eid and not errs:
        w.writerow([r['id'], r['date'], float(r['amount']), r['merchant'], r['sw_description'], r['split'], round(k - paid_k, 2), eid]); out.flush()
        print('OK', r['id'], eid, r['sw_description'], cost, bk.THEM['name'], 'owes', round(k - paid_k, 2))
    else:
        print('FAIL', r['id'], errs or txt[:300]); break
if s: s.close()
print(len(rows), 'processed', '(dry run: fake Splitwise)' if bk.DRY else '')
