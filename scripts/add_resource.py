"""Usage: python scripts/add_resource.py books title:str pages:int"""
import json
import re
import sys
from pathlib import Path
path=Path(__file__).resolve().parents[1]/"app/resources.json"
if len(sys.argv)<3 or not re.fullmatch(r"[a-z][a-z0-9_]{0,40}",sys.argv[1]):
    sys.exit("Usage: add_resource.py books title:str pages:int")
resources=json.loads(path.read_text())
name=sys.argv[1]
if name in resources:
    sys.exit("Resource already exists")
fields={}
for field in sys.argv[2:]:
    key,kind=field.split(":")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}",key) or kind not in ("str","int","float","bool"):
        sys.exit("Fields must be safe identifiers with str/int/float/bool types")
    fields[key]=kind
resources[name]=fields
path.write_text(json.dumps(resources,indent=2)+"\n")
print("Created /v1/"+name+"; restart the server and open /docs")
