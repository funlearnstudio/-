"""No paid API requests: upstream is mocked; real math worker is exercised."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi.testclient import TestClient
import app as module

class Upstream:
    status_code = 200
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def aiter_lines(self):
        for word in ['你好', '，MiniGPT']:
            yield 'data: ' + json.dumps({'choices':[{'delta':{'content':word}}]})
        yield 'data: [DONE]'

class MockClient:
    def __init__(self, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    def stream(self, method, url, **kwargs):
        assert url == 'https://api.openai.com/v1/chat/completions'
        assert kwargs['headers']['Authorization'] == 'Bearer test-api-key'
        assert kwargs['json']['messages'][0]['role'] == 'system'
        return Upstream()

def main():
    with patch.dict(os.environ, {'MINIGPT_ACCESS_TOKEN':'test-pass','OPENAI_API_KEY':'test-api-key', 'OPENAI_BASE_URL':'https://api.openai.com/v1'}, clear=True):
        client=TestClient(module.app)
        auth={'Authorization':'Bearer test-pass'}
        assert client.get('/').status_code == 200
        assert client.get('/api/health').json()['status']=='ok'
        assert client.get('/api/settings').status_code == 401
        assert client.get('/api/settings',headers=auth).json()['configured'] is True
        assert 'test-api-key' not in client.get('/api/settings',headers=auth).text
        body={'messages':[{'role':'user','content':'你好'}]}
        assert client.post('/api/chat',headers=auth,json={'messages':[{'role':'system','content':'bad'}]}).status_code==422
        assert client.post('/api/chat',headers=auth,json={**body,'search':True}).status_code==503
        with patch.object(module.httpx,'AsyncClient',MockClient):
            r=client.post('/api/chat',headers=auth,json=body)
            assert r.status_code==200
            assert '你好' in r.text and '"done": true' in r.text
            assert r.headers['content-type'].startswith('text/event-stream')
        old=Upstream.status_code
        Upstream.status_code=401
        with patch.object(module.httpx,'AsyncClient',MockClient):
            r=client.post('/api/chat',headers=auth,json=body)
            assert 'HTTP 401' in r.text and 'test-api-key' not in r.text
        Upstream.status_code=old
        r=client.post('/api/math',headers=auth,json={'expression':'x^2-4=0','operation':'solve'})
        assert r.status_code==200,r.text
        assert '-2' in r.json()['exact'] and all(v['verified'] for v in r.json()['verification'])
        r=client.post('/api/math',headers=auth,json={'expression':'__import__("os")','operation':'calculate'})
        assert r.status_code==400,r.text
        os.environ.pop('OPENAI_API_KEY')
        assert client.post('/api/chat',headers=auth,json=body).status_code==503
        os.environ.pop('MINIGPT_ACCESS_TOKEN')
        assert client.get('/api/settings',headers=auth).status_code==503
    print('PASS: home, health, auth, secret isolation, validation, SSE, upstream error, math solve, unsafe math rejection, missing config')

if __name__=='__main__': main()
