from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from postgres_repository import PostgresTaskRepository

app = FastAPI()
repo = PostgresTaskRepository()


class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/", summary="API info")
def root():
    return {"name": "Task API", "version": "3.0 (Postgres)", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks (supports filtering & search)")
def get_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    return repo.get_all(done=done, search=search)


@app.get("/tasks/{task_id}", summary="Get a single task")
def get_task(task_id: int):
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    return repo.create(task.title)


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, update: TaskUpdate):
    if update.title is not None and not update.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    updated = repo.update(task_id, update.title, update.done)
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    deleted = repo.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return


@app.get("/stats", summary="Task statistics")
def stats():
    return repo.stats()