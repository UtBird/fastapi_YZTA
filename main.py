from typing import Annotated
from pydantic import Field
from fastapi import FastAPI, Body, Path, Query, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel
from starlette import status
from sqlalchemy.orm import Session
import models
from models import Todo
from database import engine, SessionLocal
from routers.auth import router as auth_router
from routers.todo import router as todo_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette import status
import os

script_dir = os.path.dirname(os.path.abspath(__file__)) 
static_abs_path = os.path.join(script_dir, "static")


app = FastAPI()

app.mount("/static", StaticFiles(directory=static_abs_path), name="static")

@app.get("/")
def read_root(request: Request):
    return RedirectResponse(url="/todo/todo-page", status_code=status.HTTP_302_FOUND)

app.include_router(auth_router)
app.include_router(todo_router)

models.Base.metadata.create_all(bind=engine)
