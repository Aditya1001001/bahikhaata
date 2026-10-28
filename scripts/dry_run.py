"""End-to-end onboarding + first runs against fake data. Touches no real Splitwise account, page or connector.
usage: dry_run.py [--keep] [--workspace DIR]
Builds a throwaway workspace, answers onboarding with sample/answers.json, fakes Splitwise (fake_splitwise.py) and
the review page database (a local folder laid out like an ArtifactData dump), then checks each step."""
import csv, glob, json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PLUGIN = os.path.dirname(HERE)
args = sys.argv[1:]
WS = os.path.abspath(args[args.index('--workspace') + 1]) if '--workspace' in args else tempfile.mkdtemp(prefix='bahikhaata-dry-')
os.makedirs(WS, exist_ok=True)
A = json.load(open(os.path.join(PLUGIN, 'sample', 'answers.json')))
ENV = dict(os.environ, BAHIKHAATA_CONFIG=os.path.join(WS, 'bahikhaata.config.json'), BAHIKHAATA_DRY_RUN='1', BAHIKHAATA_WORKSPACE=WS)
PY = sys.executable; E = os.path.join(WS, 'engine'); PAGE = os.path.join(WS, '.dryrun', 'page')
fails = []

def run(*cmd, env=None, ok=True):
    r = subprocess.run([PY, '-I', *cmd], cwd=WS, env=dict(ENV, **(env or {})), capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if ok and r.returncode: fails.append(' '.join(cmd[:2])); print('   !! exit', r.returncode, out[-800:])
    return out

def step(n, title): print(f'\n== {n}. {title}')
def check(cond, what):
    print(('   ok  ' if cond else '   FAIL ') + what)
    if not cond: fails.append(what)

def page_apply(writes_glob):
    """Stand-in for `ArtifactData batch`: store each doc at <page>/<collection>/<doc_id>.json."""
    n = 0
    for wf in sorted(glob.glob(writes_glob)):
        for w in json.load(open(wf)):
            d = os.path.join(PAGE, w['collection']); os.makedirs(d, exist_ok=True)
            shutil.copy(w['file_path'], os.path.join(d, w['doc_id'] + '.json')); n += 1
    return n

def page_set(path, data):
    p = os.path.join(PAGE, path + '.json'); os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(data, open(p, 'w'))

def sw_db(): return json.load(open(os.path.join(WS, '.dryrun', 'splitwise.json')))
def balance(): return json.loads(run(f'{E}/pipeline/sw.py', 'get_group', json.dumps({'group_id': 5001})))['group']['balance_them_owes_me']

print('Dry-run workspace:', WS)

step(0, 'Welcome: create the workspace')
print('  ', run(f'{PLUGIN}/scripts/setup_workspace.py', 'init', WS))
run(f'{E}/scripts/setup_workspace.py', 'set', 'dry_run=true')
check(os.path.exists(f'{E}/pipeline/build.py') and os.path.exists(f'{E}/runbook.md'), 'engine copied into the workspace')

step(1, 'Splitwise: (fake) connect, list groups, pick group and flatmate')
out = run(f'{E}/scripts/doctor.py', '--groups'); print('   ' + out.replace('\n', '\n   '))
check('Flat 4B' in out and 'Zoya' in out, 'groups and members listed for picking')
m, f, s = A['me'], A['flatmate'], A['splitwise']
run(f'{E}/scripts/setup_workspace.py', 'set', f"me={json.dumps(m)}", f"flatmate={json.dumps(f)}", f"splitwise.group_id={s['group_id']}", f"splitwise.group_name={s['group_name']}")
run(f'{E}/scripts/setup_workspace.py', 'done', 'splitwise')

step(2, 'Sources: record which are on and the read-only tool names')
run(f'{E}/scripts/setup_workspace.py', 'set', f"sources={json.dumps(A['sources'])}", f"connector_tools={json.dumps(A['connector_tools'])}")
run(f'{E}/scripts/setup_workspace.py', 'done', 'sources')

step(3, 'Household rules: home, rent, never-add, learned')
run(f'{E}/scripts/setup_workspace.py', 'set', f"home={json.dumps(A['home'])}", f"rent={json.dumps(A['rent'])}")
rp = os.path.join(WS, 'rules.json'); R = json.load(open(rp)); R['never_add'] = A['never_add']; R['learned'] = A['learned']; json.dump(R, open(rp, 'w'), indent=2)
print('  ', run(f'{E}/scripts/setup_workspace.py', 'render'))
cm = open(os.path.join(WS, 'CLAUDE.md')).read()
check('Zoya' in cm and 'sunrise apartments' in cm and 'each of us pays our own half' in cm, 'CLAUDE.md has their names, home and rent rule')
run(f'{E}/scripts/setup_workspace.py', 'done', 'rules')

step(4, 'Review page: (fake) publish and seed summary/main')
html = open(os.path.join(WS, 'review.html')).read()
check('<title>' in html and '${esc(flatmate)}' in html, 'page template is generic')
run(f'{E}/scripts/setup_workspace.py', 'set', 'review_page=https://claude.ai/artifact/DRYRUN-not-real')
run(f'{E}/scripts/setup_workspace.py', 'done', 'page')
page_set('summary/main', json.load(open(os.path.join(WS, 'out', 'summary_main.json'))))
check(json.load(open(f'{PAGE}/summary/main.json'))['flatmate'] == 'Zoya', 'summary/main seeded with the flatmate name')

step(5, 'Auto-add: opt in')
R = json.load(open(rp)); R['auto_add'] = A['auto_add']; json.dump(R, open(rp, 'w'), indent=2)
run(f'{E}/scripts/setup_workspace.py', 'done', 'auto_add')

step(6, 'First run: fetch (sample files), build, publish, stamp, add with approval')
P = '2026-10-12_2026-10-25'; raw = os.path.join(WS, 'expense-log', 'raw', P)
shutil.copytree(os.path.join(PLUGIN, 'sample', 'raw', P), raw)
print('  ', run(f'{E}/pipeline/sw_all.py'))
print('  ', run(f'{E}/pipeline/build.py', '--raw', raw, '--start', '2026-10-12', '--end', '2026-10-25', '--tag', P).replace('\n', '\n   '))
st = json.load(open(os.path.join(WS, 'state.json'))); st['periods'][P] = dict(log=f'log-{P}.csv', raw=f'expense-log/raw/{P}', start='2026-10-12', end='2026-10-25'); st['last_end'] = '2026-10-25'
json.dump(st, open(os.path.join(WS, 'state.json'), 'w'), indent=2)
LOG = os.path.join(WS, 'expense-log', f'log-{P}.csv'); rows = list(csv.DictReader(open(LOG)))
by = lambda s: next((r for r in rows if s.lower() in (r['merchant'] + r['detail']).lower()), {})
check(by('meera')['split'] == 'RENT@45000' and by('meera')['auto'] == 'rent', 'rent detected: total 45000, each paid half, auto category')
check(by('wework').get('tag') == 'likely personal' or by('protein').get('tag') == 'likely personal', 'Instamart delivered away from home is personal')
check(by('atta')['auto'] == 'instamart_home', 'Instamart delivered home is auto')
check(by('truffles')['tag'] == 'likely personal' and 'Already in Splitwise' in by('truffles')['reason'], 'flatmate already logged Truffles: not suggested again')
check(by('furlenco')['tag'] == 'likely personal', 'never_add (furniture prepayment) respected')
check(by('zoya m menon')['tag'] == 'likely personal', 'transfer to the flatmate is not an expense')
check(by('cult')['tag'] == 'likely personal', 'learned rule applied')
check(sum(1 for r in rows if 'licious' in r['merchant'].lower() or 'delightful gourmet' in r['merchant'].lower()) == 1, 'card alert deduped against the Licious receipt')
print('   preview (first run, decided only):', run(f'{E}/pipeline/add.py', '', '--preview', '--decided-only', env={'LOG': LOG}).splitlines()[-1])
check(not sw_db()['expenses'][3:], 'nothing added to (fake) Splitwise before approval')
out = run(f'{E}/pipeline/publish_review.py', 'week-2026-10-20', 'Week of 20 Oct 2026', '2026-10-20', '2026-10-25', f'{LOG}:{P}', env={'BATCH': P}); print('  ', out)
n = page_apply(os.path.join(WS, 'out', 'week-2026-10-20', P, 'writes-*.json')); check(n > 0, f'{n} docs written to the (fake) page')
pub = ' '.join(open(p).read() for p in glob.glob(f'{PAGE}/**/*.json', recursive=True)).lower()
check('groww' not in pub and 'cult' not in pub and 'protein' not in pub, 'personal spending never reaches the page')
# the user stamps entries on the page
for p in glob.glob(f'{PAGE}/runs/week-2026-10-20/rows/*.json'):
    d = json.load(open(p)); txt = d['merchant'] + ' ' + d['detail']
    for k, v in A['page_decisions'].items():
        if k.lower() in txt.lower():
            d['decision'], d['d_split'] = (v, None) if isinstance(v, str) else v
            if not d['d_split']: d.pop('d_split')
    json.dump(d, open(p, 'w'))
print('  ', run(f'{E}/pipeline/ingest_review.py', PAGE, 'week-2026-10-20').splitlines()[-1])
run(f'{E}/pipeline/build.py', '--raw', raw, '--start', '2026-10-12', '--end', '2026-10-25', '--tag', P)
prev = run(f'{E}/pipeline/add.py', '', '--preview', '--decided-only', env={'LOG': LOG}); print('   ' + prev.replace('\n', '\n   '))
check('AUTO' not in prev and 'decided' in prev, 'first-run preview lists only rows the user stamped')
print('   [user says yes]')
print('   ' + run(f'{E}/pipeline/add.py', '', '--decided-only', env={'LOG': LOG}).replace('\n', '\n   '))
added = [e for e in sw_db()['expenses'] if e['id'] >= 900000]
dish = next((e for e in added if 'Dishwash' in e['description'] or e['cost'] == '199.00'), None)
check(dish is not None and dish['cost'] == '199.00', 'partial split 50/50@199 adds only the shared item')
check(all(sum(float(u['paid_share']) for u in e['users']) == float(e['cost']) for e in added), 'every added expense balances')
run(f'{E}/scripts/setup_workspace.py', 'done', 'first_run')

step(7, 'Second run: auto-add opted-in categories, then Undo one from the page')
run(f'{E}/pipeline/build.py', '--raw', raw, '--start', '2026-10-12', '--end', '2026-10-25', '--tag', P)
prev = run(f'{E}/pipeline/add.py', '', '--preview', env={'LOG': LOG}); print('   ' + prev.replace('\n', '\n   '))
print('   ' + run(f'{E}/pipeline/add.py', '', env={'LOG': LOG}).replace('\n', '\n   '))
rent = next((e for e in sw_db()['expenses'] if e['description'].startswith('Rent - Sep')), None)
check(rent and rent['cost'] == '45000.00' and all(u['paid_share'] == '22500.00' for u in rent['users']), 'rent logged as 45000 paid 50/50')
run(f'{E}/pipeline/build.py', '--raw', raw, '--start', '2026-10-12', '--end', '2026-10-25', '--tag', P)
run(f'{E}/pipeline/publish_review.py', 'week-2026-10-20', 'Week of 20 Oct 2026', '2026-10-20', '2026-10-25', f'{LOG}:{P}', env={'BATCH': P + '-2', 'RUN_EXISTS': '1'})
page_apply(os.path.join(WS, 'out', 'week-2026-10-20', P + '-2', 'writes-*.json'))
autos = glob.glob(f'{PAGE}/runs/week-2026-10-20/auto/*.json'); check(len(autos) >= 2, f'{len(autos)} auto-added rows shown on the page')
lic = next(p for p in autos if 'Licious' in open(p).read()); d = json.load(open(lic)); d['undo'] = True; json.dump(d, open(lic, 'w'))
out = run(f'{E}/pipeline/ingest_review.py', PAGE, 'week-2026-10-20'); print('  ', out.splitlines()[-1])
run(f'{E}/pipeline/sw.py', 'delete_expense', json.dumps({'expense_id': int(d['splitwise_id'])}))
check(any(e['id'] == int(d['splitwise_id']) and e['deleted_at'] for e in sw_db()['expenses']), 'Undo deleted the Licious entry in (fake) Splitwise')
b = balance(); print('   balance:', f'Zoya owes Kabir {b}' if b >= 0 else f'Kabir owes Zoya {-b}')
print('  ', run(f'{E}/pipeline/publish_months.py', '2026-10'))

step(8, 'Schedule and permissions')
print('  ', run(f'{E}/scripts/setup_workspace.py', 'render'))
task = open(os.path.join(WS, 'out', 'scheduled-task.md')).read(); allow = json.load(open(os.path.join(WS, '.claude', 'settings.local.json')))['permissions']
check(WS in task and 'DRYRUN' in task and '$' not in task.replace('$ARGUMENTS', ''), 'scheduled task prompt filled with their paths and page')
check(any('fold-fake__list_transactions' in a for a in allow['allow']) and not any('send' in a or 'create_transaction' in a for a in allow['allow']), 'allowlist has read-only connector tools only')
check(any('.env' in x for x in allow.get('deny', [])), 'keys file is denied')
run(f'{E}/scripts/setup_workspace.py', 'done', 'schedule')
print('  ', run(f'{E}/scripts/doctor.py').splitlines()[-1])

step(9, 'Privacy scan of the plugin itself')
import re
GENERIC = [r'/Users/[a-z]', r'@gmail\.com', r'claude\.ai/(code/)?artifact/[A-Za-z0-9]{12,}', r'mcp__[0-9a-f]{8}-[0-9a-f]{4}', r'\b\d{8}\b']
# Your own words to keep out (names, IDs, addresses): a JSON list in a file OUTSIDE the package, e.g. ~/.bahikhaata-denylist.json
dl = args[args.index('--denylist') + 1] if '--denylist' in args else os.path.expanduser('~/.bahikhaata-denylist.json')
BAD = json.load(open(dl)) if os.path.exists(dl) else []
hits = []
for p in glob.glob(f'{PLUGIN}/**/*', recursive=True) + glob.glob(f'{PLUGIN}/.claude-plugin/*'):
    if not os.path.isfile(p) or '__pycache__' in p: continue
    t = open(p, errors='ignore').read()
    hits += [(os.path.relpath(p, PLUGIN), w) for w in BAD if w.lower() in t.lower()]
    hits += [(os.path.relpath(p, PLUGIN), m.group(0)) for g in GENERIC for m in [re.search(g, t)] if m]
check(not hits, f'no personal names, IDs, paths or URLs in the package (denylist: {len(BAD)} words)' + (f': {hits[:8]}' if hits else ''))

print('\n' + ('ALL CHECKS PASSED' if not fails else f'{len(fails)} FAILED: {fails}'))
if '--keep' not in args and '--workspace' not in args: shutil.rmtree(WS)
sys.exit(1 if fails else 0)
