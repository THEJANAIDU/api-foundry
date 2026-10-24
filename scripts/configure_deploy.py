"""Create ignored, private deployment configuration without committing secrets."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--domain",default="api.example.com")
    args=parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?",args.domain) or "." not in args.domain:
        parser.error("Use a hostname only, e.g. api.example.com (no scheme or path)")
    targets=[ROOT/".env",ROOT/".deploy-token"]
    if any(path.exists() for path in targets):
        parser.error("Configuration already exists; preserve it or follow the rotation section in docs/DEPLOYMENT.md")
    token=secrets.token_urlsafe(32)
    tokens={token:{"subject":"deployment-owner","scopes":["read","write"]}}
    values=["API_DOMAIN="+args.domain+"\nAPI_TOKENS='"+json.dumps(tokens,separators=(",",":"))+"'\n",token+"\n"]
    for path,value in zip(targets,values):
        fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w") as stream:stream.write(value)
    print("Created .env and .deploy-token. Both are private and ignored by Git. Never share their contents.")

if __name__=="__main__":main()
