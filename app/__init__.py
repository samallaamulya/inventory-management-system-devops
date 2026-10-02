import os
import sqlite3

from flask import Flask, current_app, g


def get_db():
    """Return a per-request SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sku           TEXT NOT NULL UNIQUE,
            name          TEXT NOT NULL,
            category      TEXT NOT NULL DEFAULT 'General',
            quantity      INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            price         REAL NOT NULL DEFAULT 0 CHECK (price >= 0),
            reorder_level INTEGER NOT NULL DEFAULT 5,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get(
        "DATABASE_PATH", os.path.join(os.getcwd(), "inventory.db")
    )
    if test_config:
        app.config.update(test_config)

    init_db(app)
    app.teardown_appcontext(close_db)

    from .routes import bp
    app.register_blueprint(bp)
    return app
