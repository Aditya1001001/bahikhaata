"""Create and fill a Bahikhaata workspace. Used by /bahikhaata-setup; safe to re-run.
usage:
  setup_workspace.py init [WORKSPACE]          create folders, config, rules.json, state.json (keeps existing files)
  setup_workspace.py set KEY=VALUE [...]       edit the config (dotted keys; JSON values allowed: me.splitwise_id=123)
  setup_workspace.py done STEP                 mark a setup step done (also refreshes the page checklist seed)
  setup_workspace.py render                    write CLAUDE.md, .claude/settings.local.json, review.html,
                                               out/summary_main.json and out/scheduled-task.md from the templates
  setup_workspace.py update-engine             refresh <ws>/engine from this plugin version, then render
  setup_workspace.py show                      print the config (no secrets live there)"""
import json, os, shutil, string, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PLUGIN = os.path.dirname(HERE)
T = os.path.join(PLUGIN, 'templates')

def cfg_path(ws=None):
    ws = os.path.expanduser(ws or os.environ.get('BAHIKHAATA_WORKSPACE') or (os.path.dirname(os.environ['BAHIKHAATA_CONFIG']) if os.environ.get('BAHIKHAATA_CONFIG') else '~/Bahikhaata'))
    return ws, os.path.join(ws, 'bahikhaata.config.json')

def load(): ws, p = cfg_path(); return ws, p, json.load(open(p))
def save(p, c): json.dump(c, open(p, 'w'), indent=2, ensure_ascii=False)

def init(ws_arg):
    ws, p = cfg_path(ws_arg)
    for d in ('expense-log/raw', 'out', '.claude'): os.makedirs(os.path.join(ws, d), exist_ok=True)
    if not os.path.exists(p):
        c = json.load(open(os.path.join(PLUGIN, 'pipeline', 'bahikhaata.config.example.json')))
        c['workspace'] = ws; c['splitwise']['mcp_dir'] = os.path.join(ws, 'splitwise-mcp')
        c['me'] = {"name": "", "full_name": "", "aliases": [], "splitwise_id": 0}
        c['flatmate'] = {"name": "", "aliases": [], "splitwise_id": 0}
        c['splitwise'].update(group_id=0, group_name=''); c['home'].update(keywords=[], city='')
        c['setup']['workspace'] = True; save(p, c)
    r = os.path.join(ws, 'rules.json')
    if not os.path.exists(r): shutil.copy(os.path.join(PLUGIN, 'pipeline', 'rules.example.json'), r)
    s = os.path.join(ws, 'state.json')
    if not os.path.exists(s): json.dump({'last_end': None, 'periods': {}}, open(s, 'w'), indent=2)
    engine(ws)
    gi = os.path.join(ws, '.gitignore')
    if not os.path.exists(gi): open(gi, 'w').write('expense-log/\nout/\n.dryrun/\nsplitwise-mcp/.env\nbahikhaata.config.json\n')
    print('OK workspace', ws)

def engine(ws):
    """Copy the scripts into <ws>/engine so scheduled runs keep working when the plugin updates or moves."""
    e = os.path.join(ws, 'engine')
    for d in ('pipeline', 'scripts', 'templates', 'sample'):
        shutil.copytree(os.path.join(PLUGIN, d), os.path.join(e, d), dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(os.path.join(PLUGIN, 'skills', 'bahikhaata', 'references', 'runbook.md'), os.path.join(e, 'runbook.md'))
    open(os.path.join(e, 'VERSION'), 'w').write(json.load(open(os.path.join(PLUGIN, '.claude-plugin', 'plugin.json')))['version'])

def setkey(c, key, val):
    try: val = json.loads(val)
    except Exception: pass
    o = c; ks = key.split('.')
    for k in ks[:-1]: o = o.setdefault(k, {})
    o[ks[-1]] = val

def summary_seed(c):
    s = c['setup']
    return dict(me=c['me']['name'], flatmate=c['flatmate']['name'] or 'saathi', group=c['splitwise'].get('group_name', ''),
                setup=dict(splitwise=s.get('splitwise', False), sources=s.get('sources', False), rules=s.get('rules', False), first_run=s.get('first_run', False)))

def render():
    ws, p, c = load()
    me, them = c['me']['name'], c['flatmate']['name']
    rent = c.get('rent') or {}
    rent_txt = {'off': 'Rent is not tracked here.',
                'i_pay_all': f"Rent: {me} pays the full rent to the landlord ({rent.get('landlord_pattern') or '?'}); log it split {c.get('default_split', '50/50')}.",
                'each_pays_own_half': f"Rent: each of us pays our own half to the landlord (matched by `{rent.get('landlord_pattern')}`). If a month has no \"Rent - <Mon YYYY>\" entry, add one for the total (2× my share), paid 50/50 and owed 50/50."}[rent.get('mode', 'off')]
    if rent.get('mode', 'off') != 'off': rent_txt += ' Payment in month N is rent for ' + ('month N-1.' if rent.get('pays_for') == 'previous_month' else 'month N.')
    srcs = c.get('sources', {})
    src_list = [n for n, on in (('Fold', srcs.get('fold')), ('bank statement CSV', srcs.get('bank_csv')), ('Gmail ' + (srcs.get('gmail') or {}).get('address', ''), (srcs.get('gmail') or {}).get('enabled')),
                                ('Swiggy', srcs.get('swiggy')), ('Instamart', srcs.get('instamart'))) if on]
    rules = json.load(open(os.path.join(ws, 'rules.json')))
    auto = ', '.join(rules['auto_categories'].get(a, {}).get('label', a) for a in rules.get('auto_add', [])) or 'none'
    v = dict(ME=me, THEM=them, THEM_ALIASES=', '.join(c['flatmate'].get('aliases', [])) or 'none', GROUP=c['splitwise']['group_name'], GROUP_ID=c['splitwise']['group_id'],
             HOME=', '.join(c['home'].get('keywords', [])), CITY=c['home'].get('city', ''), HOME_LABEL=c['home'].get('label', 'Home'),
             SPLIT=c.get('default_split', '50/50'), RENT=rent_txt, ALWAYS='\n'.join('- ' + x + ' default to shared.' for x in c.get('always_shared_notes', [])),
             SOURCES=', '.join(src_list) or 'none yet', AUTO=auto, CAP=rules.get('caps', {}).get('default', 3000), PAGE=c.get('review_page') or '(not created yet)',
             WS=ws, PLUGIN=os.path.join(ws, 'engine'), PY=os.path.join(c['splitwise']['mcp_dir'], 'venv', 'bin', 'python'),
             GMAIL=(srcs.get('gmail') or {}).get('address', ''), NOTIFY_DAY=c.get('notify', {}).get('weekday', 'Sunday'), BIG=c.get('notify', {}).get('big_auto_add', 2000))
    sub = lambda name: string.Template(open(os.path.join(T, name)).read()).safe_substitute(v)
    # CLAUDE.md: keep anything the user wrote below the marker
    cm = os.path.join(ws, 'CLAUDE.md'); mine = ''
    if os.path.exists(cm) and '<!-- your notes below -->' in open(cm).read(): mine = open(cm).read().split('<!-- your notes below -->', 1)[1]
    open(cm, 'w').write(sub('CLAUDE.md.tmpl') + mine)
    # permission allowlist: only read-only connector tools that setup actually found
    allow = json.loads(sub('settings.allowlist.tmpl.json'))
    ct = c.get('connector_tools', {})
    allow['permissions']['allow'] += ['mcp__' + t if not t.startswith('mcp__') else t for k, t in ct.items() if t and not k.startswith('_')]
    st = os.path.join(ws, '.claude', 'settings.local.json')
    if os.path.exists(st):  # merge, never drop the user's own entries
        old = json.load(open(st)); allow['permissions']['allow'] = sorted(set(old.get('permissions', {}).get('allow', [])) | set(allow['permissions']['allow']))
        old['permissions'] = dict(old.get('permissions', {}), allow=allow['permissions']['allow']); allow = old
    json.dump(allow, open(st, 'w'), indent=2)
    shutil.copy(os.path.join(T, 'review.html'), os.path.join(ws, 'review.html'))
    os.makedirs(os.path.join(ws, 'out'), exist_ok=True)
    json.dump(summary_seed(c), open(os.path.join(ws, 'out', 'summary_main.json'), 'w'), ensure_ascii=False)
    open(os.path.join(ws, 'out', 'scheduled-task.md'), 'w').write(sub('scheduled-task.md.tmpl'))
    print('OK rendered: CLAUDE.md, .claude/settings.local.json, review.html, out/summary_main.json, out/scheduled-task.md')

if __name__ == '__main__':
    a = sys.argv[1:] or ['show']
    if a[0] == 'init': init(a[1] if len(a) > 1 else None)
    elif a[0] == 'set':
        ws, p, c = load()
        for kv in a[1:]: k, _, val = kv.partition('='); setkey(c, k, val)
        save(p, c); print('OK set', ', '.join(x.split('=')[0] for x in a[1:]))
    elif a[0] == 'done':
        ws, p, c = load(); c['setup'][a[1]] = True; save(p, c)
        os.makedirs(os.path.join(ws, 'out'), exist_ok=True)
        json.dump(summary_seed(c), open(os.path.join(ws, 'out', 'summary_main.json'), 'w'), ensure_ascii=False)
        print('OK step done:', a[1], '| left:', [k for k, v in c['setup'].items() if not v])
    elif a[0] == 'render': render()
    elif a[0] == 'update-engine': engine(load()[0]); render()
    else: print(json.dumps(load()[2], indent=2, ensure_ascii=False))
