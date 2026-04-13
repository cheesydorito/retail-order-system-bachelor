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

    records = [
        OrderResult(
            store=row["store"],
            supplier=row["supplier"],
            product_code=row["product_code"],
            order_qty=float(row["order_qty"])
        )
        for _, row in df.iterrows()
    ]

    db.bulk_save_objects(records)
    db.commit()