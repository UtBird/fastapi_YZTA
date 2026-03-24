from typing import Annotated
from database import SessionLocal
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from models import User
from sqlalchemy.orm import Session
from starlette import status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/auth", tags=["auth"])

templates = Jinja2Templates(directory="templates")

SECRET_KEY = "h3t35dihyldh7gep7hgno7kx4aowx0tajp2b6cu45z6uv9arqomsq5qd48j23y1v"
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3)
    email: str = Field(min_length=3)
    password: str = Field(min_length=3)
    first_name: str = Field(min_length=3)
    last_name: str = Field(min_length=3)
    role: str = Field(min_length=3)

class Token(BaseModel):
    access_token: str
    token_type: str


def authenticate_user(username: str, password: str, db: db_dependency):
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not bcrypt_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    return user

def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"id": user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")



@router.get("/login-page")
def render_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register-page")
def render_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user_request: CreateUserRequest, db: db_dependency):
    user = User(
        username=user_request.username,
        email=user_request.email,
        hashed_password=bcrypt_context.hash(user_request.password),
        first_name=user_request.first_name,
        last_name=user_request.last_name,
        role=user_request.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/token", status_code=status.HTTP_200_OK)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)    
    return {"access_token": token, "token_type": "bearer"}