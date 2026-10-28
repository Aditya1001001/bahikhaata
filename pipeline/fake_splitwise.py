"""A fake Splitwise for dry runs. State lives in <workspace>/.dryrun/splitwise.json.
Seeded from sample/splitwise_seed.json the first time. Supports the tools the pipeline uses."""
import json, os, shutil, time
import bk

SEED = os.path.join(bk.PLUGIN, 'sample', 'splitwise_seed.json')


class Store:
    def __init__(self):
        d = os.path.join(bk.WS, '.dryrun'); os.makedirs(d, exist_ok=True)
        self.path = os.path.join(d, 'splitwise.json')
        if not os.path.exists(self.path): shutil.copy(SEED, self.path)
        self.db = json.load(open(self.path))

    def _save(self): json.dump(self.db, open(self.path, 'w'), indent=1)

    def call(self, tool, a):
        db = self.db
        if tool == 'get_current_user': return json.dumps({'user': db['users'][0]})
        if tool == 'get_groups': return json.dumps({'groups': [{k: g[k] for k in ('id', 'name', 'members')} for g in db['groups']]})
        if tool == 'get_group':
            g = next(g for g in db['groups'] if g['id'] == int(a['group_id']))
            bal = sum(float(u['owed_share']) - float(u['paid_share']) for e in db['expenses'] if not e.get('deleted_at') and e['group_id'] == g['id']
                      for u in e['users'] if u['user_id'] == bk.THEM_ID)
            return json.dumps({'group': dict(g, balance_them_owes_me=round(bal, 2))})
        if tool == 'get_expenses':
            es = [e for e in db['expenses'] if e['group_id'] == int(a.get('group_id', 0))]
            off, lim = int(a.get('offset', 0)), int(a.get('limit', 20))
            return json.dumps({'expenses': es[off:off + lim]})
        if tool == 'create_expense':
            names = {u['id']: u['first_name'] for u in db['users']}
            eid = 900000 + len(db['expenses']) + 1
            e = dict(id=eid, group_id=int(a['group_id']), description=a['description'], cost=a['cost'], date=a['date'],
                     currency_code=a.get('currency_code', 'INR'), payment=False, deleted_at=None, category={'id': a.get('category_id', 18)},
                     users=[dict(user_id=u['user_id'], user={'id': u['user_id'], 'first_name': names.get(u['user_id'], '?')},
                                 paid_share=u['paid_share'], owed_share=u['owed_share']) for u in a['users']], created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'))
            if abs(sum(float(u['paid_share']) for u in a['users']) - float(a['cost'])) > 0.02:
                return json.dumps({'expenses': [], 'errors': {'base': ['paid shares do not add up to cost']}})
            db['expenses'].append(e); self._save()
            return json.dumps({'expenses': [e], 'errors': {}})
        if tool == 'delete_expense':
            e = next(e for e in db['expenses'] if e['id'] == int(a['expense_id']))
            e['deleted_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ'); self._save()
            return json.dumps({'success': True})
        raise SystemExit(f'fake Splitwise: tool {tool} not supported in dry run')
