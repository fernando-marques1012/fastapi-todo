from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Optional, List

SQLALCHEMY_DATABASE_URL = "sqlite:///./todo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    completed = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=120)
    description: Optional[str] = None
    completed: bool = False

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    completed: Optional[bool] = None

class TaskOut(TaskCreate):
    id: int
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="ToDo App [FastAPI]", description="Projeto demonstrativo", version="1.0.0")

@app.get("/api/tasks", response_model=List[TaskOut], tags=["Tasks"])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(TaskDB).offset(skip).limit(limit).all()

@app.post("/api/tasks", response_model=TaskOut, status_code=201, tags=["Tasks"])
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = TaskDB(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/api/tasks/{task_id}", response_model=TaskOut, tags=["Tasks"])
def read_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return db_task

@app.put("/api/tasks/{task_id}", response_model=TaskOut, tags=["Tasks"])
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    update_data = task.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/api/tasks/{task_id}", tags=["Tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    db.delete(db_task)
    db.commit()
    return {"message": "Tarefa removida"}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root():
    return """
    <!DOCTYPE html><html><head><title>ToDo App</title><style>body{font-family:Arial;max-width:600px;margin:40px auto;} .input-group{display:flex;gap:10px;} input[type="text"]{flex:1;padding:10px;} button{padding:10px;background:#007bff;color:white;border:none;} ul{list-style:none;padding:0;} li{padding:10px;border-bottom:1px solid #ccc;display:flex;gap:10px;} .completed{text-decoration:line-through;color:gray;}</style></head><body><h1>📋 ToDo App</h1><div class="input-group"><input type="text" id="taskInput" placeholder="Estudar FastAPI..."><button onclick="addTask()">Adicionar</button></div><ul id="taskList"></ul><script>async function fetchTasks(){const r=await fetch('/api/tasks');const t=await r.json();const l=document.getElementById('taskList');l.innerHTML='';t.forEach(x=>{const i=document.createElement('li');i.innerHTML=`<input type="checkbox" ${x.completed?'checked':''} onchange="toggleTask(${x.id},${!x.completed})"><span class="${x.completed?'completed':''}">${x.title}</span><button onclick="deleteTask(${x.id})" style="margin-left:auto;background:#dc3545;">X</button>`;l.appendChild(i);});}async function addTask(){const i=document.getElementById('taskInput');if(!i.value)return;await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:i.value})});i.value='';fetchTasks();}async function toggleTask(id,c){await fetch(`/api/tasks/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({completed:c})});fetchTasks();}async function deleteTask(id){await fetch(`/api/tasks/${id}`,{method:'DELETE'});fetchTasks();}fetchTasks();</script></body></html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
