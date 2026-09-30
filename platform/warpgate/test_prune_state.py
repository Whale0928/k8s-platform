import datetime
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import prune_state as maintenance

NOW = datetime.datetime(2026, 9, 30, tzinfo=datetime.timezone.utc)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.executescript("""
            CREATE TABLE sessions(id TEXT PRIMARY KEY, ended TEXT, username TEXT,
                user_id TEXT, target_id TEXT, target_snapshot TEXT);
            CREATE TABLE recordings(session_id TEXT);
            CREATE TABLE log(timestamp TEXT, target TEXT);
            CREATE TABLE failed_login_attempts(timestamp TEXT);
        """)

    def tearDown(self):
        self.connection.close()

    def session(self, identifier, days=2, **fields):
        row = dict(id=identifier, ended=(NOW - datetime.timedelta(days=days)).isoformat(),
                   username=None, user_id=None, target_id=None, target_snapshot=None)
        row.update(fields)
        self.connection.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", tuple(row.values()))
        self.connection.commit()

    def test_preview_does_not_delete(self):
        self.session("old")
        self.connection.execute("PRAGMA query_only=ON")
        self.assertEqual(maintenance.prune(self.connection, NOW)["sessions"], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM sessions").fetchone()[0], 1)

    def test_only_old_ended_anonymous_sessions_are_deleted(self):
        self.session("old")
        self.session("boundary", 1)
        self.session("recent", 0.5)
        self.session("active", ended=None)
        for field in ("username", "user_id", "target_id", "target_snapshot"):
            self.session(field, **{field: "present"})
        self.assertEqual(maintenance.prune(self.connection, NOW, True)["sessions"], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM sessions").fetchone()[0], 7)

    def test_recorded_session_is_preserved(self):
        self.session("recorded")
        self.connection.execute("INSERT INTO recordings VALUES('recorded')")
        self.connection.commit()
        self.assertEqual(maintenance.prune(self.connection, NOW, True)["sessions"], 0)

    def test_multiple_batches_and_repeated_execution(self):
        for i in range(1201):
            self.session(str(i))
        self.assertEqual(maintenance.prune(self.connection, NOW, True)["sessions"], 1201)
        self.assertEqual(maintenance.prune(self.connection, NOW, True)["sessions"], 0)

    def test_log_and_login_failure_retention_boundaries(self):
        for days, target in ((8, "normal"), (7, "normal"), (20, "audit"), (31, "audit")):
            self.connection.execute("INSERT INTO log VALUES(?,?)",
                                    ((NOW - datetime.timedelta(days=days)).isoformat(), target))
        for days in (8, 7):
            self.connection.execute("INSERT INTO failed_login_attempts VALUES(?)",
                                    ((NOW - datetime.timedelta(days=days)).isoformat(),))
        self.connection.commit()
        result = maintenance.prune(self.connection, NOW, True)
        self.assertEqual(result["log"], 2)
        self.assertEqual(result["failed_login_attempts"], 1)

    def test_config_change_is_scoped_and_requires_both_keys(self):
        text = ("http:\n  retention: keep\nlog:\n  retention: 7days\n"
                "  audit_retention: 365days\n  format: text\nssh:\n  retention: keep\n")
        configured = maintenance.configured_text(text)
        self.assertEqual(configured.count("30days"), 2)
        self.assertEqual(configured.count("retention: keep"), 2)
        with self.assertRaises(ValueError):
            maintenance.configured_text("log:\n  retention: 7days\n")

    def test_backup_is_complete_private_and_never_overwritten(self):
        self.session("preserved")
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "backup.sqlite3"
            maintenance.backup(self.connection, destination)
            copy = sqlite3.connect(destination)
            self.assertEqual(copy.execute("SELECT count(*) FROM sessions").fetchone()[0], 1)
            copy.close()
            self.assertEqual(os.stat(destination).st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                maintenance.backup(self.connection, destination)

    def test_initial_apply_backs_up_before_configuring_and_deleting(self):
        self.session("old")
        self.session("authenticated", username="member")
        self.connection.execute("CREATE TABLE parameters(login_protection_retention_seconds INTEGER)")
        self.connection.execute("INSERT INTO parameters VALUES(2592000)")
        self.connection.commit()
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "db.sqlite3"
            config = Path(folder) / "warpgate.yaml"
            original = "log:\n  retention: 7days\n  audit_retention: 365days\n"
            config.write_text(original)
            copy = sqlite3.connect(db)
            self.connection.backup(copy)
            copy.close()
            destination = Path(folder) / "maintenance" / "backup.sqlite3"
            arguments = ["prune_state.py", "--db", str(db), "--config", str(config),
                         "--apply", "--configure", "--backup", str(destination)]
            with patch("sys.argv", arguments), redirect_stdout(io.StringIO()):
                maintenance.main()
            copy = sqlite3.connect(destination)
            self.assertEqual(copy.execute("SELECT count(*) FROM sessions").fetchone()[0], 2)
            copy.close()
            live = sqlite3.connect(db)
            self.assertEqual(live.execute("SELECT id FROM sessions").fetchall(), [("authenticated",)])
            self.assertEqual(live.execute("SELECT * FROM parameters").fetchone(), (604800,))
            live.close()
            self.assertEqual(config.read_text().count("30days"), 2)
            self.assertEqual(destination.with_name("warpgate original.yaml").read_text(), original)


if __name__ == "__main__":
    unittest.main()
