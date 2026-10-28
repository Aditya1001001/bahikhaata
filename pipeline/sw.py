"""Call one Splitwise MCP tool over stdio.
usage: sw.py TOOL 'JSON_ARGS'   -> prints the tool's result text
In dry-run mode this talks to a fake local store instead (see fake_splitwise.py)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bk


class Session:
    """One server process for many calls (add.py adds a batch in one session)."""
    def __init__(self):
        if bk.DRY:
            import fake_splitwise; self.fake = fake_splitwise.Store(); return
        self.fake = None; self.n = 0
        self.p = subprocess.Popen([bk.MCP_PY, '-m', 'splitwise_mcp_server'], cwd=bk.MCP_DIR, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self._send({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "bahikhaata", "version": "1"}}})
        self._recv(0)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, o): self.p.stdin.write(json.dumps(o) + '\n'); self.p.stdin.flush()

    def _recv(self, i):
        while True:
            line = self.p.stdout.readline()
            if not line: raise SystemExit('Splitwise server stopped. Run scripts/doctor.py to see why.')
            m = json.loads(line)
            if m.get('id') == i: return m

    def call(self, tool, args):
        if self.fake: return self.fake.call(tool, args)
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": "tools/call", "params": {"name": tool, "arguments": args}})
        m = self._recv(self.n)
        if 'error' in m: raise SystemExit(json.dumps(m['error']))
        return m['result']['content'][0]['text']

    def close(self):
        if not self.fake: self.p.terminate()


def call(tool, args):
    s = Session()
    try: return s.call(tool, args)
    finally: s.close()


if __name__ == '__main__':
    print(call(sys.argv[1], json.loads(sys.argv[2] if len(sys.argv) > 2 else '{}')))
