from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO

from database.database import get_db, engine
from database.models import Base
from database.crud import get_order_history, save_order_results
from services.validator import validate_file, validate_cross_data_consistency, REQUIRED_FILES
from services.calculator import calculate_orders

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
    store: str | None = None,
    supplier: str | None = None,
    product_code: str | None = None,
    db: Session = Depends(get_db)
):
    orders = get_order_history(db, store=store, supplier=supplier, product_code=product_code)
    
    df = pd.DataFrame([{
        "store": o.store, 
        "supplier": o.supplier, 
        "product_code": o.product_code, 
        "order_qty": o.order_qty
    } for o in orders])

    if df.empty:
        top_suppliers, top_products, avg_order_qty = [], [], 0
    else:
        top_suppliers = list(df.groupby("supplier")["order_qty"].sum().sort_values(ascending=False).head(5).items())
        top_products = list(df.groupby("product_code")["order_qty"].sum().sort_values(ascending=False).head(5).items())
        avg_order_qty = round(float(df["order_qty"].mean()), 2)

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "top_suppliers": top_suppliers, "top_products": top_products,
        "avg_order_qty": avg_order_qty, "store": store, "supplier": supplier, "product_code": product_code
    })

@app.post("/generate-order/")
async def generate_order(
    current_stock_file: UploadFile = File(..., alias="current_stock"),
    sales_file: UploadFile = File(..., alias="sales"),
    onway_stock_file: UploadFile = File(..., alias="onway_stock"),
    minq_file: UploadFile = File(..., alias="MinQ"),
    calendar_file: UploadFile = File(..., alias="Calendar"),
    db: Session = Depends(get_db)
):
    file_inputs = {
        "current_stock": current_stock_file,
        "sales": sales_file,
        "onway_stock": onway_stock_file,
        "MinQ": minq_file,
        "Calendar": calendar_file
    }

    dataframes = {}
    
    try:
        for key, upload in file_inputs.items():
            filename_raw = upload.filename.rsplit(".", 1)[0].strip()
            if filename_raw != key:
                raise ValueError(
                    f"არასწორი ფაილი ველში! ველი მოითხოვს ფაილს სახელით '{key}.xlsx', "
                    f"მაგრამ თქვენ ატვირთეთ '{upload.filename}'."
                )

            try:
                df = pd.read_excel(upload.file)
            except Exception:
                raise ValueError(f"ფაილის '{upload.filename}' წაკითხვა ვერ მოხერხდა. დარწმუნდით, რომ Excel ფორმატი სწორია.")
            
            validate_file(df, key)
            dataframes[key] = df
            
        validate_cross_data_consistency(dataframes)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result_df = calculate_orders(dataframes)
    
    if result_df.empty:
        empty_info_df = pd.DataFrame([{"ინფორმაცია": "მიმდინარე კალენდარული დღისთვის შესაკვეთი გრაფიკები არ მოიძებნა"}])
        excel_stream = dataframe_to_excel_stream(empty_info_df)
        
        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=no_orders_today.xlsx"}
        )

    save_order_results(db, result_df)
    excel_stream = dataframe_to_excel_stream(result_df)

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=order_result.xlsx"}
    )
    
@app.get("/export-history/")
def export_history(db: Session = Depends(get_db)):
    orders = get_order_history(db)
    
    df = pd.DataFrame([{
        "ID": o.id, 
        "Order Date": o.order_creation_date.strftime("%Y-%m-%d %H:%M") if o.order_creation_date else None,
        "Delivery Date": o.delivery_date.strftime("%Y-%m-%d") if o.delivery_date else None,
        "Store": o.store, 
        "Supplier": o.supplier, 
        "Product": o.product_code, 
        "Current Qty": o.current_qty,
        "OnWay Qty": o.onway_qty,
        "Min Presentation Qty": o.min_qty,
        "ADS (Avg Sales)": round(o.avg_daily_sales, 2) if o.avg_daily_sales else 0,
        "Lead Time (Days)": o.lead_time,
        "Order Qty": o.order_qty
    } for o in orders])
    
    excel_stream = dataframe_to_excel_stream(df)
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=order_history.xlsx"}
    )