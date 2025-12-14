from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageColor
import io

app = FastAPI()

# Map sidebar dropdown values to bundled font files
FONTS = {
    "sans": "fonts/DejaVuSans.ttf",
    "serif": "fonts/DejaVuSerif.ttf",
    "handwriting": "fonts/Pacifico-Regular.ttf",
    "display": "fonts/Lobster-Regular.ttf"
}

def hex_to_rgba(hex_color: str):
    """Convert hex string (#rrggbb) to RGBA tuple."""
    return ImageColor.getrgb(hex_color) + (255,)

@app.get("/render")
def render(
    text: str,
    color: str = "#000000",
    bg_color: str = "#ffffff",
    font_size: int = 24,
    trim: bool = False,
    padding: int = 20,
    font: str = "sans",
    grad_start: str = None,
    grad_end: str = None
):
    # Load chosen font (fallback to default if missing)
    font_path = FONTS.get(font, FONTS["sans"])
    try:
        font_obj = ImageFont.truetype(font_path, font_size)
    except Exception:
        font_obj = ImageFont.load_default()

    # Measure text size
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Add padding
    width = text_width + padding * 2
    height = text_height + padding * 2

    # Transparent layer for text
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    if grad_start and grad_end:
        start_rgb = ImageColor.getrgb(grad_start)
        end_rgb = ImageColor.getrgb(grad_end)

        # Create mask for text
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((padding, padding), text, font=font_obj, fill=255)

        # Create gradient
        gradient = Image.new("RGBA", (width, height))
        grad_draw = ImageDraw.Draw(gradient)
        for y in range(height):
            ratio = y / height
            r = int(start_rgb[0] * (1-ratio) + end_rgb[0] * ratio)
            g = int(start_rgb[1] * (1-ratio) + end_rgb[1] * ratio)
            b = int(start_rgb[2] * (1-ratio) + end_rgb[2] * ratio)
            grad_draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # Apply mask so gradient only shows inside text
        gradient.putalpha(mask)
        text_layer = gradient
    else:
        # Solid color text
        text_draw.text((padding, padding), text, font=font_obj, fill=color)

    # Trim based on text pixels
    if trim:
        bbox = text_layer.getbbox()
        if bbox:
            text_layer = text_layer.crop(bbox)

    # Composite onto background AFTER trimming
    bg_rgba = hex_to_rgba(bg_color)
    bg_img = Image.new("RGBA", text_layer.size, bg_rgba)
    final_img = Image.alpha_composite(bg_img, text_layer)

    # Return PNG
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
