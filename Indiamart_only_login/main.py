import datetime
from fastapi import FastAPI, HTTPException, Request, Form,Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import pandas as pd
import os
import uvicorn
from db_config import *
from pydantic import BaseModel
import logging


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
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# HTML UI Endpoint (Login Page)
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Function to log to the log_table
def log_usage(ip: str, params: str, request_time: str, results_count: str, connection):
    query = """
        INSERT INTO log_table (ip, params, request_time, results_count)
        VALUES (:ip, :params, :request_time, :results_count)
    """
    connection.execute(text(query), {"ip": ip, "params": params, "request_time": request_time, "results_count": results_count})
    connection.commit()

# Login API Endpoint
@app.post("/login")
async def login_user(request: LoginRequest,response: Response,log_request:Request):
    try:
        # Query to check if the user exists by email
        query_check_user = "SELECT * FROM users WHERE email = :email"
        with engine.connect() as connection:
            # Check if user exists
            user = connection.execute(text(query_check_user), {"email": request.email}).fetchone()

            if not user:
                log_usage(log_request.client.host, f"email={request.email}",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "0", connection)
                # User is not registered
                raise HTTPException(status_code=404, detail="User not registered. Please sign up.")

            # Check if the provided password matches
            if user[2] != request.password:
                log_usage(log_request.client.host, f"email={request.email}",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "0", connection)
                # Password is incorrect
                raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")

            # Set a session cookie (for example, with a token)
            # expires = datetime.datetime.utcnow() + datetime.timedelta(days=1)
            expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
            response.set_cookie(key="user_session", value="logged_in", httponly=False,expires=expires)
            log_usage(log_request.client.host, f"email={request.email}",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "1", connection)
            # If email and password match
            return {"message": "Login successful"}

    except Exception as e:
        log_usage(log_request.client.host, f"email={request.email}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"0", connection)
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

# HTML UI Endpoint (Search Page)
@app.get("/search", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/search/data")
async def search_records(keyword: str, city: str,request: Request):
    try:
        # Log the incoming request with parameters
        ip_address = request.client.host  # Get the real client IP address
        params = {"keyword":f"{keyword}", "city":f"{city}"}  # The parameters passed in the search
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current timestamp
        query = f"SELECT * FROM `seller2` WHERE product_name LIKE '%{keyword}%' AND `company_basic_information_registered_address` LIKE '%{city}%'"
        with engine.connect() as connection:
            result = connection.execute(text(query))
            data = result.fetchall()

            # Count the number of results returned
            results_count = str(len(data))

            # Log the search action
            log_usage(ip_address, str(params), request_time, results_count, connection)

            if data:
                today_date = datetime.datetime.today().strftime("%d%m%Y")
                df = pd.DataFrame(data, columns=result.keys())
                file_path = os.path.join(EXCEL_FILE_PATH, f"{keyword}_{city}_{today_date}.xlsx")
                df.to_excel(file_path, index=False)

        if not data:
            raise HTTPException(status_code=404, detail="No records found")
        else:
            return {"download_link": f"/download/?file_name={keyword}_{city}_{today_date}.xlsx"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Download API Endpoint
@app.get("/download/")
async def download_file(file_name: str):
    file_path = os.path.join(EXCEL_FILE_PATH, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=file_name)


@app.get("/logout")
async def logout_user(response: Response):
    response.delete_cookie(key="user_session")
    return {"message": "Logged out successfully"}


# Run Uvicorn server programmatically
if __name__ == "__main__":
    uvicorn.run("main:app", host="172.28.151.62", port=8000, reload=True)
