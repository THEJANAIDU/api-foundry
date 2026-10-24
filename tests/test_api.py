from fastapi.testclient import TestClient
from app.main import create_app

TOKENS={"alice-key":{"subject":"alice","scopes":["read","write"]},"bob-key":{"subject":"bob","scopes":["read","write"]},"reader-key":{"subject":"alice","scopes":["read"]}}
def client(limit=1000):
    return TestClient(create_app(':memory:',TOKENS,limit))
def auth(token='alice-key',**extra):
    return {'Authorization':'Bearer '+token,**extra}
def add(c,**headers):
    return c.post('/v1/tasks',json={'title':'Build something','done':False},headers=auth(**headers))
def test_crud_and_contract():
    c=client()
    assert c.get('/health').status_code==200
    spec=c.get('/openapi.json').json()
    assert '/v1/tasks/{id}' in spec['paths']
    r=add(c); assert r.status_code==201
    path=r.headers['location']
    assert c.get(path,headers=auth()).json()==r.json()
    assert c.put(path,json={'title':'Shipped','done':True},headers=auth()).status_code==200
    assert c.get('/v1/tasks?q=Shipped&limit=1',headers=auth()).json()['total']==1
    assert c.delete(path,headers=auth()).status_code==204
    assert c.get(path,headers=auth()).status_code==404

def test_ownership_and_scopes():
    c=client(); path=add(c).headers['location']
    for method,kw in [('get',{}),('put',{'json':{'title':'attack','done':True}}),('delete',{})]:
        assert getattr(c,method)(path,headers=auth('bob-key'),**kw).status_code==404
    assert c.get('/v1/tasks',headers=auth('bob-key')).json()['total']==0
    assert c.post('/v1/tasks',json={'title':'x','done':False},headers=auth('reader-key')).status_code==403
    assert c.get('/v1/tasks').status_code==401

def test_validation_problem_and_pagination():
    c=client()
    for body in ({'title':'x','done':False,'owner':'bob'},{'title':5,'done':False},{}):
        r=c.post('/v1/tasks',json=body,headers=auth()); assert r.status_code==422
        assert r.headers['content-type']=='application/problem+json'
    assert c.get('/v1/tasks?limit=1000',headers=auth()).status_code==422
    add(c); add(c)
    page=c.get('/v1/tasks?limit=1',headers=auth()).json()
    assert len(page['items'])==1 and page['links']['next']

def test_retry_and_etag():
    c=client(); first=add(c,**{'Idempotency-Key':'retry'})
    assert add(c,**{'Idempotency-Key':'retry'}).json()==first.json()
    assert c.get('/v1/tasks',headers=auth()).json()['total']==1
    assert c.post('/v1/tasks',headers=auth(**{'Idempotency-Key':'retry'}),json={'title':'different','done':False}).status_code==409
    path=first.headers['location']; etag=c.get(path,headers=auth()).headers['etag']
    assert c.get(path,headers=auth(**{'If-None-Match':etag})).status_code==304
    assert c.get(path,headers=auth()).headers['x-request-id']

def test_rate_limit():
    c=client(1)
    assert c.get('/health').status_code==200
    r=c.get('/health'); assert r.status_code==429 and r.headers['retry-after']=='60'

def test_persistence(tmp_path):
    path=str(tmp_path/'test.db')
    c=TestClient(create_app(path,TOKENS)); item=add(c).headers['location']
    other=TestClient(create_app(path,TOKENS))
    assert other.get(item,headers=auth()).status_code==200

def test_learning_routes():
    c=client()
    page=c.get('/')
    assert page.status_code==200 and 'WATCH THE WIRE' in page.text
    assert 'localStorage' not in page.text
    assert c.get('/learn').status_code==200
    assert 'Your first API' in c.get('/learn').text

def test_generator_adds_resource_without_overwriting(tmp_path):
    import json
    import shutil
    import subprocess
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'app').mkdir(); (tmp_path/'scripts').mkdir()
    shutil.copy(root/'app/resources.json',tmp_path/'app/resources.json')
    shutil.copy(root/'scripts/add_resource.py',tmp_path/'scripts/add_resource.py')
    args=[sys.executable,str(tmp_path/'scripts/add_resource.py'),'books','title:str','pages:int']
    subprocess.run(args,check=True,capture_output=True)
    resources=json.loads((tmp_path/'app/resources.json').read_text())
    assert resources['books']=={'title':'str','pages':'int'}
    assert 'tasks' in resources
    assert subprocess.run(args,capture_output=True).returncode!=0
