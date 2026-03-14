from sqlalchemy import Column, Integer, String, Float
from database.database import Base

class OrderResult(Base):
    __tablename__ = "order_results"

    id = Column(Integer, primary_key=True, index=True)
    store = Column(String)
    supplier = Column(String)
    product_code = Column(String)
    order_qty = Column(Float)
