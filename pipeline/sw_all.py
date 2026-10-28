"""Snapshot every expense in the shared group to expense-log/raw/splitwise_all.json.
usage: sw_all.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk
from sw import Session

s = Session(); out = []; off = 0
while True:
    es = json.loads(s.call('get_expenses', {"group_id": bk.GROUP_ID, "limit": 100, "offset": off}))['expenses']
    out += es
    if len(es) < 100: break
    off += 100
s.close()
os.makedirs(bk.RAW0, exist_ok=True)
json.dump(out, open(bk.RAW0 + 'splitwise_all.json', 'w'))
print(len(out), 'expenses', '(dry run: fake Splitwise)' if bk.DRY else '')
