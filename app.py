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
    trim: bool = False,
    padding: int = 20
):
    # Load a font safely
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Measure text size
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
    # textbbox returns (x0, y0, x1, y1), so width = x1, height = y1

    # Add padding
    width = text_width + padding * 2
    height = text_height + padding * 2

    # Create canvas sized to text
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((padding, padding), text, font=font, fill=color)

    if trim:
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
