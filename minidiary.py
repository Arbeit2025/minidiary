from flask import Flask, request, redirect, url_for, render_template_string, g, abort
import sqlite3
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("diary.db")

# -----------------------------
# DB helpers
# -----------------------------
def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(_):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

# -----------------------------
# HTML templates (embedded)
# -----------------------------
BASE_CSS = """
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; line-height: 1.5; }
h1 { margin: 0 0 12px; }
h2 { margin-top: 20px; }
.box { max-width: 760px; }
input, textarea { width: 100%; max-width: 760px; padding: 10px; }
textarea { resize: vertical; }
.row { display: flex; gap: 12px; flex-wrap: wrap; }
.meta { color: #666; font-size: 0.95rem; }
.btn { padding: 8px 12px; cursor: pointer; }
hr { margin: 18px 0; }
ul { padding-left: 18px; }
li { margin: 8px 0; }
.inline { display: inline; }
pre { white-space: pre-wrap; background: #f6f6f6; padding: 12px; border-radius: 8px; }
a { text-decoration: none; }
a:hover { text-decoration: underline; }
"""

INDEX_HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>日記ツール</title>
  <style>{{ css }}</style>
</head>
<body>
  <div class="box">
    <h1>日記ツール</h1>
    <p class="meta">単一ファイル版 / SQLite保存（diary.db）</p>

    <h2>新規作成</h2>
    <form method="post" action="{{ url_for('create') }}">
      <div class="row">
        <div style="flex: 1 1 420px;">
          <label>タイトル</label>
          <input name="title" required maxlength="120" placeholder="例：2026-03-03 今日のこと">
        </div>
      </div>

      <div style="margin-top: 10px;">
        <label>本文</label>
        <textarea name="content" rows="8" required placeholder="思ったこと、やったこと、残したいこと…"></textarea>
      </div>

      <div style="margin-top: 10px;">
        <button class="btn" type="submit">保存</button>
      </div>
    </form>

    <hr>

    <h2>一覧（新しい順）</h2>
    {% if entries %}
      <ul>
        {% for e in entries %}
          <li>
            <a href="{{ url_for('view', entry_id=e['id']) }}">{{ e['title'] }}</a>
            <span class="meta">（{{ e['created_at'] }}）</span>
            <form class="inline" method="post" action="{{ url_for('delete', entry_id=e['id']) }}">
              <button class="btn" type="submit" onclick="return confirm('削除しますか？')">削除</button>
            </form>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <p>まだ日記がありません。</p>
    {% endif %}
  </div>
</body>
</html>
"""

VIEW_HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{{ entry['title'] }} - 日記ツール</title>
  <style>{{ css }}</style>
</head>
<body>
  <div class="box">
    <p><a href="{{ url_for('index') }}">← 一覧へ戻る</a></p>

    <h1>{{ entry['title'] }}</h1>
    <p class="meta">作成: {{ entry['created_at'] }}</p>

    <pre>{{ entry['content'] }}</pre>

    <form method="post" action="{{ url_for('delete', entry_id=entry['id']) }}">
      <button class="btn" type="submit" onclick="return confirm('削除しますか？')">この日記を削除</button>
    </form>
  </div>
</body>
</html>
"""

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    db = get_db()
    entries = db.execute(
        "SELECT id, title, created_at FROM entries ORDER BY id DESC"
    ).fetchall()
    return render_template_string(INDEX_HTML, entries=entries, css=BASE_CSS)

@app.route("/create", methods=["POST"])
def create():
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()

    # minimal validation
    if not title or not content:
        return redirect(url_for("index"))

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = get_db()
    db.execute(
        "INSERT INTO entries (title, content, created_at) VALUES (?, ?, ?)",
        (title, content, created_at),
    )
    db.commit()
    return redirect(url_for("index"))

@app.route("/entry/<int:entry_id>", methods=["GET"])
def view(entry_id: int):
    db = get_db()
    entry = db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if entry is None:
        abort(404)
    return render_template_string(VIEW_HTML, entry=entry, css=BASE_CSS)

@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete(entry_id: int):
    db = get_db()
    db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    db.commit()
    return redirect(url_for("index"))

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)