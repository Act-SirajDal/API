import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import pandas as pd
import os
import uvicorn
from db_config import *

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

# HTML UI Endpoint
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Search API Endpoint
@app.get("/search/")
async def search_records(keyword: str, city: str):
    try:
        query = f"SELECT * FROM `seller2` WHERE product_name LIKE '%{keyword}%' AND `company_basic_information_registered_address` LIKE '%{city}%'"
        with engine.connect() as connection:
            result = connection.execute(text(query))
            data = result.fetchall()
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


# Run Uvicorn server programmatically
if __name__ == "__main__":
    uvicorn.run("main:app", host="172.28.151.62", port=8000, reload=True)
