# -*- coding: utf-8 -*-
import os, sqlite3, threading
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable, Optional

class DatabaseManager:
    def __init__(self, path: Optional[str] = None):
        default_path = os.path.join(os.path.dirname(__file__), "shop_bot.db")
        self.path = path or os.getenv("DB_PATH", default_path)
        Path(os.path.dirname(self.path) or ".").mkdir(parents=True, exist_ok=True)
        Path(self.path).touch(exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA synchronous = NORMAL;")
        self._conn.commit()
        self._bootstrap_schema()

    def execute_query(self, sql: str, params: Optional[Iterable[Any]] = None):
        params = tuple(params) if params is not None else tuple()
        is_read = sql.lstrip().split(None, 1)[0].upper() in {"SELECT", "PRAGMA", "WITH"}
        with self._lock, closing(self._conn.cursor()) as cur:
            cur.execute(sql, params)
            if is_read:
                return cur.fetchall()
            self._conn.commit()
            return cur.rowcount

    def _cols(self, table: str):
        with closing(self._conn.cursor()) as cur:
            cur.execute(f"PRAGMA table_info({table})")
            return {r[1] for r in cur.fetchall()}

    def _add_col(self, table: str, name: str, ddl: str):
        if name in self._cols(table): return
        with closing(self._conn.cursor()) as cur:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        self._conn.commit()

    def _bootstrap_schema(self):
        with closing(self._conn.cursor()) as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, username TEXT, email TEXT, password_hash TEXT,
                is_admin INTEGER DEFAULT 0 NOT NULL,
                role TEXT,
                chat_id TEXT, phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT, emoji TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER, subcategory_id INTEGER,
                title TEXT, name TEXT, description TEXT,
                price REAL, cost_price REAL DEFAULT 0,
                stock INTEGER DEFAULT 0, sales_count INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                image_url TEXT, is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, status TEXT, payment_method TEXT,
                total_amount REAL DEFAULT 0,
                delivery_address TEXT, delivery_phone TEXT,
                latitude REAL, longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER, product_id INTEGER,
                qty INTEGER DEFAULT 1, quantity INTEGER DEFAULT 1,
                price REAL DEFAULT 0
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT, title TEXT, content TEXT,
                scheduled_at TIMESTAMP, status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS post_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER, views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0, forwards INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        self._conn.commit()
        for t, cols in {{
            "categories": [("description","TEXT"),("emoji","TEXT"),("is_active","INTEGER DEFAULT 1")],
            "products": [("subcategory_id","INTEGER"),("name","TEXT"),("image_url","TEXT"),
                         ("is_active","INTEGER DEFAULT 1"),("cost_price","REAL DEFAULT 0"),
                         ("stock","INTEGER DEFAULT 0"),("sales_count","INTEGER DEFAULT 0"),("views","INTEGER DEFAULT 0")],
            "orders": [("payment_method","TEXT"),("delivery_phone","TEXT"),("latitude","REAL"),("longitude","REAL")],
            "order_items": [("qty","INTEGER DEFAULT 1"),("quantity","INTEGER DEFAULT 1")],
            "scheduled_posts": [("title","TEXT")],
        }}.items():
            for col, ddl in cols:
                try: self._add_col(t, col, ddl)
                except Exception: pass
        with closing(self._conn.cursor()) as cur:
            cur.execute("UPDATE products SET name = COALESCE(NULLIF(name,''), title)")
            cur.execute("""UPDATE products SET sales_count = COALESCE((
                SELECT SUM(COALESCE(oi.quantity, oi.qty, 0))
                FROM order_items oi JOIN orders o ON o.id = oi.order_id
                WHERE oi.product_id = products.id AND (o.status IS NULL OR o.status != 'cancelled')
            ), 0)""")
            cur.execute("UPDATE products SET views = COALESCE(views, 0)")
            cur.execute("UPDATE order_items SET quantity = COALESCE(NULLIF(quantity,0), qty)")
            cur.execute("UPDATE order_items SET qty = COALESCE(NULLIF(qty,0), quantity)")
            cur.execute("UPDATE scheduled_posts SET title = COALESCE(title, '')")
        self._conn.commit()