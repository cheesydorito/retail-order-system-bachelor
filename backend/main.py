from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pandas as pd

from database.database import get_db, engine
from database.models import Base
from database.crud import get_order_history
from database.crud import save_order_results
from services.validator import validate_file
from services.calculator import calculate_orders
from io import BytesIO


app = FastAPI(title="Retail Order Automation System")
templates = Jinja2Templates(directory="templates")

def dataframe_to_excel_stream(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="OrderResults")

    output.seek(0)
    return output

Base.metadata.create_all(bind=engine)


@app.get("/ui/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/ui/history", response_class=HTMLResponse)
def history_page(request: Request, db: Session = Depends(get_db)):
    orders = get_order_history(db)
    return templates.TemplateResponse("history.html", {"request": request, "orders": orders})

@app.get("/ui/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    orders = get_order_history(db)

    df = pd.DataFrame([{
        "supplier": o.supplier,
        "product_code": o.product_code,
        "order_qty": o.order_qty
    } for o in orders])

    if df.empty:
        top_suppliers = []
        top_products = []
        avg_order_qty = 0
    else:
        top_suppliers = list(
            df.groupby("supplier")["order_qty"].sum().sort_values(ascending=False).head(5).items()
        )

        top_products = list(
            df.groupby("product_code")["order_qty"].sum().sort_values(ascending=False).head(5).items()
        )

        avg_order_qty = round(float(df["order_qty"].mean()), 2)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "top_suppliers": top_suppliers,
            "top_products": top_products,
            "avg_order_qty": avg_order_qty
        }
    )

@app.post("/generate-order/")
async def generate_order(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):

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

    result_df = calculate_orders(dataframes)

    save_order_results(db, result_df)

    excel_stream = dataframe_to_excel_stream(result_df)

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=order_result.xlsx"
        }
    )