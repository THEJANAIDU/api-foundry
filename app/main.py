"""API Foundry: configuration-driven, owner-isolated resources."""
import asyncio
import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ConfigDict, create_model
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("foundry")

def create_app(database=None, credentials=None, rate_limit=120):
    tokens = credentials if credentials is not None else json.loads(os.environ.get("API_TOKENS", "{}"))
    if not tokens:
        raise RuntimeError('Set API_TOKENS to a JSON token map; see README.md')
    db = sqlite3.connect(database or os.environ.get("DATABASE_PATH", "foundry.db"), check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS records (resource TEXT, id TEXT PRIMARY KEY, owner TEXT, body TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS retries (owner TEXT, resource TEXT, key TEXT, digest TEXT, body TEXT, PRIMARY KEY(owner,resource,key))")
    db.commit()
    app = FastAPI(title="API Foundry", version="0.2.0", description="Generate owner-isolated APIs from app/resources.json. Try /docs.")
    app.state.db = db
    buckets = {}
    request_lock = asyncio.Lock()
    bearer = HTTPBearer(auto_error=False)

    def principal(auth: HTTPAuthorizationCredentials = Depends(bearer)):
        token = auth.credentials if auth else ""
        for known, identity in tokens.items():
            if secrets.compare_digest(token, known):
                return identity
        raise HTTPException(401, "A valid bearer token is required", headers={"WWW-Authenticate": "Bearer"})

    def permission(identity, scope):
        if scope not in identity.get("scopes", []):
            raise HTTPException(403, "Missing scope: " + scope)

    @app.middleware("http")
    async def telemetry(request, call_next):
        start = time.monotonic()
        rid = str(uuid4())
        # Per-process IP bucket, intended only for a local single-process MVP.
        key = request.client.host if request.client else "unknown"
        window, count = buckets.get(key, (start, 0))
        if start - window >= 60:
            window, count = start, 0
        if count >= rate_limit:
            response = JSONResponse({"type":"about:blank","title":"Too Many Requests","status":429,"detail":"Retry after the rate window resets","instance":request.url.path}, status_code=429, media_type="application/problem+json", headers={"Retry-After":"60"})
        else:
            buckets[key] = (window, count + 1)
            async with request_lock:
                response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault("Cache-Control", "no-store")
        log.info(json.dumps({"request_id":rid,"method":request.method,"path":request.url.path,"status":response.status_code,"duration_ms":round((time.monotonic()-start)*1000,2)}))
        return response

    @app.exception_handler(StarletteHTTPException)
    async def problem(request, exc):
        from http import HTTPStatus
        return JSONResponse({"type":"about:blank","title":HTTPStatus(exc.status_code).phrase,"status":exc.status_code,"detail":str(exc.detail),"instance":request.url.path}, status_code=exc.status_code, headers=exc.headers, media_type="application/problem+json")

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse({"type":"about:blank","title":"Unprocessable Content","status":422,"detail":"Request does not match the schema","instance":request.url.path,"errors":[{"location":list(e["loc"]),"message":e["msg"]} for e in exc.errors()]}, status_code=422, media_type="application/problem+json")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home():
        return Path(__file__).with_name("index.html").read_text()

    @app.get("/learn", response_class=HTMLResponse, include_in_schema=False)
    def learn():
        return Path(__file__).with_name("learn.html").read_text()


    @app.get("/health", tags=["platform"])
    def health():
        db.execute("SELECT 1")
        return {"status":"ok"}

    def register(resource, fields):
        types = {"str":str,"int":int,"bool":bool,"float":float}
        Model = create_model(resource.title() + "Input", __config__=ConfigDict(extra="forbid", strict=True), **{k:(types[v], ...) for k,v in fields.items()})
        base = "/v1/" + resource

        def find(id, owner):
            row = db.execute("SELECT body FROM records WHERE resource=? AND id=? AND owner=?", (resource,id,owner)).fetchone()
            if row is None:
                raise HTTPException(404,"Resource not found")
            return json.loads(row[0])

        @app.get(base, tags=[resource], name="list_"+resource)
        def listing(offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),q:str=Query("",max_length=100),sort:str=Query("id",pattern="^-?id$"),identity=Depends(principal)):
            permission(identity,"read")
            rows = db.execute("SELECT body FROM records WHERE resource=? AND owner=? ORDER BY id " + ("DESC" if sort.startswith("-") else "ASC"),(resource,identity["subject"])).fetchall()
            items = [json.loads(row[0]) for row in rows]
            items = [x for x in items if q.lower() in json.dumps(x["data"]).lower()]
            from urllib.parse import urlencode
            next_link = base+"?"+urlencode({"offset":offset+limit,"limit":limit,"q":q,"sort":sort}) if offset+limit<len(items) else None
            return {"items":items[offset:offset+limit],"total":len(items),"links":{"self":base,"next":next_link}}

        @app.post(base,status_code=201,tags=[resource],name="create_"+resource)
        def create(payload:Model,request:Request,response:Response,identity=Depends(principal)):
            permission(identity,"write")
            data = payload.model_dump()
            if any(isinstance(v,str) and len(v)>10000 for v in data.values()):
                raise HTTPException(413,"Field too large")
            digest = hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
            key = request.headers.get("Idempotency-Key")
            if key and len(key)>200:
                raise HTTPException(400,"Idempotency key too long")
            with db:
                if key:
                    previous = db.execute("SELECT digest,body FROM retries WHERE owner=? AND resource=? AND key=?",(identity["subject"],resource,key)).fetchone()
                    if previous:
                        if previous[0]!=digest:
                            raise HTTPException(409,"Idempotency key reused with different payload")
                        item=json.loads(previous[1])
                        response.headers["Location"]=item["links"]["self"]
                        return item
                id = str(uuid4())
                item={"id":id,"data":data,"links":{"self":base+"/"+id,"collection":base}}
                body=json.dumps(item)
                db.execute("INSERT INTO records VALUES(?,?,?,?)",(resource,id,identity["subject"],body))
                if key:
                    db.execute("INSERT INTO retries VALUES(?,?,?,?,?)",(identity["subject"],resource,key,digest,body))
            response.headers["Location"]=base+"/"+id
            return item

        @app.get(base+"/{id}",tags=[resource],name="get_"+resource)
        def get(id:str,request:Request,response:Response,identity=Depends(principal)):
            permission(identity,"read")
            item=find(id,identity["subject"])
            etag='"'+hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()+'"'
            if request.headers.get("If-None-Match")==etag:
                return Response(status_code=304,headers={"ETag":etag})
            response.headers["ETag"]=etag
            return item

        @app.put(base+"/{id}",tags=[resource],name="replace_"+resource)
        def replace(id:str,payload:Model,identity=Depends(principal)):
            permission(identity,"write")
            item=find(id,identity["subject"])
            item["data"]=payload.model_dump()
            with db:
                db.execute("UPDATE records SET body=? WHERE id=? AND owner=?",(json.dumps(item),id,identity["subject"]))
            return item

        @app.delete(base+"/{id}",status_code=204,tags=[resource],name="delete_"+resource)
        def delete(id:str,identity=Depends(principal)):
            permission(identity,"write")
            find(id,identity["subject"])
            with db:
                db.execute("DELETE FROM records WHERE id=? AND owner=?",(id,identity["subject"]))
            return Response(status_code=204)

    for resource,fields in json.loads(Path(__file__).with_name("resources.json").read_text()).items():
        register(resource,fields)
    return app
