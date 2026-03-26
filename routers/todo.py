import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import markdown
from bs4 import BeautifulSoup
from typing import Annotated
from pydantic import Field
from fastapi import APIRouter, Body, Path, Query, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel
from starlette import status
from sqlalchemy.orm import Session
from models import Todo, User
from database import engine, SessionLocal
from routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage   

router = APIRouter(prefix="/todo", tags=["todos"])

templates = Jinja2Templates(directory="templates")

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


def redirect_to_login():
    return RedirectResponse(url="/auth/login-page", status_code=status.HTTP_302_FOUND)

@router.get("/todo-page")
def render_todo_page(request: Request, db: db_dependency):
    try:
        user = get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()    
        todos = db.query(Todo).filter(Todo.owner_id == user.get("id")).all()    
        return templates.TemplateResponse("todo.html", {"request": request, "todos": todos})
    except Exception as e:
        return redirect_to_login()


@router.get("/add-todo-page")
def render_add_todo_page(request: Request):
    try:
        user = get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()    
        return templates.TemplateResponse("add-todo.html", {"request": request})
    except Exception as e:
        return redirect_to_login()

@router.get("/edit-todo-page/{todo_id}")
def render_edit_todo_page(request: Request, db: db_dependency, todo_id: int = Path(gt=0)):
    try:
        user = get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()    
        todo = db.query(Todo).filter(Todo.id == todo_id).first()    
        if todo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
        return templates.TemplateResponse("edit-todo.html", {"request": request, "todo": todo})
    except Exception as e:
        return redirect_to_login()


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


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, todo_request: TodoRequest, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    todo = Todo(**todo_request.dict(), owner_id=user.get("id"))
    todo.description = markdown_to_text(create_todo_with_gemini(todo.description))
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
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

@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(db: db_dependency, todo_id: int = Path(gt=0)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    db.query(Todo).filter(Todo.id == todo_id).delete()
    db.commit()
    return {"message": "Todo deleted successfully"}




def create_todo_with_gemini(todo_string: str):
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest")
    response = llm.invoke([
        HumanMessage(content="You are a todo list manager. what i want you to do is to create a longer and more comprehensive description of that todo item, my next message will be my todo:."),
        HumanMessage(content=todo_string)
    ])
    return response.content
    
def markdown_to_text(markdown_string: str):
        html = markdown.markdown(markdown_string)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()
        return text
        


if __name__ == "__main__":
    print(markdown_to_text(create_todo_with_gemini("buy milk")))    