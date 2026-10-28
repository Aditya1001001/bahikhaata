"""Builds a static preview of the review page from a dry-run workspace, for README screenshots. See MAINTAINING.md.
usage: screenshots_preview.py <workspace> <review.html> <out.html>"""
import json, os, glob, sys
ws, tmpl, out = sys.argv[1:4]
P = os.path.join(ws, '.dryrun', 'page'); docs = {}
for f in glob.glob(P + '/**/*.json', recursive=True):
    docs[os.path.relpath(f, P)[:-5]] = json.load(open(f))
for f in glob.glob(ws + '/out/months/2*.json'):
    docs['months/' + os.path.basename(f)[:-5]] = json.load(open(f))
docs['summary/main'].update(balance=1321, as_of='2026-10-26T10:00:00')
# Show the queue as it looks before review: a couple stamped, the rest waiting.
for i, k in enumerate(sorted(k for k in docs if '/rows/' in k)):
    docs[k]['decision'] = {0: 'shared', 1: 'personal'}.get(i)
shim = """<script>(()=>{const D=%s;
const snap=p=>({exists:p in D,data:()=>D[p]});
const kids=c=>Object.keys(D).filter(k=>k.startsWith(c+'/')&&!k.slice(c.length+1).includes('/')).map(k=>({id:k.slice(c.length+1),data:()=>D[k]}));
const db={doc:p=>({onSnapshot:f=>{setTimeout(()=>f(snap(p)));return()=>{}},update:d=>{Object.assign(D[p],d);return Promise.resolve()}}),
 collection:c=>({onSnapshot:f=>{setTimeout(()=>f({docs:kids(c)}));return()=>{}}})};
window.claude={use:async n=>n==='db'?db:n==='user'?{can:async()=>true}:null};
addEventListener('load',()=>setTimeout(()=>scrollTo(0,0),300));const t=new URLSearchParams(location.search).get('tab');try{localStorage.setItem('bk-tab',t||'hisaab')}catch(e){}
})()</script>""" % json.dumps(docs)
h = open(tmpl).read(); i = h.index('<script'); open(out, 'w').write(h[:i] + shim + h[i:])
