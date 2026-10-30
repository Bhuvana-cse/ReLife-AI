import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DB_PATH = os.getenv("RELIFE_DB_PATH", str(Path(__file__).resolve().parents[1] / "relife.db"))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                student_id TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                product_name TEXT NOT NULL DEFAULT '',
                age_years REAL NOT NULL,
                useful_life_years REAL NOT NULL DEFAULT 2,
                condition TEXT NOT NULL,
                visible_damage TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                recommendation TEXT NOT NULL,
                explanation TEXT NOT NULL,
                repair_cost REAL NOT NULL,
                resale_value REAL NOT NULL,
                image_name TEXT,
                inference_mode TEXT NOT NULL DEFAULT 'rule-based demo',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS passports (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                public_id TEXT NOT NULL UNIQUE,
                events TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS recipient_requests (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                min_condition TEXT NOT NULL,
                location TEXT NOT NULL,
                requirement TEXT NOT NULL,
                demo INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS match_decisions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                request_id INTEGER NOT NULL REFERENCES recipient_requests(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'pending',
                UNIQUE(user_id, product_id, request_id)
            );
            CREATE TABLE IF NOT EXISTS recovery_centers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                categories TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                demo INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS component_assessments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                components TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS scenario_comparisons (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                assumptions TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS recovery_plans (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS plan_steps (
                id INTEGER PRIMARY KEY,
                plan_id INTEGER NOT NULL REFERENCES recovery_plans(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                provider_id INTEGER REFERENCES recovery_centers(id)
            );
            CREATE TABLE IF NOT EXISTS product_updates (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                update_type TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
        if "student_id" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN student_id TEXT")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_student_id_unique ON users(student_id)")
        product_columns = {row["name"] for row in db.execute("PRAGMA table_info(products)")}
        if "location" not in product_columns:
            db.execute("ALTER TABLE products ADD COLUMN location TEXT NOT NULL DEFAULT ''")
        if "product_name" not in product_columns:
            db.execute("ALTER TABLE products ADD COLUMN product_name TEXT NOT NULL DEFAULT ''")
        if "useful_life_years" not in product_columns:
            db.execute("ALTER TABLE products ADD COLUMN useful_life_years REAL NOT NULL DEFAULT 2")
        if db.execute("SELECT COUNT(*) FROM recipient_requests").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO recipient_requests(name, category, min_condition, location, requirement) VALUES (?, ?, ?, ?, ?)",
                [
                    ("Campus Repair & Reuse Club (sample)", "electronics", "fair", "Campus", "Working or repairable devices for student projects"),
                    ("Community Home Starter Kit (sample)", "furniture", "good", "North district", "Clean tables and chairs for households"),
                    ("Circular Closet Pop-up (sample)", "clothing", "fair", "Campus", "Wearable clothing in fair condition or better"),
                    ("Neighborhood Tool Library (sample)", "household", "good", "Central district", "Safe, functional household tools and appliances"),
                ],
            )
        if db.execute("SELECT COUNT(*) FROM recovery_centers").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO recovery_centers(name, kind, categories, location, description) VALUES (?, ?, ?, ?, ?)",
                [
                    ("Student Fix Lab (sample)", "repair", "electronics,furniture,household", "Campus", "Sample listing; availability and contact details are not verified."),
                    ("Community Reuse Shelf (sample)", "reuse", "furniture,clothing,household", "North district", "Sample listing; confirm acceptance before visiting."),
                    ("Local Giving Hub (sample)", "donation", "electronics,furniture,clothing,household", "Central district", "Sample listing; donation criteria are not verified."),
                    ("Materials Recovery Point (sample)", "recycling", "electronics,furniture,clothing,household", "West district", "Sample listing; check local rules for accepted materials."),
                ],
            )
