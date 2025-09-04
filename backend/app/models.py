from pydantic import BaseModel, Field
from typing import List

class Pricetag(BaseModel):
  box_id: int 
  main_price: str|None = None 
  discount_price: str|None = None 
  what_was_read: List[str] = Field(default_factory=list)

class AnalyzeRequest(BaseModel):
  image: str # e.g. "img2.png"
  box: List[float] # [0.2,0.3,0.4,0.4]
  box_id: int 