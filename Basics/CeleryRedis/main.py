import json
from re import L
from turtle import title
from typing import Any, Literal
from data import todos
from fastapi import FastAPI
import httpx
from app.main import api_router
from redis_client import redis_client
from schemas import CreateTodo, Todo
from pydantic import  BaseModel
from app.celery_files.tasks import process_todo
app = FastAPI()



# ==============================================================================
@app.get("/todos/page")
async def get_todos(page:int = 1, limit : int = 10):
    # Check Redis first
    # cached_todos = await redis_client.get("todos")
    offset = (page -1 ) * limit
    print("offset -->", offset)
    return {
        "source":  "database", 
        "data": todos[offset: offset+ limit],
        "limit":limit,
        "page": page
    }
# =======================================================================================
@app.get("/")
def read_root():
    return {"message": "Hello"}

@app.get("/todos")#GetTodo
async def get_todos():
    # check redis first 
    cached_todos = await redis_client.get("todos")
    if cached_todos:
        return {
            "source": "redis",
            "data": json.loads(cached_todos)
        }
        
    await redis_client.set(
        "todos",  
        json.dumps(todos), 
        ex=60
    )
    
    return {
        "source" : "database", 
        "data":  todos
    }
    
@app.post("/todo") # response_model=list[Todo]
async def create_item(item: CreateTodo):
    new_item = {
        "id": len(todos) + 1,
        "title": item.title
    }
    
    todos.append(new_item)
    # clear redis cache
    await redis_client.delete("todos")
    return todos

# =============================================================================
    
@app.get("/users")
async def get_users():
    res = await httpx.AsyncClient().get("https://jsonplaceholder.typicode.com/todos")    
    return res.json()

class CreateUser(BaseModel):
    name: str
    user:str
    email:str

@app.post("/users")
async def create_user(user : CreateUser):
    res = await httpx.AsyncClient().post("https://jsonplaceholder.typicode.com/todos", 
            json=user.model_dump(),
            )
    
    print("res->", res.json())
    # await redis_client.delete("user-data")
    res.raise_for_status()
    
    return res.json()



# =========================Celery===================================
@app.get("/celery/todos")
async def get_todos():
    cached_todos = await redis_client.get("celery-todos")
    if cached_todos:
        return {
            "source": "redis",
            "data": json.loads(cached_todos)
        }
        
    await redis_client.set("celery-todos", json.dumps(todos), ex=60)
    return {
        "source": "database", 
        "data": todos
    }



@app.post("/celery/todos")
async def create_todo(item: CreateTodo):
    
    # Normally you would save the todo in DB here
    todo_id = 123

    # Send task to Celery
    task = process_todo.delay(todo_id)
    
    return {
        "status": "created",
        "task_id": task.id
    }
    
    