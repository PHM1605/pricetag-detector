import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI 
from fastapi.staticfiles import StaticFiles
from openai import OpenAI 
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from app.models import Box, Pricetag
from typing import List

client = OpenAI()
app = FastAPI()

DATA_LOC = Path("../data/")
DATA_IMAGES = DATA_LOC / "images"
DATA_LABELS = DATA_LOC / "labels"

app.mount("/static/images", StaticFiles(directory=DATA_IMAGES))

app.add_middleware(
  CORSMiddleware,
  allow_origins= [
    "http://localhost:5173",  # Vite
    "http://localhost:3000",  # CRA/Next
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"]
)

# list of ["img1.jpg", "img3.jpg",...]
def list_images():
  imgs = []
  for f in os.listdir(DATA_IMAGES):
    lf = f.lower()
    if lf.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
      imgs.append(f)
  imgs.sort()
  return imgs 

def image_size(path:str):
  with Image.open(path) as img:
    return img.width, img.height

# [(cls_id, x_norm, y_norm, w_norm, h_norm),...]
def read_yolo_labels(path):
  rows = []
  with open(path, "r", encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      parts = line.split()
      cls = int(float(parts[0]))
      x, y, w, h = map(float, parts[1:])
      rows.append((cls, x, y, w, h))
  return rows 

def norm_to_pixels(xn, yn, wn, hn, W, H):
  cx = xn*W 
  cy = yn*H
  w = wn*W 
  h = hn*H 
  x = int(round(cx - w/2))
  y = int(round(cy - h/2))
  w = int(round(w))
  h = int(round(h))
  # clamp
  x = max(0, min(W-1, x))
  y = max(0, min(H-1, y))
  if x+w > W: 
    w = W-x
  if y+h > H:
    h = H-y 
  return x, y, w, h

@app.get("/images")
def get_images():
  images = list_images()
  return images

# Send a pricetag image URL (cropped box) to OpenAI Vision API 
@app.post("/analyze-price-tag")
async def analyze_price_tag(img_url):
  response = client.responses.create()

# get YOLO boxes (pixel) for filename without extension
@app.get("/labels/{base_name}")
def get_labels(base_name):
  imgs = [f for f in list_images() if os.path.splitext(f)[0] == base_name]
  img_path = os.path.join(DATA_IMAGES, imgs[0])
  W, H = image_size(img_path)
  label_path = os.path.join(DATA_LABELS, base_name+".txt")
  rows = read_yolo_labels(label_path)
  boxes: List[Box] = []
  box_id = 0
  for cls, xn, yn, wn, hn in rows:
    x, y, w, h = norm_to_pixels(xn, yn, wn, hn, W, H)
    boxes.append(Box(id=box_ix, x=x, y=y, w=w, h=h))
    box_id += 1
  return boxes 
