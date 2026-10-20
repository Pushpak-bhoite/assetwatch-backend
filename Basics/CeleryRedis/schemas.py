from typing import Any, Literal

from pydantic import BaseModel, Field

class Todo(BaseModel):
    id: int
    title: str   = Field(min_length=2)
    
class CreateTodo(BaseModel):
    title: str

class GetTodo(BaseModel):
    source: Literal["redis", "database"]
    data: Any #list[Todo]
    
    
    