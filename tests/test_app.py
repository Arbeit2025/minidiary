import importlib.util
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

APP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "minidiary.py"
)


def load_app(db_path):
    spec = importlib.util.spec_from_file_location("minidiary", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DB_PATH = Path(db_path)
    module.init_db()
    return module


class MinidiaryTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(self.db_path)
        self.mod = load_app(self.db_path)
        self.client = self.mod.app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def count(self):
        c = sqlite3.connect(self.db_path)
        n = c.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        c.close()
        return n

    def test_index_ok(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_create_and_view(self):
        self.client.post(
            "/create", data={"title": "テスト日記", "content": "今日の出来事"}
        )
        self.assertEqual(self.count(), 1)
        c = sqlite3.connect(self.db_path)
        mid = c.execute("SELECT id FROM entries").fetchone()[0]
        c.close()
        res = self.client.get(f"/entry/{mid}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("今日の出来事", res.get_data(as_text=True))

    def test_create_empty_ignored(self):
        self.client.post("/create", data={"title": " ", "content": " "})
        self.assertEqual(self.count(), 0)

    def test_delete_entry(self):
        self.client.post("/create", data={"title": "t", "content": "c"})
        c = sqlite3.connect(self.db_path)
        mid = c.execute("SELECT id FROM entries").fetchone()[0]
        c.close()
        self.client.post(f"/delete/{mid}")
        self.assertEqual(self.count(), 0)
        res = self.client.get(f"/entry/{mid}")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
