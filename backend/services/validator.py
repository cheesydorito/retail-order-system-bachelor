import pandas as pd

FILE_SCHEMAS = {
    "current_stock": ["date", "store", "supplier", "product_code", "current_qty"],
    "sales": ["date", "store", "supplier", "product_code", "sold_qty"],
    "onway_stock": ["date", "store", "supplier", "product_code", "onway_qty"],
    "MinQ": ["store", "product_code", "supplier", "min_qty"],
    "Calendar": ["store", "supplier", "order_day", "delivery_day"] 
}

NUMERIC_COLUMNS = {
    "current_stock": ["current_qty"],
    "sales": ["sold_qty"],
    "onway_stock": ["onway_qty"],
    "MinQ": ["min_qty"],
    "Calendar": ["order_day", "delivery_day"]
}

REQUIRED_FILES = set(FILE_SCHEMAS.keys())

def validate_file(df: pd.DataFrame, file_key: str):
    required = set(FILE_SCHEMAS[file_key])
    present = set(df.columns)

    missing = required - present
    if missing:
        raise ValueError(f"ფაილში '{file_key}' აკლია სვეტები: {sorted(list(missing))}")

    if df[list(required)].isnull().any().any():
        raise ValueError(f"ფაილი '{file_key}' შეიცავს ცარიელ მნიშვნელობებს (Null/NaN/ცარიელი უჯრა)")

    for col in NUMERIC_COLUMNS.get(file_key, []):
        if (df[col] < 0).any():
            raise ValueError(f"ფაილში '{file_key}' სვეტში '{col}' დაფიქსირდა უარყოფითი მნიშვნელობები")

def validate_cross_data_consistency(dataframes: dict):
    master_df = dataframes["MinQ"]
    
    valid_stores = set(master_df["store"].unique())
    valid_suppliers = set(master_df["supplier"].unique())
    valid_products = set(master_df["product_code"].unique())

    for key, df in dataframes.items():
        if key == "MinQ":
            continue

        if "store" in df.columns:
            invalid_stores = set(df["store"].unique()) - valid_stores
            if invalid_stores:
                raise ValueError(f"ფაილში '{key}' ნაპოვნია წინასწარ განუსაზღვრელი მაღაზია (Store): {invalid_stores}")

        if "supplier" in df.columns:
            invalid_suppliers = set(df["supplier"].unique()) - valid_suppliers
            if invalid_suppliers:
                raise ValueError(f"ფაილში '{key}' ნაპოვნია წინასწარ განუსაზღვრელი მომწოდებელი (Supplier): {invalid_suppliers}")

        if "product_code" in df.columns:
            invalid_products = set(df["product_code"].unique()) - valid_products
            if invalid_products:
                raise ValueError(f"ფაილში '{key}' ნაპოვნია არავალიდური პროდუქტის კოდი: {invalid_products}")