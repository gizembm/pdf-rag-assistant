import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DATABASE_PATH = Path("chat_history.db")


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def get_current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS document_sets (
                fingerprint TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_fingerprint TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY (document_fingerprint)
                    REFERENCES document_sets(fingerprint)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                document_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,

                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.commit()


def document_set_exists(document_fingerprint):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT fingerprint
            FROM document_sets
            WHERE fingerprint = ?
            """,
            (document_fingerprint,)
        ).fetchone()

    return row is not None


def create_document_set(document_fingerprint):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO document_sets (
                fingerprint,
                created_at
            )
            VALUES (?, ?)
            """,
            (
                document_fingerprint,
                get_current_timestamp()
            )
        )

        connection.commit()


def get_document_sets():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                ds.fingerprint,
                ds.created_at,
                COUNT(d.id) AS document_count
            FROM document_sets AS ds
            LEFT JOIN documents AS d
                ON d.document_fingerprint = ds.fingerprint
            GROUP BY
                ds.fingerprint,
                ds.created_at
            ORDER BY ds.created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def delete_document_set(document_fingerprint):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM conversations
            WHERE document_fingerprint = ?
            """,
            (document_fingerprint,)
        )

        connection.execute(
            """
            DELETE FROM document_sets
            WHERE fingerprint = ?
            """,
            (document_fingerprint,)
        )

        connection.commit()


def add_document(document_fingerprint, file_name, file_path):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO documents (
                document_fingerprint,
                file_name,
                file_path,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                document_fingerprint,
                file_name,
                file_path,
                get_current_timestamp()
            )
        )

        connection.commit()


def get_documents(document_fingerprint):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                file_name,
                file_path,
                created_at
            FROM documents
            WHERE document_fingerprint = ?
            ORDER BY id ASC
            """,
            (document_fingerprint,)
        ).fetchall()

    return [dict(row) for row in rows]


def create_conversation(conversation_id, title, document_fingerprint):
    timestamp = get_current_timestamp()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO conversations (
                id,
                title,
                document_fingerprint,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                title,
                document_fingerprint,
                timestamp,
                timestamp
            )
        )

        connection.commit()


def update_conversation_title(conversation_id, title):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE conversations
            SET
                title = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                get_current_timestamp(),
                conversation_id
            )
        )

        connection.commit()


def get_conversations(document_fingerprint):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE document_fingerprint = ?
            ORDER BY updated_at DESC
            """,
            (document_fingerprint,)
        ).fetchall()

    return [dict(row) for row in rows]


def delete_conversation(conversation_id):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        )

        connection.commit()


def delete_conversations_for_documents(document_fingerprint):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM conversations
            WHERE document_fingerprint = ?
            """,
            (document_fingerprint,)
        )

        connection.commit()


def add_message(conversation_id, role, content, sources=None):
    if sources is None:
        sources = []

    timestamp = get_current_timestamp()
    sources_json = json.dumps(sources, ensure_ascii=False)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                sources,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                sources_json,
                timestamp
            )
        )

        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                timestamp,
                conversation_id
            )
        )

        connection.commit()


def get_messages(conversation_id):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                role,
                content,
                sources,
                created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,)
        ).fetchall()

    messages = []

    for row in rows:
        messages.append({
            "role": row["role"],
            "content": row["content"],
            "sources": json.loads(row["sources"]),
            "created_at": row["created_at"]
        })

    return messages
