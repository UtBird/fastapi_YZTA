from typing import Annotated
from pydantic import Field
from fastapi import APIRouter, Body, Path, Query, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from starlette import status
from sqlalchemy.orm import Session
import models
from models import Todo, User
from database import engine, SessionLocal
from routers.auth import get_current_user

router = APIRouter(prefix="/todos", tags=["todos"])

class TodoRequest(BaseModel):
    title: str = Field (min_length=3)
    description: str = Field (min_length=3, max_length=1000)
    priority: int = Field (gt=0, lt=6)
    complete: bool = Field (default=False)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/", status_code=status.HTTP_200_OK)
async def read_user(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return db.query(Todo).all()


@router.get("/todos", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    return db.query(Todo).filter(Todo.owner_id == user.get("id")).all()

@router.get("/get_by_id/{todo_id}", status_code=status.HTTP_201_CREATED)
async def read_by_id(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return todo


@router.post("/create_todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, todo_request: TodoRequest, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    todo = Todo(**todo_request.dict(), owner_id=user)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.put("/update_todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo( db: db_dependency, todo_request: TodoRequest, todo_id: int = Path(gt=0)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    todo.title = todo_request.title
    todo.description = todo_request.description
    todo.priority = todo_request.priority
    todo.complete = todo_request.complete
    db.commit()
    db.refresh(todo)
    return todo

@router.delete("/delete_todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(db: db_dependency, todo_id: int = Path(gt=0)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    db.query(Todo).filter(Todo.id == todo_id).delete()
    db.commit()
    return {"message": "Todo deleted successfully"}