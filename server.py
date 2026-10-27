from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import sqlite3
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "clinic_feedback.db"
STATUSES = {"Pending", "Reviewed", "Resolved"}


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                category TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comments TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                date_submitted TEXT NOT NULL
            )
        """)


def row_to_feedback(row):
    return {
        "id": row["id"], "name": row["name"], "visitDate": row["visit_date"],
        "category": row["category"], "rating": str(row["rating"]),
        "comments": row["comments"], "status": row["status"],
        "dateSubmitted": row["date_submitted"]
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("Request is too large.")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if urlparse(self.path).path != "/api/feedback":
            return super().do_GET()
        with connect_db() as db:
            rows = db.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()
        self.send_json([row_to_feedback(row) for row in rows])

    def do_POST(self):
        if urlparse(self.path).path != "/api/feedback":
            return self.send_json({"error": "Not found"}, 404)
        try:
            data = self.read_json()
            name = str(data.get("name", "")).strip()[:200]
            visit_date = str(data.get("visitDate", ""))
            category = str(data.get("category", "")).strip()[:100]
            rating = int(data.get("rating", 0))
            comments = str(data.get("comments", "")).strip()[:10000]
            if not name or not visit_date or not category or not comments or rating not in range(1, 6):
                return self.send_json({"error": "Please provide all required feedback fields."}, 400)
            date_submitted = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
            with connect_db() as db:
                cursor = db.execute("""
                    INSERT INTO feedback (name, visit_date, category, rating, comments, status, date_submitted)
                    VALUES (?, ?, ?, ?, ?, 'Pending', ?)
                """, (name, visit_date, category, rating, comments, date_submitted))
                row = db.execute("SELECT * FROM feedback WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self.send_json(row_to_feedback(row), 201)
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"error": "Invalid feedback data."}, 400)

    def do_PATCH(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "feedback"]:
            return self.send_json({"error": "Not found"}, 404)
        try:
            feedback_id = int(parts[2])
            status = self.read_json().get("status")
            if status not in STATUSES:
                return self.send_json({"error": "Invalid status."}, 400)
            with connect_db() as db:
                cursor = db.execute("UPDATE feedback SET status = ? WHERE id = ?", (status, feedback_id))
            if not cursor.rowcount:
                return self.send_json({"error": "Feedback not found."}, 404)
            return self.send_json({"ok": True})
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"error": "Invalid request."}, 400)

    def do_DELETE(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "feedback"]:
            return self.send_json({"error": "Not found"}, 404)
        try:
            feedback_id = int(parts[2])
            with connect_db() as db:
                cursor = db.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
            if not cursor.rowcount:
                return self.send_json({"error": "Feedback not found."}, 404)
            self.send_response(204)
            self.end_headers()
        except ValueError:
            return self.send_json({"error": "Invalid feedback ID."}, 400)


if __name__ == "__main__":
    initialize_db()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Clinic Feedback Portal: http://127.0.0.1:8000")
    print(f"SQLite database: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer stopped.")
    finally:
        server.server_close()
