from typing import Annotated
from pydantic import Field
from fastapi import FastAPI, Body, Path, Query, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from starlette import status
from sqlalchemy.orm import Session
import models
from models import Todo
from database import engine, SessionLocal
from routers.auth import router as auth_router
from routers.todo import router as todo_router


app = FastAPI()

app.include_router(auth_router)
app.include_router(todo_router)

models.Base.metadata.create_all(bind=engine)
