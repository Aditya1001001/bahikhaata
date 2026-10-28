"""Shared config for every Bahikhaata script.

Config lookup: $BAHIKHAATA_CONFIG, else ./bahikhaata.config.json, else ~/Bahikhaata/bahikhaata.config.json.
Dry run: $BAHIKHAATA_DRY_RUN=1 (or "dry_run": true in the config) swaps Splitwise for a local fake store
in <workspace>/.dryrun/splitwise.json, so nothing real is ever touched."""
import json, os, re

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_path():
    for p in (os.environ.get('BAHIKHAATA_CONFIG'), os.path.join(os.getcwd(), 'bahikhaata.config.json'),
              os.path.expanduser('~/Bahikhaata/bahikhaata.config.json')):
        if p and os.path.exists(p): return os.path.abspath(p)
    raise SystemExit('No bahikhaata.config.json found. Run /bahikhaata-setup first, or set BAHIKHAATA_CONFIG.')


CONFIG_PATH = config_path()
CFG = json.load(open(CONFIG_PATH))
WS = os.path.expanduser(CFG.get('workspace') or os.path.dirname(CONFIG_PATH))
EL = os.path.join(WS, 'expense-log') + '/'
RAW0 = EL + 'raw/'
OUTDIR = os.path.join(WS, 'out')
STATE = os.path.join(WS, 'state.json')
MCP_DIR = os.path.expanduser(CFG['splitwise']['mcp_dir'])
MCP_PY = os.path.join(MCP_DIR, 'venv', 'bin', 'python')
DRY = os.environ.get('BAHIKHAATA_DRY_RUN') == '1' or bool(CFG.get('dry_run'))

ME = CFG['me']; THEM = CFG['flatmate']
ME_ID, THEM_ID = int(ME['splitwise_id']), int(THEM['splitwise_id'])
GROUP_ID = int(CFG['splitwise']['group_id'])
CURRENCY = CFG.get('currency', 'INR')
HOME = CFG.get('home', {})
HOME_KEYS = [k.lower() for k in HOME.get('keywords', [])]  # e.g. ["sunrise apartments", "hsr layout"]
HOME_LABEL = HOME.get('label', 'Home')
RULES = CFG.get('rules', {})
RENT = CFG.get('rent') or {}

def is_home(addr):
    a = (addr or '').lower()
    return bool(a) and any(k in a for k in HOME_KEYS)

def rx(pats):
    """Join a list of regex fragments; returns a pattern that never matches when empty."""
    pats = [p for p in (pats or []) if p]
    return re.compile('|'.join(pats), re.I) if pats else re.compile(r'(?!x)x')

# My own names, the flatmate's names: transfers between us are never expenses.
PEOPLE_RX = rx([re.escape(n.lower()) for n in [ME.get('name', ''), ME.get('full_name', ''), THEM.get('name', '')] + THEM.get('aliases', []) + ME.get('aliases', []) if n])

def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {'last_end': None, 'periods': {}}

def save_state(s): json.dump(s, open(STATE, 'w'), indent=2)

def parse_split(split, amount):
    """Split syntax -> (cost, their_owed, paid_by_me, paid_by_them).
    50/50, 70/30         my share / their share, of the whole amount, I paid
    50/50@190            only 190 of the payment is shared, split 50/50
    THEM=2996            they owe a fixed amount (any NAME=2996 works too, for older logs)
    RENT@45000           we each paid our own half to the landlord: total 45000, paid and owed 50/50"""
    sp = (split or '50/50').strip(); cost = round(float(amount), 2)
    m = re.match(r'^([A-Za-z]+)=([\d.]+)$', sp)
    if sp.upper().startswith('RENT@'):
        cost = round(float(sp.split('@')[1]), 2); half = round(cost / 2, 2)
        return cost, round(cost - half, 2), half, round(cost - half, 2)
    if m:
        k = round(float(m.group(2)), 2); return cost, k, cost, 0.0
    if '@' in sp: sp, part = sp.split('@'); cost = round(float(part), 2)
    mine = int(sp.split('/')[0]); k = round(cost * (100 - mine) / 100, 2)
    return cost, k, cost, 0.0

def they_owe(amount, split):
    cost, k, _, paid_k = parse_split(split, amount)
    return round(k - paid_k, 2)
