from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pandas as pd

from database.database import get_db, engine
from database.models import Base
from database.crud import get_order_history
from services.validator import validate_file
from services.calculator import calculate_orders

app = FastAPI(title="Retail Order Automation System")
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)


@app.get("/ui/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/ui/history", response_class=HTMLResponse)
def history_page(request: Request, db: Session = Depends(get_db)):
    orders = get_order_history(db)
    return templates.TemplateResponse("history.html", {"request": request, "orders": orders})


@app.get("/ui/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.post("/generate-order/")
async def generate_order(files: list[UploadFile] = File(...)):
    if len(files) != 5:
        raise HTTPException(status_code=400, detail="Exactly 5 Excel files must be uploaded")

    file_map = {f.filename.rsplit(".", 1)[0].strip(): f for f in files}
    required_files = {"current_stock", "sales", "onway_stock", "MinQ", "Calendar"}

    if set(file_map.keys()) != required_files:
        raise HTTPException(
            status_code=400,
            detail="Files must be named exactly: current_stock, sales, onway_stock, MinQ, Calendar"
        )

    dataframes = {}

    for key, upload in file_map.items():
        try:
            df = pd.read_excel(upload.file)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Cannot read {key} Excel file")

        validate_file(df, key)
        dataframes[key] = df

    return {
        "message": "Files uploaded and validated successfully",
        "uploaded_files": list(dataframes.keys())

    }
    
    result_df = calculate_orders(dataframes)

    return {
    "message": "Order calculation completed",
    "rows": len(result_df)
    }