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
    # Load scalable font
    font = ImageFont.truetype("DejaVuSans.ttf", font_size)

    # Transparent layer for text
    temp_img = Image.new("RGBA", (2000, 500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp_img)
    draw.text((padding, padding), text, font=font, fill=color)

    # Crop to text bounding box
    bbox = temp_img.getbbox()
    if trim and bbox:
        temp_img = temp_img.crop(bbox)

    # Add background
    bg_rgba = hex_to_rgba(bg_color)
    bg_img = Image.new("RGBA", temp_img.size, bg_rgba)
    final_img = Image.alpha_composite(bg_img, temp_img)

    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
