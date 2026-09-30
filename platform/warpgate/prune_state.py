"""Bound Warpgate history without removing active or authenticated sessions."""

import argparse
from contextlib import closing
import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

BATCH_SIZE = 500


def policies(now):
    def cutoff(days):
        return (now - datetime.timedelta(days=days)).isoformat()

    return [
        ("sessions", "ended IS NOT NULL AND username IS NULL AND user_id IS NULL "
         "AND target_id IS NULL AND target_snapshot IS NULL "
         "AND julianday(ended)<julianday(?) AND NOT EXISTS "
         "(SELECT 1 FROM recordings WHERE recordings.session_id=sessions.id)",
         (cutoff(1),)),
        ("failed_login_attempts", "julianday(timestamp)<julianday(?)", (cutoff(7),)),
        ("log", "(target!='audit' AND julianday(timestamp)<julianday(?)) OR "
         "(target='audit' AND julianday(timestamp)<julianday(?))",
         (cutoff(7), cutoff(30))),
    ]


def prune(connection, now, apply=False):
    result = {}
    for table, condition, values in policies(now):
        if not apply:
            result[table] = connection.execute(
                f"SELECT count(*) FROM {table} WHERE {condition}", values
            ).fetchone()[0]
            continue
        deleted, after = 0, 0
        while True:
            # Keyset traversal avoids repeatedly scanning already visited rows.
            rows = connection.execute(
                f"SELECT rowid FROM {table} WHERE rowid>? AND ({condition}) "
                "ORDER BY rowid LIMIT ?", (after, *values, BATCH_SIZE)
            ).fetchall()
            if not rows:
                break
            ids = [row[0] for row in rows]
            with connection:
                deleted += connection.execute(
                    f"DELETE FROM {table} WHERE rowid IN "
                    f"({','.join('?' for _ in ids)}) AND ({condition})",
                    (*ids, *values),
                ).rowcount
            after = ids[-1]
        result[table] = deleted
    return result


def configured_text(text):
    match = re.search(r"(?m)^log:\s*\n(?:^[ \t].*\n|^\s*\n)*", text)
    if not match:
        raise ValueError("log configuration section is missing")
    section = match.group()
    for key in ("retention", "audit_retention"):
        section, count = re.subn(
            rf"(?m)^  {key}:.*$", f"  {key}: 30days", section
        )
        if count != 1:
            raise ValueError(f"expected one log.{key} entry")
    return text[:match.start()] + section + text[match.end():]


def backup(connection, destination):
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    required = connection.execute("PRAGMA page_count").fetchone()[0] * \
        connection.execute("PRAGMA page_size").fetchone()[0]
    space = os.statvfs(destination.parent)
    if space.f_bavail * space.f_frsize < required + 64 * 1024 * 1024:
        raise RuntimeError("insufficient space for a complete backup")
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(destination)) as copy:
        connection.backup(copy, pages=256, sleep=0.05)
        if copy.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise RuntimeError("backup integrity check failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="/data/db/db.sqlite3")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--config", default="/data/warpgate.yaml")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if args.configure and args.apply and not args.backup:
        parser.error("initial configuration requires --backup")
    config = Path(args.config)
    new_text = configured_text(config.read_text()) if args.configure else None
    mode = "rw" if args.apply else "ro"
    connection = sqlite3.connect(
        Path(args.db).resolve().as_uri() + f"?mode={mode}", uri=True, timeout=5
    )
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA cache_size=-2048")
    connection.execute("PRAGMA temp_store=MEMORY")
    if not args.apply:
        connection.execute("PRAGMA query_only=ON")
    if args.apply and args.backup:
        backup(connection, args.backup)
    if args.apply and args.configure:
        original = args.backup.with_name("warpgate original.yaml")
        with original.open("x") as output:
            output.write(config.read_text())
        with tempfile.NamedTemporaryFile(mode="w", dir=config.parent, delete=False) as output:
            output.write(new_text)
            temp_name = output.name
        os.replace(temp_name, config)
        with connection:
            connection.execute(
                "UPDATE parameters SET login_protection_retention_seconds=?", (7 * 86400,)
            )
    now = datetime.datetime.now(datetime.timezone.utc)
    print(json.dumps({"mode": "apply" if args.apply else "preview",
                      "affected_rows": prune(connection, now, args.apply),
                      "configure": args.configure}), flush=True)
    connection.close()


if __name__ == "__main__":
    main()
