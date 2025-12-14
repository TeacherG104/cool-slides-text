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
    # Load a font (make sure arial.ttf or another font file is available in your environment)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Create a large enough canvas
    img = Image.new("RGBA", (1000, 300), bg_color)
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, font=font, fill=color)

    if trim:
        # Find the bounding box of non-background pixels
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

    # Return as PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
