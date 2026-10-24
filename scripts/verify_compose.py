"""Disposable deployment acceptance test. Never runs against production volumes."""
import json
import os
from pathlib import Path
import secrets
import shutil
import ssl
import time
import subprocess
import sys
import tempfile
from urllib.request import Request,urlopen
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]

def main():
    # A separate project owns fresh volumes; only those volumes are removed afterward.
    project="foundry-verify-"+secrets.token_hex(4)
    env=os.environ.copy();env["LOCAL_PORT"]=os.environ.get("VERIFY_PORT","18080")
    compose=["docker","compose","-p",project,"-f","compose.yaml","-f","deploy/compose.local.yaml"]
    def run(*args):subprocess.run(compose+list(args),cwd=ROOT,env=env,check=True)
    base="http://127.0.0.1:"+env["LOCAL_PORT"]
    token=(ROOT/".deploy-token").read_text().strip()
    def api(method,path,body=None):
        headers={"Authorization":"Bearer "+token}
        if body is not None:headers["Content-Type"]="application/json"
        with urlopen(Request(base+path,method=method,headers=headers,data=json.dumps(body).encode() if body is not None else None),timeout=15) as response:
            raw=response.read();return json.loads(raw) if raw else None
    with tempfile.TemporaryDirectory() as tmp:
        try:
            run("up","-d","--build","--wait")
            subprocess.run([sys.executable,str(ROOT/"scripts/smoke_deploy.py"),"--url",base],check=True)
            item=api("POST","/v1/tasks",{"title":"persistence-"+str(uuid4()),"done":False})
            path=item["links"]["self"]
            run("restart","api")
            run("up","-d","--wait")
            assert api("GET",path)["id"]==item["id"]
            run("exec","-T","api","python","scripts/manage_db.py","backup","/data/checkpoint.sqlite3")
            exported=subprocess.run(compose+["exec","-T","api","cat","/data/checkpoint.sqlite3"],cwd=ROOT,env=env,stdout=subprocess.PIPE,check=True)
            (Path(tmp)/"checkpoint.sqlite3").write_bytes(exported.stdout)
            subprocess.run([sys.executable,str(ROOT/"scripts/manage_db.py"),"check",str(Path(tmp)/"checkpoint.sqlite3")],check=True)
            api("DELETE",path)
            run("stop","api")
            importer="import os,sys; from pathlib import Path; p=Path('/data/restore.sqlite3'); p.write_bytes(sys.stdin.buffer.read()); os.chmod(p,0o600)"
            subprocess.run(compose+["run","--rm","-T","--no-deps","api","python","-c",importer],cwd=ROOT,env=env,input=(Path(tmp)/"checkpoint.sqlite3").read_bytes(),check=True)
            run("run","--rm","--no-deps","api","python","scripts/manage_db.py","restore","/data/restore.sqlite3","--replace")
            run("up","-d","--wait")
            assert api("GET",path)["id"]==item["id"]
            api("DELETE",path)
            run("run","--rm","--no-deps","gateway","caddy","validate","--config","/etc/caddy/Caddyfile","--adapter","caddyfile")
            # Validate the real public Caddyfile without attempting DNS or ACME issuance.
            public=["docker","compose","-p",project,"-f","compose.yaml","-f","deploy/compose.public.yaml"]
            subprocess.run(public+["config","--quiet"],cwd=ROOT,env=env,check=True)
            subprocess.run(public+["run","--rm","--no-deps","gateway","caddy","validate","--config","/etc/caddy/Caddyfile","--adapter","caddyfile"],cwd=ROOT,env=env,check=True)
            tls=["docker","compose","-p",project,"-f","compose.yaml","-f","deploy/compose.tls-test.yaml"]
            subprocess.run(tls+["up","-d","--wait"],cwd=ROOT,env=env,check=True)
            ca=Path(tmp)/"root.crt"
            for attempt in range(30):
                exported=subprocess.run(tls+["cp","gateway:/data/caddy/pki/authorities/local/root.crt",str(ca)],cwd=ROOT,env=env,capture_output=True)
                if exported.returncode==0:break
                time.sleep(1)
            else:raise RuntimeError("Caddy did not create local CA")
            tlsbase="https://localhost:"+env.get("TLS_TEST_PORT","18443")
            context=ssl.create_default_context(cafile=str(ca))
            for attempt in range(30):
                try:
                    with urlopen(tlsbase+"/health",timeout=3,context=context) as response:
                        assert response.status==200
                    break
                except OSError:time.sleep(1)
            else:raise RuntimeError("HTTPS did not become healthy")
            subprocess.run([sys.executable,str(ROOT/"scripts/smoke_deploy.py"),"--url",tlsbase,"--ca-file",str(ca)],check=True)
            print("PASS: container CRUD, restart persistence, SQLite backup/export/restore, HTTP proxy, verified local HTTPS using public Caddyfile")
        finally:
            # This random test project never shares volumes with api-foundry.
            run("down","--volumes","--remove-orphans")

if __name__=="__main__":main()
