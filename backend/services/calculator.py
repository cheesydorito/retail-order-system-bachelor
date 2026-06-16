from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def calculate_orders(dataframes: dict) -> pd.DataFrame:
    for df_name, df_obj in dataframes.items():
        if df_obj is not None:
            # სვეტების სახელების გასუფთავება
            df_obj.columns = df_obj.columns.str.strip()
            
            # ვასუფთავებ ტექსტურ მნიშვნელობებს ძირითად სვეტებში, რათა merge სწორად გაკეთდეს
            for col in ["store", "supplier", "product_code"]:
                if col in df_obj.columns:
                    df_obj[col] = df_obj[col].astype(str).str.strip()

    sales = dataframes["sales"]
    current_stock = dataframes["current_stock"]
    onway = dataframes["onway_stock"]
    minq = dataframes["MinQ"]
    calendar = dataframes["Calendar"]

    today_dt = datetime.now()
    active_calendar = calendar

    # Edge Case: თუ დღეს არცერთ მაღაზიას/მომწოდებელს არ უწევს შეკვეთა, ცარიელ ცხრილს ვაბრუნებთ
    if active_calendar.empty:
        return pd.DataFrame()

    # საშ. დღ. გაყიდვების (ADS) გამოთვლა
    sales_summary = sales.groupby(["store", "supplier", "product_code"]).agg(
        total_sales=("sold_qty", "sum"),
        unique_days=("date", "nunique")
    ).reset_index()
    
    sales_summary["avg_daily_sales"] = sales_summary["total_sales"] / sales_summary["unique_days"]

    # მონაცემთა გაერთიანება (კავშირი მაღაზიით, მომწოდებლით და პროდუქტით)
    df = active_calendar.merge(current_stock, on=["store", "supplier"], how="inner") \
                        .merge(onway, on=["store", "supplier", "product_code"], how="left") \
                        .merge(minq, on=["store", "supplier", "product_code"], how="left") \
                        .merge(sales_summary, on=["store", "supplier", "product_code"], how="left")
    
    if df.empty:
        return pd.DataFrame()

    # თუ პროდუქტზე ნაშთი, გზაში ნაშთი მინიმალური ან გაყიდვები არ ფიქსირდება, ვავსებ 0-ით (rounding-ისთვის ნაგულისხმევია 1)
    fill_values = {"current_qty": 0, "onway_qty": 0, "min_qty": 0, "avg_daily_sales": 0, "rounding": 1}
    df = df.fillna(value=fill_values)

    # Lead Time-ის დინამიური გამოთვლა
    order_days = df["order_day"].astype(float).astype(int)
    delivery_days = df["delivery_day"].astype(float).astype(int)
    df["lead_time"] = (delivery_days - order_days - 1) % 7 + 1

    # 1. საწყისი მათემატიკური მოთხოვნის დათვლა (დამრგვალებამდე)
    raw_qty = (df["avg_daily_sales"] * df["lead_time"]) + df["min_qty"] - (df["current_qty"] + df["onway_qty"])
    df["order_qty"] = raw_qty.clip(lower=0)

    # 2. Ceiling დამრგვალება 'rounding' (ჯერადის) მიხედვით
    # ვამრგვალებ მხოლოდ იმ პროდუქტებს, სადაც საწყისი შეკვეთა მეტია 0-ზე
    positive_order_mask = df["order_qty"] > 0
    df.loc[positive_order_mask, "order_qty"] = np.ceil(
        df.loc[positive_order_mask, "order_qty"] / df.loc[positive_order_mask, "rounding"]
    ) * df.loc[positive_order_mask, "rounding"]

    # 3. შემოწმება MinQ-ზე: თუ დამრგვალებული შეკვეთა მაინც ნაკლებია min_qty-ზე, ავიყვან min_qty-მდე
    min_qty_mask = (df["order_qty"] > 0) & (df["order_qty"] < df["min_qty"])
    df.loc[min_qty_mask, "order_qty"] = df.loc[min_qty_mask, "min_qty"]

    # ვტოვებ მხოლოდ იმ პროდუქტებს, რომელთა შესყიდვაც რეალურად საჭიროა
    df = df[df["order_qty"] > 0]

    if df.empty:
        return pd.DataFrame()

    # მიწოდების თარიღის გამოთვლა თითოეული სტრიქონისთვის lead_time-ის მიხედვით
    def compute_delivery_date(row):
        days_to_add = int(row["lead_time"])
        return today_dt + timedelta(days=days_to_add)

    # სისტემური თარიღების დამატება ბაზისთვის
    df["order_creation_date"] = today_dt
    df["delivery_date"] = df.apply(compute_delivery_date, axis=1)

    # მხოლოდ იმ სვეტების ვტოვებ, რომლებსაც მონაცემთა ბაზაში შევინახავ
    final_cols = [
        "order_creation_date", "delivery_date", "store", "supplier", 
        "product_code", "current_qty", "onway_qty", "min_qty", 
        "avg_daily_sales", "lead_time", "rounding", "order_qty"
    ]
    
    return df[final_cols]