import datetime
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import pandas as pd
import os
import uvicorn
from db_config import *
from pydantic import BaseModel

app = FastAPI()

# Set up database and template folder
DATABASE_URL = "mysql+pymysql://{user}:{password}@{host}/{db}".format(
    user=db_user, password=db_password,
    host=db_host, db=db_name
)
engine = create_engine(DATABASE_URL)
EXCEL_FILE_PATH = "/path/to/store/excel_files"
os.makedirs(EXCEL_FILE_PATH, exist_ok=True)

templates = Jinja2Templates(directory="templates")

# Define Pydantic model for request validation
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# HTML UI Endpoint (Login Page)
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index_login.html", {"request": request})

# Login API Endpoint
# Login API Endpoint
@app.post("/login")
async def login_user(request: LoginRequest):
    try:
        # Query to check if the user exists by email
        query_check_user = "SELECT * FROM users WHERE email = :email"
        with engine.connect() as connection:
            # Check if user exists
            user = connection.execute(text(query_check_user), {"email": request.email}).fetchone()

            if not user:
                # User is not registered
                raise HTTPException(status_code=404, detail="User not registered. Please sign up.")

            # Check if the provided password matches
            if user[3] != request.password:
                # Password is incorrect
                raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")

            # If email and password match
            return {"message": "Login successful"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Register API Endpoint
@app.post("/register")
async def register_user(request: RegisterRequest):
    try:
        query_check = "SELECT * FROM users WHERE email = :email"
        query_insert = "INSERT INTO users (name, email, password) VALUES (:name, :email, :password)"
        with engine.connect() as connection:
            # Check if user already exists
            existing_user = connection.execute(text(query_check), {"email": request.email}).fetchone()
            if existing_user:
                raise HTTPException(status_code=400, detail="User already registered")

            # Insert new user into the database
            connection.execute(
                text(query_insert),
                {"name": request.name, "email": request.email, "password": request.password}
            )
            connection.commit()
            return {"message": "Registration successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Google OAuth Login Redirect
@app.get("/login-google")
async def login_google():
    return RedirectResponse("https://accounts.google.com/o/oauth2/auth")

# Run Uvicorn server programmatically
if __name__ == "__main__":
    uvicorn.run("main_login:app", host="172.28.151.62", port=8000, reload=True)
