# Clinic Feedback Portal (SQLite)

The page saves feedback through a small Python API into `clinic_feedback.db` in this folder. The database and `feedback` table are created automatically the first time the server starts. SQLite is included with Python; there are no external Python packages to install.

## Run it

1. Install Python 3 if it is not already installed.
2. Open a terminal in this folder and run `python server.py`.
3. Open http://127.0.0.1:8000 in your browser.
4. Click **Dashboard** to view feedback stored in the database.
5. Stop the server with Ctrl+C. Keep `clinic_feedback.db` to retain the records.

Do not open `index.html` directly as a file. It must be served by `server.py` so the page can call the API.

This is a local demo server. The dashboard does not have administrator login; do not expose it to a public network or use it for real patient information without adding authentication, HTTPS, backups, and appropriate privacy/security controls.
