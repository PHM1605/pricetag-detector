from openai import OpenAI
from typing import List
from PIL import Image
from pathlib import Path
from io import BytesIO
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Body
import os
import base64
import json
from app.models import Pricetag, AnalyzeRequest
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()
app = FastAPI()

DATA_LOC = Path("../data/")
DATA_IMAGES = DATA_LOC / "images"
DATA_LABELS = DATA_LOC / "labels"
DATA_CLASSES = DATA_LOC / "classes.txt"
CROPS_DIR = DATA_LOC / "crops"
CROPS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static/images", StaticFiles(directory=DATA_IMAGES))
app.mount("/static/crops", StaticFiles(directory=CROPS_DIR))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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


def list_classes(path: Path):
    return [line for line in path.read_text().splitlines() if line.strip()]


def image_size(path: str):
    with Image.open(path) as img:
        return img.width, img.height

# [(cls_id, x_norm, y_norm, w_norm, h_norm),...]


def read_yolo_labels(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            parts = line.split()
            if len(parts) == 0:
                continue
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


def crop_from_norm_box(image_path, box_norm, box_id, save=False):
    xn, yn, wn, hn = box_norm
    W, H = image_size(image_path)
    x, y, w, h = norm_to_pixels(xn, yn, wn, hn, W, H)
    with Image.open(image_path) as im:
        crop = im.crop((x, y, x+w, y+h))
        # optional save to disk
        saved_path = None
        if save:
            base = Path(image_path).stem
            fname = f"{base}_box{box_id or 0}.png"
            saved_path = CROPS_DIR / fname
            crop.convert("RGBA" if crop.mode == "P" else "RGB").save(
                saved_path, format="PNG")

        buf = BytesIO()
        crop.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return crop, b64, saved_path


@app.get("/images")
def get_images():
    images = list_images()
    return images


SYSTEM_PROMPT = (
    "You are a price reader. Extract prices and time discount from a price tag image."
    "Return strict JSON with fields: main_price (string or null), discount_price (string or null), and time_discount (object or null with fields: time_start (string or null), time_end (string or null)), and what_was_read (array of strings)."
    "Note that: Sometimes, when displaying prices, the digits in the thousands place are shown larger in size, while the digits in the hundreds, tens, and ones places are shown smaller."
    "Do NOT include any other text."
)

# Send a pricetag image URL (cropped box) to OpenAI Vision API

im = Image.open(
    r'C:\workspace\work\check_pricetag\pricetag-detector\data\sample\0B41B537-9E50-4F40-8BA6-77B445455455_box1.png')
buf = BytesIO()
im.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode("utf-8")


@app.post("/analyze-price-tag", response_model=Pricetag)
async def analyze_price_tag(payload: AnalyzeRequest = Body(...)):
    img_path = str(DATA_IMAGES / payload.image)
    _, crop_b64, saved_path = crop_from_norm_box(
        img_path, payload.box, save=True, box_id=payload.box_id)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": "Read prices and time discount from this price tag. JSON only. Example: {b64} main price: 195.400đ"},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{crop_b64}"}}
        ]}
    ]
    try:
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0
        )
        text = (chat.choices[0].message.content or "").strip()
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        data = {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"main_price": None, "discount_price": None,
                    "time_discount": None, "what_was_read": [text]}
        what = data.get("what_was_read") or []
        if saved_path:
            what = [f"debug_crop: /static/crops/{saved_path.name}", *what]

        return Pricetag(
            box_id=payload.box_id,
            main_price=data.get("main_price"),
            discount_price=data.get("discount_price"),
            time_discount=data.get("time_discount"),
            what_was_read=what
        )
    except Exception as e:
        debug = [
            f"debug_crop: /static/crops/{saved_path.name}"] if saved_path else []
        return Pricetag(
            box_id=payload.box_id,
            main_price=None,
            discount_price=None,
            what_was_read=[f"fallback: {type(e).__name__}"]
        )

# get YOLO boxes (pixel) for filename without extension


@app.get("/labels/{base_name}")
def get_labels(base_name):
    imgs = [f for f in list_images() if os.path.splitext(f)[0] == base_name]
    img_path = os.path.join(DATA_IMAGES, imgs[0])
    label_path = os.path.join(DATA_LABELS, base_name+".txt")
    rows = read_yolo_labels(label_path)
    boxes = []
    classes = list_classes(DATA_CLASSES)
    for box_id, (cls, xn, yn, wn, hn) in enumerate(rows):
        boxes.append({
            "id": box_id,
            "box": [xn, yn, wn, hn],
            "label": classes[cls]
        })
    return boxes
