import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
spec=importlib.util.spec_from_file_location('gateway',Path(__file__).resolve().parents[1]/'mac-gateway/gateway.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Response:
    status_code=200
    async def __aenter__(self):return self
    async def __aexit__(self,*a):pass
    async def aiter_lines(self):
        yield '{"message":{"content":"本機回覆"},"done":false}'
        yield '{"done":true}'
class Client:
    def __init__(self,**kw):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*a):pass
    def stream(self,method,url,**kw):
        assert url=='http://127.0.0.1:11434/api/chat'
        assert kw['json']['model']=='qwen2.5:0.5b'
        assert kw['json']['options']['num_predict']==2048
        return Response()
with patch.dict(os.environ,{'OLLAMA_GATEWAY_TOKEN':'secret','OLLAMA_MODEL':'qwen2.5:0.5b'},clear=True):
    client=TestClient(m.app);body={'model':'qwen2.5:0.5b','messages':[{'role':'user','content':'hello'}]}
    assert client.post('/api/chat',json=body).status_code==401
    auth={'Authorization':'Bearer secret'}
    assert client.post('/api/chat',headers=auth,json={**body,'model':'other'}).status_code==400
    with patch.object(m.httpx,'AsyncClient',Client):
        r=client.post('/api/chat',headers=auth,json=body)
        assert r.status_code==200 and '本機回覆' in r.text
    assert client.delete('/api/delete',headers=auth).status_code==404
print('PASS: gateway auth, fixed model, localhost-only upstream, NDJSON forwarding, no management route')
