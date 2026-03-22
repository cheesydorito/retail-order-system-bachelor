import pandas as pd
from fastapi import HTTPException

FILE_SCHEMAS = {
    "current_stock": ["date", "store", "supplier", "product_code", "current_qty"],
    "sales": ["date", "store", "supplier", "product_code", "sold_qty"],
    "onway_stock": ["date", "store", "supplier", "product_code", "onway_qty"],
    "MinQ": ["store", "product_code", "supplier", "min_qty"],
    "Calendar": ["store", "supplier", "order_date", "delivery_date"]
}

NUMERIC_COLUMNS = {
    "current_stock": ["current_qty"],
    "sales": ["sold_qty"],
    "onway_stock": ["onway_qty"],
    "MinQ": ["min_qty"]
}

def validate_file(df: pd.DataFrame, file_key: str):
    required = set(FILE_SCHEMAS[file_key])
    present = set(df.columns)

    missing = required - present
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"{file_key}: Missing columns: {sorted(list(missing))}"
        )

    if df[list(required)].isnull().any().any():
        raise HTTPException(
            status_code=400,
            detail=f"{file_key}: Contains empty values"
        )

    for col in NUMERIC_COLUMNS.get(file_key, []):
        if (df[col] < 0).any():
            raise HTTPException(
                status_code=400,
                detail=f"{file_key}: Negative values found in {col}"
            )