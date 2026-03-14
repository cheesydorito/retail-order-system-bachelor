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
