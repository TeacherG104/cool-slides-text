from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI()

def hex_to_rgba(hex_color: str):
    hex_color = hex_color.lstrip('#')
    lv = len(hex_color)
    return tuple(int(hex_color[i:i+lv//3], 16) for i in range(0, lv, lv//3)) + (255,)

@app.get("/render")
def render(
    text: str,
    color: str = "#000000",
    bg_color: str = "#ffffff",
    font_size: int = 24,
    trim: bool = False,
    padding: int = 20
):
    # Load a scalable font
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Measure text size
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Add padding
    width = text_width + padding * 2
    height = text_height + padding * 2

    # Use chosen background color
    bg_rgba = hex_to_rgba(bg_color)
    img = Image.new("RGBA", (width, height), bg_rgba)
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
