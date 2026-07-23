from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

items = list()

class Item(BaseModel):
    item: str = Field(..., min_length=3, max_length=30)
    

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.post("/item")
def create_item(item):
    items.append(item)
    return {"message": "Item created successfully", "items":items}

# @app.patch()