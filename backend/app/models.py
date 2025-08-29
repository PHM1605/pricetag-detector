from pydantic import BaseModel 
from typing import List

class Box(BaseModel):
  id: int 
  x: int 
  y: int 
  w: int 
  h: int 
  cls: str

class Pricetag(BaseModel):
  box_id: int 
  main_price: str|None = None 
  discount_price: str|None = None 
  what_was_read: List[str] = None

