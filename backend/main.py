from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from contextlib import contextmanager

app = FastAPI()

# CORS middleware to allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "notesdb"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres")
}

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

class Note(BaseModel):
    title: str
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

@app.on_event("startup")
async def startup():
    """Initialize database table on startup"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

@app.get("/")
async def root():
    return {"message": "Notes API is running"}

@app.get("/health")
async def health():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.get("/notes")
async def get_notes():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM notes ORDER BY created_at DESC")
                notes = cur.fetchall()
                return {"notes": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notes")
async def create_note(note: Note):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO notes (title, content) VALUES (%s, %s) RETURNING *",
                    (note.title, note.content)
                )
                new_note = cur.fetchone()
                conn.commit()
                return {"note": new_note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/{note_id}")
async def get_note(note_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM notes WHERE id = %s", (note_id,))
                note = cur.fetchone()
                if not note:
                    raise HTTPException(status_code=404, detail="Note not found")
                return {"note": note}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/notes/{note_id}")
async def update_note(note_id: int, note: NoteUpdate):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build dynamic update query
                update_fields = []
                values = []
                if note.title is not None:
                    update_fields.append("title = %s")
                    values.append(note.title)
                if note.content is not None:
                    update_fields.append("content = %s")
                    values.append(note.content)

                if not update_fields:
                    raise HTTPException(status_code=400, detail="No fields to update")

                values.append(note_id)
                query = f"UPDATE notes SET {', '.join(update_fields)} WHERE id = %s RETURNING *"
                cur.execute(query, values)
                updated_note = cur.fetchone()

                if not updated_note:
                    raise HTTPException(status_code=404, detail="Note not found")

                conn.commit()
                return {"note": updated_note}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM notes WHERE id = %s RETURNING id", (note_id,))
                deleted = cur.fetchone()
                if not deleted:
                    raise HTTPException(status_code=404, detail="Note not found")
                conn.commit()
                return {"message": "Note deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
