from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI()

@app.get("/render")
def render(
    text: str,
    color: str = "#000000",
    bg_color: str = "#ffffff",
    font_size: int = 24,
    trim: bool = False
):
    # Use default font to avoid missing file errors
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Create canvas with solid background
    img = Image.new("RGBA", (1000, 300), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, font=font, fill=color)

    if trim:
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
