import os
import psycopg
from psycopg.rows import dict_row


def get_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL не знайдено")
    return psycopg.connect(url, row_factory=dict_row)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id SERIAL PRIMARY KEY,
                    telegram_chat_id BIGINT NOT NULL,
                    raw_text TEXT NOT NULL,
                    sender_name TEXT,
                    sender_email TEXT,
                    category TEXT,
                    priority TEXT,
                    status TEXT DEFAULT 'new',
                    summary TEXT,
                    extracted_data TEXT,
                    draft_subject TEXT,
                    draft_body TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()


def save_email(chat_id: int, raw_text: str, analysis: dict):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO emails (
                    telegram_chat_id, raw_text, sender_name, sender_email,
                    category, priority, status, summary, extracted_data,
                    draft_subject, draft_body
                )
                VALUES (%s,%s,%s,%s,%s,%s,'triaged',%s,%s,%s,%s)
                RETURNING id;
            """, (
                chat_id,
                raw_text,
                analysis.get("sender_name"),
                analysis.get("sender_email"),
                analysis.get("category"),
                analysis.get("priority"),
                analysis.get("summary"),
                analysis.get("extracted_data"),
                analysis.get("draft_subject"),
                analysis.get("draft_body"),
            ))
            row = cur.fetchone()
            conn.commit()
            return row["id"]


def get_email(email_id: int, chat_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM emails WHERE id=%s AND telegram_chat_id=%s;", (email_id, chat_id))
            return cur.fetchone()


def list_emails(chat_id: int, limit: int = 20):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM emails WHERE telegram_chat_id=%s ORDER BY id DESC LIMIT %s;", (chat_id, limit))
            return cur.fetchall()


def update_status(email_id: int, chat_id: int, status: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE emails SET status=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND telegram_chat_id=%s RETURNING id;
            """, (status, email_id, chat_id))
            row = cur.fetchone()
            conn.commit()
            return row is not None


def report(chat_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT category, COUNT(*) AS count FROM emails WHERE telegram_chat_id=%s GROUP BY category ORDER BY category;", (chat_id,))
            by_category = cur.fetchall()
            cur.execute("SELECT priority, COUNT(*) AS count FROM emails WHERE telegram_chat_id=%s GROUP BY priority ORDER BY priority;", (chat_id,))
            by_priority = cur.fetchall()
            return {"by_category": by_category, "by_priority": by_priority}


def clear_all(chat_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM emails WHERE telegram_chat_id=%s;", (chat_id,))
            conn.commit()
