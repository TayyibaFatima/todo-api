import os
import psycopg2
import psycopg2.extras
from typing import Optional
from repository import TaskRepository

DATABASE_URL = os.getenv("DATABASE_URL")


class PostgresTaskRepository(TaskRepository):
    def __init__(self):
        self.conn_str = DATABASE_URL

    def _connect(self):
        return psycopg2.connect(self.conn_str, cursor_factory=psycopg2.extras.RealDictCursor)

    def _row_to_task(self, row):
        return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

    def get_all(self, done: Optional[bool] = None, search: Optional[str] = None) -> list[dict]:
        conn = self._connect()
        cur = conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if done is not None:
            query += " AND done = %s"
            params.append(done)

        if search:
            query += " AND title ILIKE %s"
            params.append(f"%{search}%")

        query += " ORDER BY id"
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return [self._row_to_task(r) for r in rows]

    def get(self, task_id: int) -> Optional[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
        conn.close()
        return self._row_to_task(row) if row else None

    def create(self, title: str) -> dict:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
            (title, False),
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return self._row_to_task(row)

    def update(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[dict]:
        existing = self.get(task_id)
        if existing is None:
            return None

        new_title = title if title is not None else existing["title"]
        new_done = done if done is not None else existing["done"]

        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
            (new_title, new_done, task_id),
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return self._row_to_task(row)

    def delete(self, task_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        if cur.fetchone() is None:
            conn.close()
            return False
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        conn.close()
        return True

    def stats(self) -> dict:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM tasks")
        total = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS done_count FROM tasks WHERE done = true")
        done_count = cur.fetchone()["done_count"]
        conn.close()
        return {"total": total, "done": done_count, "open": total - done_count}