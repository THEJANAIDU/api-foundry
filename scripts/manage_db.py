"""Consistent SQLite snapshots. Restore only while all API processes are stopped."""
import argparse
import os
from pathlib import Path
import sqlite3

def check(path):
    if not path.is_file():raise ValueError("Database file does not exist")
    with sqlite3.connect(str(path)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("Database integrity check failed")
        connection.execute("SELECT id FROM records LIMIT 1")

def snapshot(source,target,replace=False):
    check(source)
    if target.exists() and not replace:raise ValueError("Target exists; choose another name")
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+".tmp")
    if temporary.exists():raise ValueError("Temporary snapshot exists; inspect it before retrying")
    try:
        with sqlite3.connect(str(source)) as src,sqlite3.connect(str(temporary)) as dst:
            src.backup(dst)
        check(temporary)
        os.chmod(temporary,0o600)
        os.replace(temporary,target)
    finally:
        if temporary.exists():temporary.unlink()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["backup","restore","check"])
    parser.add_argument("file",type=Path)
    parser.add_argument("--database",type=Path,default=Path(os.environ.get("DATABASE_PATH","foundry.db")))
    parser.add_argument("--replace",action="store_true",help="Replace destination during restore; stop the API first")
    args=parser.parse_args()
    if args.action=="backup":snapshot(args.database,args.file)
    elif args.action=="restore":
        if args.file.resolve()==args.database.resolve():parser.error("Backup and database must differ")
        for suffix in ("-wal","-shm","-journal"):
            if Path(str(args.database)+suffix).exists():parser.error("SQLite sidecar exists; ensure API stopped and recover database before restore")
        snapshot(args.file,args.database,args.replace)
    else:check(args.file)
    print(args.action+" succeeded")

if __name__=="__main__":main()
