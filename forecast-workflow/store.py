import sqlite3
from pathlib import Path

from engine import SkuMaster, cases_per_hour

_COVER_KEY = "cover_n"

_SEED_ROWS: list[tuple[str, str, object, str]] = [
    ("MDP750VEND-129", "GALAXY VENDPCH 10X750G", 156, "forecast"),
    ("MDP750TT-129", "GALAXY T/TOP 10X750G", 156, "forecast"),
    ("CHOC450", "MBK CHOC NRSPO 10X450G", 112, "forecast"),
    ("STRAW450-032", "MOOSEBRK STRAW 10X450G SG", 112, "forecast"),
    ("CNVIGN-121", "CNUEVA DOLCE 10X300G", 182, "forecast"),
    ("CNDELZ-121", "CAFE NUEVA DELIZIA COFFEE 10X300G", 182, "forecast"),
    ("SUPSKIM-123", "MILFRESH GOLD 10X500G", 0, "forecast"),
    ("SCGM500-123", "MILFRESH SCUPS 10X500G", None, "forecast"),
    ("GRANMB-123", "MILFRESH SILVR 10X500G", None, "forecast"),
    ("GRANMBLAV-123", "MILFRESH SILVER LAVAZZA 10X500G", None, "forecast"),
    ("B302ZDHC1-383", "ZUMA DARK HOT CHOC 8X1KG BAGS", None, "forecast"),
    ("B304ZOHC1-383", "ZUMA ORIGINAL HOT CHOC 8X1KG BAGS", None, "forecast"),
]


def _connect(path: Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path) -> None:
    with _connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sku (
                part TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                cases_per_hour REAL,
                demand_driver TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )


def seed_if_empty(path: Path) -> None:
    with _connect(path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM sku").fetchone()[0]
        if count > 0:
            return
        for part, description, cph_raw, demand_driver in _SEED_ROWS:
            cph = cases_per_hour(cph_raw)
            conn.execute(
                """
                INSERT INTO sku (part, description, cases_per_hour, demand_driver)
                VALUES (?, ?, ?, ?)
                """,
                (part, description, cph, demand_driver),
            )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (_COVER_KEY, "8"),
        )


def list_skus(path) -> list[SkuMaster]:
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT part, description, cases_per_hour, demand_driver FROM sku ORDER BY part"
        ).fetchall()
    return [_row_to_sku(row) for row in rows]


def upsert_sku(path, sku: SkuMaster) -> None:
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO sku (part, description, cases_per_hour, demand_driver)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(part) DO UPDATE SET
                description = excluded.description,
                cases_per_hour = excluded.cases_per_hour,
                demand_driver = excluded.demand_driver
            """,
            (sku.part, sku.description, sku.cases_per_hour, sku.demand_driver),
        )


def delete_sku(path, part: str) -> None:
    with _connect(path) as conn:
        conn.execute("DELETE FROM sku WHERE part = ?", (part,))


def get_cover_n(path) -> int:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (_COVER_KEY,)
        ).fetchone()
    if row is None:
        return 8
    return int(row["value"])


def set_cover_n(path, n: int) -> None:
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_COVER_KEY, str(n)),
        )


def _row_to_sku(row: sqlite3.Row) -> SkuMaster:
    cph = row["cases_per_hour"]
    if cph is not None:
        cph = float(cph)
    return SkuMaster(row["part"], row["description"], cph, row["demand_driver"])