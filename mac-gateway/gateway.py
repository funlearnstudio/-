"""Run only on the model host; tunnel this port, never Ollama's raw port."""
import hmac
import json
import os
from pathlib import Path
from typing import Literal
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
load_dotenv(Path(__file__).with_name('.env'))
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)

class Message(BaseModel):
    role: Literal['system','user','assistant']
    content: str=Field(min_length=1,max_length=30000)
class Chat(BaseModel):
    model: str=Field(max_length=200)
    messages: list[Message]=Field(min_length=1,max_length=41)
    @model_validator(mode='after')
    def bounded(self):
        if sum(len(m.content) for m in self.messages)>40000:
            raise ValueError('上下文太長')
        return self

@app.post('/api/chat')
async def chat(body:Chat,authorization:str=Header(default='')):
    key=os.getenv('OLLAMA_GATEWAY_TOKEN','')
    if not key:raise HTTPException(503,'Missing gateway token')
    if not hmac.compare_digest(authorization,'Bearer '+key):raise HTTPException(401,'Unauthorized')
    model=os.getenv('OLLAMA_MODEL','qwen2.5:0.5b')
    if body.model!=model:raise HTTPException(400,'模型名稱須與 Mac OLLAMA_MODEL 相同')
    async def events():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45,connect=5)) as client:
                async with client.stream('POST','http://127.0.0.1:11434/api/chat',json={
                    'model':model,'messages':[m.model_dump() for m in body.messages],
                    'stream':True,'options':{'num_predict':2048,'num_ctx':8192}}) as response:
                    if response.status_code>=400:
                        yield json.dumps({'error':'Ollama HTTP '+str(response.status_code)})+'\n'
                        return
                    async for line in response.aiter_lines():
                        if line:yield line+'\n'
        except httpx.RequestError:
            yield json.dumps({'error':'Ollama offline or timed out'})+'\n'
    return StreamingResponse(events(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
