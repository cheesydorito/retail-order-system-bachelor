import pandas as pd

def calculate_orders(dataframes: dict) -> pd.DataFrame:

    current_stock = dataframes["current_stock"]
    sales = dataframes["sales"]
    onway = dataframes["onway_stock"]
    minq = dataframes["MinQ"]
    calendar = dataframes["Calendar"]

    # გაყიდვების საშუალო რაოდენობა
    sales["date"] = pd.to_datetime(sales["date"])

    sales_summary = (
        sales.groupby(["store", "supplier", "product_code"])
        .agg(
            total_sales=("sold_qty", "sum"),
            days=("date", "nunique")
        )
        .reset_index()
    )

    sales_summary["avg_daily_sales"] = sales_summary["total_sales"] / sales_summary["days"]

    # მონაცემების გაერთიანება
    df = (
        current_stock
        .merge(onway, on=["store","supplier","product_code"], how="left")
        .merge(minq, on=["store","supplier","product_code"], how="left")
        .merge(sales_summary, on=["store","supplier","product_code"], how="left")
    )

    df.fillna(0, inplace=True)

    # მარტივი შეკვეთის ფორმულა
    df["order_qty"] = (
        df["avg_daily_sales"] * 7
        + df["min_qty"]
        - (df["current_qty"] + df["onway_qty"])
    )

    df["order_qty"] = df["order_qty"].clip(lower=0)

    return df