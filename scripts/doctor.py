"""Check a Bahikhaata install without printing any secret.
usage: doctor.py [--groups]     --groups also lists Splitwise groups and members (for picking during setup)
Prints one line per check: OK / TODO / FAIL, and what to do next."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'pipeline'))
import bk

def line(s, what, hint=''): print(f'{s:4} {what}' + (f'  -> {hint}' if hint else ''))

cfg = bk.CFG
line('OK', f'config {bk.CONFIG_PATH}' + ('  (DRY RUN)' if bk.DRY else ''))
if not bk.DRY:
    if not os.path.exists(bk.MCP_PY): line('FAIL', 'Splitwise server not installed', 'run scripts/install_splitwise_mcp.sh'); sys.exit(1)
    env = os.path.join(bk.MCP_DIR, '.env')
    vals = dict(l.strip().split('=', 1) for l in open(env) if '=' in l and not l.lstrip().startswith('#')) if os.path.exists(env) else {}
    filled = [k for k, v in vals.items() if v.strip()]
    bad = [k for k, v in vals.items() if v.strip() != v or v.strip()[:1] in '"\'']
    if not filled: line('TODO', '.env has no keys yet', f'open {env} and paste the keys from secure.splitwise.com/apps'); sys.exit(1)
    if bad: line('FAIL', f'.env values have spaces or quotes: {", ".join(bad)}', 'remove them'); sys.exit(1)
    line('OK', f'.env has {len(filled)} key(s) set (values not shown)')
    if oct(os.stat(env).st_mode)[-3:] != '600': os.chmod(env, 0o600); line('OK', '.env made private (chmod 600)')
from sw import Session
try:
    s = Session(); me = json.loads(s.call('get_current_user', {}))
    u = me.get('user', me); line('OK', f"Splitwise connected as {u.get('first_name', '?')} (id {u.get('id')})")
    if '--groups' in sys.argv:
        gs = json.loads(s.call('get_groups', {})).get('groups', [])
        for g in gs:
            if g['id'] == 0: continue
            ms = ', '.join(f"{m.get('first_name', '')} {m.get('last_name') or ''}".strip() + f" ({m['id']})" for m in g.get('members', []) if m['id'] != u.get('id'))
            print(f"     group {g['id']}: {g['name']}  — with {ms}")
    s.close()
except SystemExit as e:
    line('FAIL', f'Splitwise call failed: {str(e)[:200]}', 'check the keys in .env; see references/troubleshooting.md'); sys.exit(1)
for k in ('group_id',):
    if not cfg['splitwise'].get(k): line('TODO', 'no Splitwise group chosen yet', 'pick one from --groups')
if not cfg.get('review_page'): line('TODO', 'review page not created yet')
missing = [k for k, v in cfg.get('setup', {}).items() if not v]
line('OK' if not missing else 'TODO', 'setup steps ' + ('all done' if not missing else 'left: ' + ', '.join(missing)))
