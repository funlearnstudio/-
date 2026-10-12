"""Brave Search adapter, adapted from MiniGPT v0.4."""
import httpx
from . import storage as st

def search(query,count=5):
    if not st.setting('web_enabled',False):raise ValueError('請先啟用網路搜尋；查詢字詞會送給搜尋供應商')
    if not 1<=len(query)<=500:raise ValueError('搜尋詞需1至500字元')
    key=st.secret('brave_key','BRAVE_API_KEY')
    if not key:raise ValueError('請設定Brave Search API key')
    with httpx.Client(timeout=20) as c:
        response=c.get('https://api.search.brave.com/res/v1/web/search',params={'q':query,'count':max(1,min(10,int(count)))},headers={'X-Subscription-Token':key,'Accept':'application/json'})
    if response.status_code>=400:raise ValueError(f'Brave Search HTTP {response.status_code}；請檢查金鑰與額度')
    rows=[{'title':r['title'],'url':r['url'],'description':r.get('description','')} for r in response.json().get('web',{}).get('results',[])]
    st.record('search',{'query':query,'results':rows});return rows
