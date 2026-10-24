"""One-command local learning server. Run: python3 start.py"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    envdir=ROOT/".venv"
    python=envdir/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not python.exists():
        print("Creating an isolated Python environment...",flush=True)
        venv.create(envdir,with_pip=True)
    requirements=ROOT/"requirements.txt"
    marker=envdir/"foundry-requirements.txt"
    if not marker.exists() or marker.read_text()!=requirements.read_text():
        subprocess.run([str(python),"-m","pip","install","-r",str(requirements)],check=True)
        marker.write_text(requirements.read_text())
    token=secrets.token_urlsafe(32)
    environment=os.environ.copy()
    environment["API_TOKENS"]=json.dumps({token:{"subject":"local-learner","scopes":["read","write"]}})
    print("\nAPI Foundry · LOCAL LEARNING MODE\nOpen http://127.0.0.1:8000\nPaste this token into Connect:\n"+token+"\n\nToken changes on each launch; your tasks remain. Ctrl+C stops the server.\n",flush=True)
    try:
        return subprocess.call([str(python),"-m","uvicorn","app.main:create_app","--factory","--host","127.0.0.1","--port","8000"],env=environment)
    except KeyboardInterrupt:
        return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,subprocess.CalledProcessError) as exc:
        print("Setup failed: "+str(exc)+"\nSee docs/TROUBLESHOOTING.md. Check Python, internet access and folder permissions.",file=sys.stderr)
        sys.exit(1)
