"""Small localhost-only client for the user-enabled UE MCP server."""
import json
import sys
import http.client
from pathlib import Path

class Client:
    def __init__(self):
        self.headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
        self.seq=0
        self.rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'CodexT05','version':'1'}})
        self.rpc('notifications/initialized',{},notification=True)

    def rpc(self,method,params,notification=False):
        self.seq+=1
        body={'jsonrpc':'2.0','method':method,'params':params}
        if not notification: body['id']=self.seq
        connection=http.client.HTTPConnection('127.0.0.1',8000,timeout=45)
        try:
            connection.request('POST','/mcp',body=json.dumps(body).encode('utf-8'),headers=self.headers)
            r=connection.getresponse()
            if r.headers.get('Mcp-Session-Id'): self.headers['Mcp-Session-Id']=r.headers['Mcp-Session-Id']
            if 'text/event-stream' in r.headers.get('Content-Type',''):
                while True:
                    line=r.readline().decode('utf-8').strip()
                    if line.startswith('data: '):
                        raw=line[6:]
                        break
                    if not line and r.isclosed(): raise RuntimeError('MCP stream closed without result')
            else: raw=r.read().decode('utf-8')
        finally: connection.close()
        if not raw: return None
        if raw.lstrip().startswith('event:'):
            raw='\n'.join(s[6:] for s in raw.splitlines() if s.startswith('data: '))
        data=json.loads(raw)
        if 'error' in data: raise RuntimeError(data['error'])
        return data.get('result',data)

    def tool(self,name,args=None):
        return self.rpc('tools/call',{'name':name,'arguments':args or {}})

if __name__=='__main__':
    c=Client()
    args=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig')) if len(sys.argv)>2 else {}
    result=c.tool(sys.argv[1],args)
    print(json.dumps(result,ensure_ascii=False,indent=2))
