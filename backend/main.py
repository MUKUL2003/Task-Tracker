from fastapi import FastAPI , HTTPException
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI()

def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT","5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )

class Task(BaseModel):
    title : str
    done : bool = False

@app.on_event("startup")
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS tasks (
      id SERIAL PRIMARY KEY,
      title TEXT NOT NULL,
      done BOOLEAN DEFAULT FALSE
      )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
def health():
    return {"status" : "ok"}

@app.get("/tasks")
def list_tasks():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id , title , done FROM tasks ORDER BY id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"id" : r[0] , "title":r[1] , "done":r[2]}for r in rows]

@app.post("/tasks")
def create_task(task: Task):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks(title , done) VALUES (%s , %s) RETURNING id", (task.title , task.done))
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return {"id": new_id, **task.dict()}

@app.put("/tasks/{task_id}")
def update_task(task_id:int , task:Task):
    conn= get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET title=%s , done=%s WHERE id=%s" , (task.title , task.done , task_id))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404 , detail="Task Not found")
    conn.commit(); cur.close(); conn.close()
    return {"id":task_id , **task.dict()}

@app.delete("/tasks/{task_id}")
def delete_task(task_id:int):
    conn=get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s",(task_id,))
    conn.commit(); cur.close(); conn.close()
    return {"deleted":task_id }
    
