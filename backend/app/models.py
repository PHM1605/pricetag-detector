from pydantic import BaseModel, Field
from typing import List, Optional

class TimeDiscount(BaseModel):
    time_start: str|None = None 
    time_end: str|None = None

class Pricetag(BaseModel):
  box_id: int 
  product_name: Optional[str] = None
  main_price: Optional[int] = None
  discount_price: Optional[int] = None
  discount_type: Optional[str] = None
  time_discount: Optional[TimeDiscount] = None
  what_was_read: List[str] = Field(default_factory=list)

class AnalyzeRequest(BaseModel):
  image: str # e.g. "img2.png"
  box: List[float] # [0.2,0.3,0.4,0.4]
  box_id: int 