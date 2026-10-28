"""Bahikhaata build: merge raw sources for one period, classify, apply decisions + auto-add rules.
usage: build.py --raw RAW_DIR --start YYYY-MM-DD --end YYYY-MM-DD --tag TAG
Reads RAW_DIR/{emails,fold,bank}.csv (any that exist), expense-log/raw/splitwise_all.json, the workspace rules.json
and expense-log/decisions.csv. Writes expense-log/log-TAG.csv."""
import argparse, csv, itertools, json, os, re, sys
from collections import Counter
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk

ap = argparse.ArgumentParser(); ap.add_argument('--raw', required=True); ap.add_argument('--start', required=True)
ap.add_argument('--end', required=True); ap.add_argument('--tag', required=True)
ARGS = ap.parse_args()
RAW = ARGS.raw.rstrip('/') + '/'; TAG = ARGS.tag; START, END = ARGS.start, ARGS.end
RULES = json.load(open(os.path.join(bk.WS, 'rules.json')))
THEM = bk.THEM['name']

def d(s): return date.fromisoformat(s[:10])
def amt(s):
    try: return round(float(str(s).replace(',', '')), 2)
    except: return None
def rd(name): return list(csv.DictReader(open(RAW + name))) if os.path.exists(RAW + name) else []
def near(a, b, days=1): return abs((a - b).days) <= days

emails = [e for e in rd('emails.csv') if START <= e['date'][:10] <= END]
# Fold and a plain bank-statement CSV share one format (see references/sources.md)
fold = [f for f in rd('fold.csv') + rd('bank.csv') if START <= f['date'][:10] <= END]
SWF = bk.RAW0 + 'splitwise_all.json'
SWALL = json.load(open(SWF)) if os.path.exists(SWF) else []
sw = [{'date': e['date'][:10], 'description': e['description'], 'cost': e['cost'], 'deleted': bool(e.get('deleted_at')), 'payment': bool(e.get('payment'))} for e in SWALL]

for e in emails:
    e['_d'] = d(e['date']); e['_a'] = amt(e['amount']); e['_used'] = False
    e['sender'] = 'swiggy' if 'swiggy' in e['sender'] else ('zomato' if 'zomato' in e['sender'] else e['sender'])
    if e['kind'] == 'bill': e['kind'] = 'other'
    if e['kind'] == 'other' and e['_a'] == 0: e['_a'] = None
    addr = e.get('delivery_address') or ''
    if bk.is_home(addr) or addr.startswith('Home'): e['delivery_address'] = bk.HOME_LABEL
    elif e['kind'] in ('food', 'instamart') and addr and 'dine' not in addr.lower(): e['delivery_address'] = 'NOT HOME: ' + addr
for f in fold:
    f['_d'] = d(f['date']); f['_a'] = amt(f['amount'])
    for k in ('merchant_name', 'category', 'excluded_from_cash_flow', 'id'): f.setdefault(k, '')

rows = []
def add(src, dt, merchant, detail, amount, where='', pay='', ref=''):
    r = dict(src=src, date=dt, merchant=merchant, detail=detail, amount=amount, where=where, pay=pay, ref=ref); rows.append(r); return r

# --- 1. receipts from email ---
orders = [e for e in emails if e['kind'] in ('food', 'instamart', 'amazon', 'other', 'grocery')]
alerts = [e for e in emails if e['kind'] == 'bank_alert' and e['_a'] and 'declined' not in e['items'].lower()]
for o in orders:
    if o['kind'] == 'other' and not o['_a']: continue
    src = {'food': 'Swiggy' if o['sender'] == 'swiggy' else 'Zomato', 'instamart': 'Instamart', 'amazon': 'Amazon', 'other': 'Email', 'grocery': 'Grocery'}[o['kind']]
    if 'dineout' in o['items'].lower() or 'dine' in (o['delivery_address'] or '').lower(): src = 'Swiggy Dineout' if o['sender'] == 'swiggy' else 'Zomato'
    o['_row'] = add(src, o['_d'], o['merchant'], o['items'], o['_a'], o['delivery_address'], o['payment_method'], o['order_id'] or o['email_id'])

# card alerts that duplicate a receipt (single order, or several Amazon orders summed)
GROC_RX = bk.rx(RULES.get('grocery_merchants', []))
fam = lambda t: 'grocery' if GROC_RX.search(t) else next((k for k in ('swiggy', 'instamart', 'zomato', 'amazon') if k in t.lower()), None)
def ofam(o): return 'swiggy' if o['kind'] == 'instamart' or (o['kind'] == 'food' and o['sender'] == 'swiggy') else ('zomato' if o['kind'] == 'food' else o['kind'])
for tol in (2, 12):
    for a in alerts:
        if a['_used']: continue
        af = fam(a['merchant']); af = 'swiggy' if af == 'instamart' else af
        m = sorted([o for o in orders if not o.get('_alerted') and o['_a'] and near(o['_d'], a['_d']) and abs(o['_a'] - a['_a']) <= tol and af and af == ofam(o)], key=lambda o: abs(o['_a'] - a['_a']))
        if m: m[0]['_alerted'] = True; a['_used'] = True
for a in alerts:
    if a['_used']: continue
    am = [o for o in orders if o['kind'] == 'amazon' and not o.get('_alerted') and near(o['_d'], a['_d'])]
    for k in range(2, 4):
        hit = next((c for c in itertools.combinations(am, k) if abs(sum(x['_a'] for x in c) - a['_a']) <= 2), None)
        if hit:
            for x in hit: x['_alerted'] = True
            a['_used'] = True; break
for a in alerts:
    if a['_used'] or 'statement' in a['merchant'].lower(): continue
    add('Card', a['_d'], a['merchant'], 'card charge, no receipt found', a['_a'], '', a['payment_method'], a['email_id'])

# --- 2. bank debits (drop ones already covered by a receipt or card row) ---
for f in fold:
    nar = f['narration']
    if str(f['excluded_from_cash_flow']).lower() == 'true' or 'self transfer' in f['category'].lower(): continue
    dup = next((r for r in rows if r['src'] != 'Fold' and r['amount'] and near(r['date'], f['_d']) and abs(r['amount'] - f['_a']) <= 15
                and fam(nar + ' ' + f['merchant_name']) and fam(nar + ' ' + f['merchant_name']) in ('swiggy', 'instamart', 'zomato', 'amazon', 'grocery')
                and fam(r['src'] + ' ' + r['merchant'])), None)
    if dup: dup['pay'] = (dup['pay'] + ' / bank').strip(' /'); continue
    payee = re.split(r'/', nar)[3].strip() if nar.startswith('UPI/') and nar.count('/') >= 3 else nar[:40]
    add('Fold', f['_d'], f['merchant_name'] or payee, payee if payee.lower() != (f['merchant_name'] or '').lower() else '', f['_a'], '', f['category'], f['id'])
rows.sort(key=lambda r: (r['date'], r['src']))

# --- 3. classify ---
def C(tag, why, desc='', cat=''): return tag, why, desc, cat
SHORT = lambda s: re.sub(r'\s*\(.*?\)', '', s).strip()
SH_RX, PE_RX = bk.rx(RULES.get('household_items', [])), bk.rx(RULES.get('personal_items', []))
SKIP_RX = bk.rx(RULES.get('never_expenses', []))
NEVER = [(bk.rx([n['match']]), n['why']) for n in RULES.get('never_add', [])]
EATOUT_RX = bk.rx(RULES.get('eating_out_merchants', []))
RENT_RX = bk.rx([bk.RENT.get('landlord_pattern', '')]) if bk.RENT.get('mode', 'off') != 'off' else bk.rx([])

def rent_month(dt):
    if bk.RENT.get('pays_for', 'previous_month') == 'previous_month': dt = dt.replace(day=1) - timedelta(days=1)
    return dt.strftime('%b %Y')

def classify(r):
    m, det, a, src, where = r['merchant'], r['detail'], r['amount'], r['src'], r['where']
    ml = (m + ' ' + det).lower(); pay = r['pay'].lower()
    for pat, why in NEVER:
        if pat.search(ml): return C('likely personal', why)
    if src in ('Swiggy', 'Zomato'):
        if 'NOT HOME' in where: return C('likely personal', f'Delivered away from home ({where.split(":", 1)[1].split(",")[0].strip()})')
        if a >= RULES.get('food_for_two_from', 600) or re.search(r'x[2-9]\b|serves 2|family|for two|combo for 2', det, re.I):
            return C('uncertain', f'Order for two? {det[:60]}', f'Food - {SHORT(m)}', 'Dining out')
        return C('likely personal', "Looks like one person's order")
    if src == 'Swiggy Dineout': return C('uncertain', f'Dine-out bill ₹{a:,.0f} - was {THEM} there?', f'Dinner - {SHORT(m)}', 'Dining out')
    if src == 'Grocery': return C('likely shared', f'{m} groceries delivered home', f'Grocery - {m}', 'Groceries')
    if src == 'Instamart':
        if 'NOT HOME' in where: return C('likely personal', 'Instamart order delivered away from home')
        return C('likely shared', 'Groceries delivered home', 'Grocery - Instamart', 'Groceries')
    if src == 'Amazon':
        sh, pe = SH_RX.search(ml), PE_RX.search(ml); first = 'Amazon - ' + SHORT(det.split(';')[0].split(' x')[0])[:40]
        if sh and not pe: return C('likely shared', f'Household item ({sh.group(0)})', first, 'Household supplies')
        if sh and pe: return C('uncertain', f'Mixed order: {sh.group(0)} (household) + {pe.group(0)} (personal) - share only part? Use 50/50@<amount>', first, 'Household supplies')
        if pe: return C('likely personal', f'Personal item ({pe.group(0)})')
        return C('uncertain', 'Amazon order - for the house or for you?', first, 'Household supplies')
    if src == 'Email':
        if SH_RX.search(ml): return C('likely shared', f'Home service or household item ({SH_RX.search(ml).group(0)})', f'{SHORT(m)} - {SHORT(det)[:30]}', 'Cleaning')
        return C('uncertain', f'{m} receipt - for the home?', SHORT(m), 'General')
    if src == 'Card':
        if 'add money' in ml: return C('likely personal', 'Wallet top-up (what it paid for is invisible)')
        if GROC_RX.search(ml): return C('uncertain', f'{m} grocery charge, no receipt - for home?', f'Grocery - {SHORT(m).title()}', 'Groceries')
        if 'amazon' in ml: return C('uncertain', 'Amazon charge without order detail', 'Amazon - ', 'Household supplies')
        if re.search(r'groce|instamart|swiggy', ml): return C('uncertain', 'Swiggy/Instamart charge with no receipt - groceries for home?', 'Grocery - Instamart', 'Groceries')
        if EATOUT_RX.search(ml) and a >= RULES.get('eating_out_from', 800): return C('uncertain', f'₹{a:,.0f} at {m} - eating out together?', f'Food - {m.title()}', 'Dining out')
        return C('likely personal', 'Personal shopping / entertainment')
    # bank debits
    if SKIP_RX.search(ml + ' ' + pay) or bk.PEOPLE_RX.search(ml): return C('likely personal', 'Transfer, investment or card bill - not an expense')
    if RENT_RX.search(ml):
        pm = rent_month(r['date']); mon, yr = pm.split()
        exists = [x for x in sw if not x['deleted'] and x['description'].lower().startswith('rent') and mon.lower() in x['description'].lower() and yr in x['description']]
        if exists: return C('likely personal', f'Rent for {pm} already in Splitwise ("{exists[0]["description"]}")')
        if bk.RENT.get('mode') == 'each_pays_own_half':
            share = int(a // 50 * 50)  # drop small transfer fees (22,505.90 -> 22,500)
            r['_rentsplit'] = f'RENT@{share * 2}'
            return C('likely shared', f'Your rent share for {pm} - no entry yet, so log the total ₹{share * 2:,} paid 50/50', 'Rent - ' + pm, 'Rent')
        return C('likely shared', f'Rent for {pm} paid to the landlord - no entry yet', 'Rent - ' + pm, 'Rent')
    if GROC_RX.search(ml): return C('likely shared', f'{m} groceries', f'Grocery - {SHORT(m).title()}', 'Groceries')
    if SH_RX.search(ml): return C('uncertain', f'{m} - household? ({SH_RX.search(ml).group(0)})', SHORT(m).title(), 'Household supplies')
    if 'Food' in r['pay'] or EATOUT_RX.search(ml):
        if a >= RULES.get('eating_out_from', 800): return C('uncertain', f'₹{a:,.0f} at {m} - eating out together?', f'Food - {m.title()}', 'Dining out')
        return C('likely personal', 'Small food/coffee spend')
    return C('likely personal', (r['pay'] or 'Personal payment').split('/')[0])

LEARN = [(bk.rx([x['match']]), x['tag'], x['why'], x.get('desc', ''), x.get('cat', '')) for x in RULES.get('learned', [])]
for r in rows:
    r['tag'], r['reason'], r['desc'], r['cat'] = classify(r)
    if r['tag'] in ('uncertain', 'likely shared') and not r.get('_rentsplit'):
        for pat, t, why, desc, cat in LEARN:
            if pat.search(r['merchant'] + ' ' + r['detail']):
                r['tag'], r['reason'] = t, why
                if desc: r['desc'], r['cat'] = desc, cat
                break

# --- 4. cross-check Splitwise for anything the flatmate already logged ---
live = [s for s in sw if not s['deleted'] and not s['payment']]
for r in rows:
    if r['tag'] == 'likely personal': continue
    hit = [s for s in live if abs(amt(s['cost']) - r['amount']) <= 5 and near(d(s['date']), r['date'], 3)]
    if hit: r['tag'] = 'likely personal'; r['reason'] = f'Already in Splitwise: "{hit[0]["description"]}" ({hit[0]["date"]})'

# a same-day grocery lump sum I logged myself may already include this order
mine = [x for x in SWALL if not x.get('deleted_at') and any(int(u.get('user_id') or u['user']['id']) == bk.ME_ID and float(u['paid_share']) > 0 for u in x['users'])]
for r in rows:
    if r['src'] in ('Instamart', 'Card') and r['tag'] != 'likely personal' and 'Already' not in r['reason']:
        h = [x for x in mine if 'nstamart' in x['description'] and '->' not in x['description'] and abs((d(x['date']) - r['date']).days) <= 1]
        if h: r['tag'] = 'uncertain'; r['reason'] = f'You logged "{h[0]["description"]}" ₹{float(h[0]["cost"]):,.0f} on {h[0]["date"][:10]} - is this order already in it?'

# --- 4b. Amazon order-history export fills in card charges with no email ---
AMZF = bk.RAW0 + 'amazon/Order History.csv'
amz = list(csv.DictReader(open(AMZF, encoding='utf-8-sig'))) if os.path.exists(AMZF) else []
for r in rows:
    if r['src'] == 'Card' and 'amazon' in r['merchant'].lower() and amz:
        hit = [o for o in amz if near(d(o['Order Date']), r['date']) and abs(amt(o['Total Amount']) - r['amount']) <= 2]
        if hit: r['detail'] = hit[0]['Product Name'][:70]; r['ref'] = hit[0]['Order ID']
        else: r['reason'] = 'No matching Amazon.in order - probably Amazon Pay used at another merchant'

# --- 4c. your decisions (decisions.csv) override Claude's guesses ---
r_split = {}
DECF = bk.EL + 'decisions.csv'
dec = list(csv.DictReader(open(DECF))) if os.path.exists(DECF) else []
for x in dec:
    m = [r for r in rows if not r.get('_dec') and str(r['date']) == x['date'] and abs(r['amount'] - float(x['amount'])) <= 1 and r['merchant'][:8].lower() == x['merchant'][:8].lower()]
    if not m: x['_unmatched'] = True; continue
    r = m[0]; r['_dec'] = True; r['tag'] = x['tag']; r['desc'] = x['sw_description'] or r['desc']; r['cat'] = x['sw_category'] or r['cat']; r_split[id(r)] = x['split']
    if x['note']: r['reason'] = x['note']
um = [(x['old_id'], x['date'], x['amount']) for x in dec if x.get('_unmatched') and START <= x['date'] <= END]
if um: print('UNMATCHED decisions:', um)

# --- 4d. auto-add: only categories the user opted into, only rows rated 'likely shared', never ones they decided ---
CATS = RULES.get('auto_categories', {})
def item_price(det, word):
    m = re.search(word + r'[^;]*?x\d+\s*([\d.]+)', det, re.I); return float(m.group(1)) if m else None
for r in rows:
    r['auto'] = ''
    if r.get('_dec') or r['tag'] != 'likely shared': continue
    ml = (r['merchant'] + ' ' + r['detail']).lower(); cat = None
    if r['src'] == 'Instamart' and r['where'] == bk.HOME_LABEL and 'logged' not in r['reason']: cat = 'instamart_home'
    elif r.get('_rentsplit') or (r['cat'] == 'Rent' and RENT_RX.search(ml)): cat = 'rent'
    else:
        for cid, c in CATS.items():
            if c.get('match') and re.search(c['match'], ml, re.I) and (not c.get('sources') or r['src'] in c['sources']):
                cat = cid
                if c.get('item'):  # one shared item inside a mixed order: share only its price
                    others = [x for x in r['detail'].split(';') if x.strip() and not re.search(c['match'], x, re.I)]
                    if others:
                        p = item_price(r['detail'], c['match'])
                        if not p: cat = None
                        else: r['_partial'] = f'50/50@{p:g}'
                if cat and c.get('desc'): r['desc'] = c['desc']
                if cat and c.get('cat'): r['cat'] = c['cat']
                break
    if not cat or cat not in RULES.get('auto_add', []): continue
    cap = RULES.get('caps', {}).get(cat, RULES.get('caps', {}).get('default', 3000))
    eff = float(r['_partial'].split('@')[1]) if r.get('_partial') else r['amount']
    if eff > cap: r['reason'] += f' (over the ₹{cap:,} auto-add cap - review)'; continue
    r['tag'] = 'shared'; r['auto'] = cat; r['reason'] = f'AUTO-ADDED ({cat}): ' + r['reason']

# --- 5. IDs + log ---
pref = {'Grocery': 'G', 'Swiggy': 'S', 'Swiggy Dineout': 'S', 'Zomato': 'Z', 'Instamart': 'I', 'Amazon': 'A', 'Email': 'E', 'Card': 'C', 'Fold': 'F'}
cnt = Counter()
for r in rows: p = pref[r['src']]; cnt[p] += 1; r['id'] = f'{p}{cnt[p]}'
AF = bk.EL + 'added.csv'
ADDED = {(a['date'], round(float(a['amount']), 2), a['merchant']): a['splitwise_expense_id'] for a in csv.DictReader(open(AF))} if os.path.exists(AF) else {}
cols = ['id', 'date', 'source', 'merchant', 'detail', 'amount', 'paid_via', 'delivered_to', 'tag', 'reason', 'sw_description', 'sw_category', 'split', 'source_ref', 'splitwise_expense_id', 'auto']
os.makedirs(bk.EL, exist_ok=True)
with open(bk.EL + f'log-{TAG}.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(cols)
    for r in rows:
        w.writerow([r['id'], r['date'], r['src'], r['merchant'], r['detail'], r['amount'], r['pay'], r['where'], r['tag'], r['reason'], r['desc'], r['cat'],
                    r_split.get(id(r)) or r.get('_partial') or r.get('_rentsplit') or ('50/50' if r['desc'] else ''), r['ref'],
                    ADDED.get((str(r['date']), round(r['amount'], 2), r['merchant']), ''), r['auto']])
print(len(rows), dict(Counter(r['tag'] for r in rows)))
print('auto-add:', dict(Counter(r['auto'] for r in rows if r['auto'])))
