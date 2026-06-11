from datetime import datetime, timedelta
import pandas as pd

def calculate_orders(dataframes: dict) -> pd.DataFrame:
    for df_name, df_obj in dataframes.items():
        if df_obj is not None:
            #სვეტების სახელების გასუფთავება
            df_obj.columns = df_obj.columns.str.strip()
            
            #ვასუფთავებ ტექსტურ მნიშვნელობებს ძირითად სვეტებში, რათა merge სწორად გაკეთდეს
            for col in ["store", "supplier", "product_code"]:
                if col in df_obj.columns:
                    df_obj[col] = df_obj[col].astype(str).str.strip()

    sales = dataframes["sales"]
    current_stock = dataframes["current_stock"]
    onway = dataframes["onway_stock"]
    minq = dataframes["MinQ"]
    calendar = dataframes["Calendar"]

    #მიმდინარე კვირის დღის განსაზღვრა (1 = ორშაბათი, 7 = კვირა)
    today_dt = datetime.now()
    today_weekday = today_dt.isoweekday() 

    #კალენდრის გაფილტვრა მიმდინარე დღის მიხედვით (მხოლოდ მათთვის, ვისაც დღეს უწევს შეკვეთა)
    active_calendar = calendar[calendar["order_day"].astype(float).astype(int) == today_weekday]

    #Edge Case: თუ დღეს არცერთ მაღაზიას/მომწოდებელს არ უწევს შეკვეთა, ცარიელ ცხრილს ვაბრუნებთ
    if active_calendar.empty:
        return pd.DataFrame()

    #საშ. დღ. გაყიდვების (ADS) გამოთვლა
    sales_summary = sales.groupby(["store", "supplier", "product_code"]).agg(
        total_sales=("sold_qty", "sum"),
        unique_days=("date", "nunique")
    ).reset_index()
    
    sales_summary["avg_daily_sales"] = sales_summary["total_sales"] / sales_summary["unique_days"]

    #მონაცემთა გაერთიანება (კავშირი მაღაზიით, მომწოდებლით და პროდუქტით)
    df = active_calendar.merge(current_stock, on=["store", "supplier"], how="inner") \
                        .merge(onway, on=["store", "supplier", "product_code"], how="left") \
                        .merge(minq, on=["store", "supplier", "product_code"], how="left") \
                        .merge(sales_summary, on=["store", "supplier", "product_code"], how="left")
    
    if df.empty:
        return pd.DataFrame()

    #თუ პროდუქტზე ნაშთი, გზაში ნაშთი მინიმალური ან გაყიდვები არ ფიქსირდება, ვავსებ 0-ით
    fill_values = {"current_qty": 0, "onway_qty": 0, "min_qty": 0, "avg_daily_sales": 0}
    df = df.fillna(value=fill_values)

    #Lead Time-ის დინამიური გამოთვლა
    order_days = df["order_day"].astype(float).astype(int)
    delivery_days = df["delivery_day"].astype(float).astype(int)
    df["lead_time"] = (delivery_days - order_days - 1) % 7 + 1

    #ბიზნეს ფორმულა შესაკვეთი რაოდენობისთვის
    df["order_qty"] = (df["avg_daily_sales"] * df["lead_time"]) + df["min_qty"] - (df["current_qty"] + df["onway_qty"])
    
    #უარყოფით შეკვეთებს ავტომატურად ვანულებ (clip)
    df["order_qty"] = df["order_qty"].clip(lower=0)

    df = df[df["order_qty"] > 0]

    #მიწოდების თარიღის გამოთვლა თითოეული სტრიქონისთვის lead_time-ის მიხედვით
    def compute_delivery_date(row):
        days_to_add = int(row["lead_time"])
        return today_dt + timedelta(days=days_to_add)

    #სისტემური თარიღების დამატება ბაზისთვის
    df["order_creation_date"] = today_dt
    df["delivery_date"] = df.apply(compute_delivery_date, axis=1)

    #მხოლოდ იმ სვეტების ვტოვებ, რომლებსაც მონაცემთა ბაზაში შევინახავ
    final_cols = [
        "order_creation_date", "delivery_date", "store", "supplier", 
        "product_code", "current_qty", "onway_qty", "min_qty", 
        "avg_daily_sales", "lead_time", "order_qty"
    ]
    
    return df[final_cols]