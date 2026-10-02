import sqlite3

from flask import Blueprint, jsonify, render_template, request

from . import get_db

bp = Blueprint("inventory", __name__)


def _validate(data, partial=False):
    """Validate product payload. Returns (clean_dict, error_message)."""
    clean = {}
    if not partial:
        for field in ("sku", "name"):
            if not str(data.get(field, "")).strip():
                return None, f"'{field}' is required"

    for field in ("sku", "name", "category"):
        if field in data:
            clean[field] = str(data[field]).strip()
            if field != "category" and not clean[field]:
                return None, f"'{field}' cannot be empty"

    for field, cast in (("quantity", int), ("reorder_level", int), ("price", float)):
        if field in data:
            try:
                clean[field] = cast(data[field])
            except (TypeError, ValueError):
                return None, f"'{field}' must be a number"
            if clean[field] < 0:
                return None, f"'{field}' cannot be negative"
    return clean, None


def _fetch(db, pid):
    return db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/health")
def health():
    return jsonify(status="ok")


@bp.route("/api/products", methods=["GET"])
def list_products():
    q = request.args.get("q", "").strip()
    sql, params = "SELECT * FROM products", []
    if q:
        sql += " WHERE name LIKE ? OR sku LIKE ? OR category LIKE ?"
        params = [f"%{q}%"] * 3
    sql += " ORDER BY id DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.route("/api/products/<int:pid>", methods=["GET"])
def get_product(pid):
    row = _fetch(get_db(), pid)
    if not row:
        return jsonify(error="Product not found"), 404
    return jsonify(dict(row))


@bp.route("/api/products", methods=["POST"])
def create_product():
    data, err = _validate(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO products (sku, name, category, quantity, price, reorder_level)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                data["sku"], data["name"], data.get("category") or "General",
                data.get("quantity", 0), data.get("price", 0.0),
                data.get("reorder_level", 5),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="SKU already exists"), 409
    return jsonify(dict(_fetch(db, cur.lastrowid))), 201


@bp.route("/api/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    data, err = _validate(request.get_json(silent=True) or {}, partial=True)
    if err:
        return jsonify(error=err), 400
    if not data:
        return jsonify(error="No fields to update"), 400
    db = get_db()
    if not _fetch(db, pid):
        return jsonify(error="Product not found"), 404
    assignments = ", ".join(f"{k} = ?" for k in data)  # keys come from a whitelist
    try:
        db.execute(
            f"UPDATE products SET {assignments} WHERE id = ?", (*data.values(), pid)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="SKU already exists"), 409
    return jsonify(dict(_fetch(db, pid)))


@bp.route("/api/products/<int:pid>/adjust", methods=["POST"])
def adjust_stock(pid):
    """Add or remove stock. Body: {"change": 10} or {"change": -3}."""
    body = request.get_json(silent=True) or {}
    try:
        change = int(body.get("change"))
    except (TypeError, ValueError):
        return jsonify(error="'change' must be an integer"), 400
    db = get_db()
    row = _fetch(db, pid)
    if not row:
        return jsonify(error="Product not found"), 404
    new_qty = row["quantity"] + change
    if new_qty < 0:
        return jsonify(error="Insufficient stock"), 400
    db.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, pid))
    db.commit()
    return jsonify(dict(_fetch(db, pid)))


@bp.route("/api/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    db = get_db()
    cur = db.execute("DELETE FROM products WHERE id = ?", (pid,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Product not found"), 404
    return "", 204


@bp.route("/api/stats", methods=["GET"])
def stats():
    row = get_db().execute(
        """
        SELECT COUNT(*) AS total_products,
               COALESCE(SUM(quantity), 0) AS total_units,
               COALESCE(SUM(quantity * price), 0) AS total_value,
               COALESCE(SUM(CASE WHEN quantity <= reorder_level THEN 1 ELSE 0 END), 0)
                   AS low_stock_count
        FROM products
        """
    ).fetchone()
    result = dict(row)
    result["total_value"] = round(result["total_value"], 2)
    return jsonify(result)


@bp.route("/api/low-stock", methods=["GET"])
def low_stock():
    rows = get_db().execute(
        "SELECT * FROM products WHERE quantity <= reorder_level ORDER BY quantity ASC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])
