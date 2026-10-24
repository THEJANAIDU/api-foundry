"""Exercise a running deployment; creates and deletes one uniquely named test record."""
import argparse
import json
import ssl
import time
from urllib.parse import urlsplit
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://127.0.0.1:8080")
    parser.add_argument("--token-file",type=Path,default=ROOT/".deploy-token")
    parser.add_argument("--ca-file",type=Path,help="Trusted CA file for local HTTPS acceptance tests")
    args=parser.parse_args()
    base=args.url.rstrip("/"); token=args.token_file.read_text().strip()
    parsed=urlsplit(base)
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        parser.error("URL must contain only scheme, host and optional port")
    if not (parsed.scheme=="https" or (parsed.scheme=="http" and parsed.hostname in ("127.0.0.1","localhost"))):
        parser.error("Use loopback HTTP or HTTPS to avoid sending bearer tokens over a network in plaintext")
    context=ssl.create_default_context(cafile=str(args.ca_file) if args.ca_file else None)
    def call(method,path,body=None,auth=True,extra=None):
        headers={"Authorization":"Bearer "+token} if auth else {}
        if body is not None:headers["Content-Type"]="application/json"
        headers.update(extra or {})
        req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
        try: response=urlopen(req,timeout=15,context=context)
        except HTTPError as exc:response=exc
        with response:
            raw=response.read()
            try:data=json.loads(raw) if raw else None
            except ValueError:data=raw.decode(errors="replace")
            return response.status,response.headers,data
    for attempt in range(30):
        try:
            if call("GET","/health",auth=False)[0]==200:break
        except OSError:pass
        time.sleep(.5)
    else:raise RuntimeError("Deployment health did not become ready")
    assert call("GET","/v1/tasks",auth=False)[0]==401
    assert call("POST","/v1/tasks",{"title":"body-limit-test","done":False,"extra":"x"*(1024*1024+1)})[0]==413
    title="deployment-smoke-"+str(uuid4()); key=str(uuid4()); body={"title":title,"done":False}
    status,headers,item=call("POST","/v1/tasks",body,extra={"Idempotency-Key":key})
    assert status==201 and headers.get("X-Request-ID")
    path=item["links"]["self"]
    try:
        assert call("POST","/v1/tasks",body,extra={"Idempotency-Key":key})[2]["id"]==item["id"]
        status,headers,_=call("GET",path);assert status==200
        assert call("GET",path,extra={"If-None-Match":headers["ETag"]})[0]==304
        assert call("PUT",path,{"title":title,"done":True})[0]==200
        assert call("POST","/v1/tasks",{"title":title,"done":"false"})[0]==422
    finally:
        assert call("DELETE",path)[0]==204
    assert call("GET",path)[0]==404
    print("PASS: health, auth, proxy body limit, create, retry, read, ETag, update, validation, delete")

if __name__=="__main__":main()
