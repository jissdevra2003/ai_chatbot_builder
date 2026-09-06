"""
Development server launcher with safe --reload settings.

By default `uvicorn --reload` watches EVERY file under the working directory.
When documents are uploaded to ./uploads/, the file watcher detects these
changes and restarts the server — killing any context and reloading packages.

This script starts uvicorn with explicit --reload-exclude patterns so that
data directories are ignored by the file watcher.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=[
            "uploads/*",
            "*.sqlite3",
            "*.db",
            "__pycache__/*",
            ".git/*",
        ],
        log_level="info",
    )
