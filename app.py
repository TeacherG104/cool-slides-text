from fastapi import FastAPI, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI()

# Utility: load a font safely
def load_font(font_name: str = "Arial", size: int = 64):
    try:
        return ImageFont.truetype(f"{font_name}.ttf", size)
    except Exception:
        # Fallback to default PIL font if custom font not found
        return ImageFont.load_default()

# Utility: render text into a PNG
def render_text_image(text: str, color: str, font_name: str):
    font_obj = load_font(font_name, 64)
    width, height = 600, 200
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    w, h = draw.textsize(text, font=font_obj)
    draw.text(((width - w) // 2, (height - h) // 2), text, fill=color, font=font_obj)
    return img

# Utility: render fraction into a PNG
def render_fraction_image(numerator: str, denominator: str, numColor: str, denColor: str):
    font_obj = load_font("Arial", 64)
    width, height = 300, 200
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Numerator
    w_num, h_num = draw.textsize(numerator, font=font_obj)
    draw.text(((width - w_num) // 2, 20), numerator, fill=numColor, font=font_obj)

    # Divider line
    draw.line((20, height // 2, width - 20, height // 2), fill="black", width=4)

    # Denominator
    w_den, h_den = draw.textsize(denominator, font=font_obj)
    draw.text(((width - w_den) // 2, height // 2 + 20), denominator, fill=denColor, font=font_obj)

    return img

# --- TEXT ENDPOINTS ---

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

# --- FRACTION ENDPOINTS ---

@app.get("/fraction")
def fraction_preview(
    numerator: str = Query(...),
    denominator: str = Query(...),
    numColor: str = Query("#000000"),
    denColor: str = Query("#000000")
):
    try:
        img = render_fraction_image(numerator, denominator, numColor, denColor)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/fraction")
def fraction_insert(payload: dict = Body(...)):
    try:
        numerator = payload.get("numerator", "")
        denominator = payload.get("denominator", "")
        numColor = payload.get("numColor", "#000000")
        denColor = payload.get("denColor", "#000000")
        img = render_fraction_image(numerator, denominator, numColor, denColor)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
