from fastapi import FastAPI, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI()

def load_font(font_name: str = "Arial", size: int = 64):
    try:
        return ImageFont.truetype(f"{font_name}.ttf", size)
    except Exception:
        return ImageFont.load_default()

def render_text_image(text: str, color: str, font_name: str):
    font_obj = load_font(font_name, 64)
    width, height = 600, 200
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font_obj)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((width - w) // 2, (height - h) // 2), text, fill=color, font=font_obj)

    return img
from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # or restrict to specific origins later
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/render")
def render_preview(
    text: str = Query(...),
    color: str = Query("#000000"),
    font: str = Query("Arial")
):
    try:
        img = render_text_image(text, color, font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/render")
def render_insert(payload: dict = Body(...)):
    try:
        text = payload.get("text", "")
        color = payload.get("color", "#000000")
        font = payload.get("font", "Arial")
        img = render_text_image(text, color, font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
