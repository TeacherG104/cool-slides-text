from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

@app.get("/render")
def render_text(
    text: str = Query("Hello World"),
    color: str = Query("#ff0000"),
    font_size: int = Query(120),
    bg_color: str = Query("#ffffff")  # background color parameter
):
    # Create solid background image
    img = Image.new("RGBA", (800, 300), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to load a font; fall back if missing
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Measure text size using textbbox (modern Pillow)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    # Center text
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    draw.text((x, y), text, font=font, fill=color)

    # Return PNG
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.get("/")
def home():
    return {"status": "Renderer is running. Use /render?text=Hello&color=%23ff0000&bg_color=%23ffffff"}
