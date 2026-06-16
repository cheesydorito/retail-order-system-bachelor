from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Unicode
from database.database import Base

class OrderResult(Base):
    __tablename__ = "order_results"

    id = Column(Integer, primary_key=True, index=True)
    store = Column(String(50))
    supplier = Column(Unicode(150))
    product_code = Column(String(50))
    
    current_qty = Column(Float, default=0.0)      
    onway_qty = Column(Float, default=0.0)        
    min_qty = Column(Float, default=0.0)          
    avg_daily_sales = Column(Float, default=0.0)  
    lead_time = Column(Integer)    
    rounding = Column(Integer, default=1)               
    order_qty = Column(Float)                     
    
    order_creation_date = Column(DateTime, default=datetime.now) 
    delivery_date = Column(DateTime)                             