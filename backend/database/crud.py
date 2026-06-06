from sqlalchemy.orm import Session
from database.models import OrderResult

def get_order_history(db: Session, store=None, supplier=None, product_code=None):
    query = db.query(OrderResult)

    if store:
        query = query.filter(OrderResult.store == store)
    if supplier:
        query = query.filter(OrderResult.supplier == supplier)
    if product_code:
        query = query.filter(OrderResult.product_code == product_code)

    return query.order_by(OrderResult.id.desc()).all()


def save_order_results(db: Session, df):
    if df.empty:
        return

    records = [
        OrderResult(
            store=row["store"],
            supplier=row["supplier"],
            product_code=row["product_code"],
            current_qty=float(row["current_qty"]),
            onway_qty=float(row["onway_qty"]),
            min_qty=float(row["min_qty"]),
            avg_daily_sales=float(row["avg_daily_sales"]),
            lead_time=int(row["lead_time"]),
            order_qty=float(row["order_qty"]),
            order_creation_date=row["order_creation_date"],
            delivery_date=row["delivery_date"]
        )
        for _, row in df.iterrows()
    ]

    db.bulk_save_objects(records)
    db.commit()