from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

@app.get("/render")
def render_text(
    text: str = Query("Hello World"),
    color: str = Query("#ff0000"),
    font_size: int = Query(120)
):
    # Create blank transparent image
    img = Image.new("RGBA", (800, 300), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Try to load a font; fall back if missing
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)  # safer than arial.ttf
    except:
        font = ImageFont.load_default()

    # Draw text centered
    w, h = draw.textsize(text, font=font)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    draw.text((x, y), text, font=font, fill=color)

    # Return PNG
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
    # Return PNG
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
@app.get("/")
def home():
    return {"status": "Renderer is running. Use /render?text=Hello&color=%23ff0000"}
