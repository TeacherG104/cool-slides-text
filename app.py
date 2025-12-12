from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

import logging
logger = logging.getLogger("uvicorn")

@app.get("/render")
def render_text(
    text: str = Query("Hello World"),
    color: str = Query("#ff0000"),
    font_size: int = Query(120),
    bg_color: str = Query("#ffffff")
):
    logger.info(f"Render called with text={text}, color={color}, font_size={font_size}, bg_color={bg_color}")
    try:
        img = Image.new("RGBA", (800, 300), bg_color)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except Exception as e:
            logger.warning(f"Font load failed: {e}")
            font = ImageFont.load_default()

        w, h = draw.textsize(text, font=font)
        x = (img.width - w) // 2
        y = (img.height - h) // 2
        draw.text((x, y), text, font=font, fill=color)

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        logger.error(f"Render failed: {e}")
        return {"error": str(e)}

@app.get("/render")
def render_text(
    text: str = Query("Hello World"),
    color: str = Query("#ff0000"),
    font_size: int = Query(120),
    bg_color: str = Query("#ffffff")  # background color parameter
):
    # Create solid background image
    img = Image.new("RGBA", (800, 300), bg_color)  # solid background instead of transparent
    draw = ImageDraw.Draw(img)

    # Try to load a font; fall back if missing
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
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

@app.get("/")
def home():
    return {"status": "Renderer is running. Use /render?text=Hello&color=%23ff0000&bg_color=%23ffffff"}
