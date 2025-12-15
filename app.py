from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageColor
import io, math
import numpy as np
from scipy.ndimage import distance_transform_edt

app = FastAPI()

# Map sidebar dropdown values to your uploaded font files
FONTS = {
    "henny": "fonts/HennyPenny-Regular.ttf",
    "honk": "fonts/Honk-Regular-VariableFont_MORF,SHLN.ttf",
    "metamorphous": "fonts/Metamorphous-Regular.ttf",
    "monoton": "fonts/Monoton-Regular.ttf",
    "moolahlah": "fonts/MooLahLah-Regular.ttf",
    "mysteryquest": "fonts/MysteryQuest-Regular.ttf",
    "nabla": "fonts/Nabla-Regular-VariableFont_EDPT,EHLT.ttf",
    "pacifico": "fonts/Pacifico-Regular.ttf",
    "transformers": "fonts/Transformers Movie.ttf",
    "uncial": "fonts/UncialAntiqua-Regular.ttf"
}

def hex_to_rgba(hex_color: str):
    """Convert hex string (#rrggbb) to RGBA tuple."""
    return ImageColor.getrgb(hex_color) + (255,)

def load_font(name: str, size: int):
    """Load a font safely, fallback to default if missing."""
    path = FONTS.get(name)
    if not path:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

@app.get("/render")
def render(
    text: str,
    color: str = "#000000",
    bg_color: str = "#ffffff",
    font_size: int = 24,
    trim: bool = False,
    padding: int = 20,
    font: str = "henny",
    grad_start: str = None,
    grad_end: str = None,
    grad_shape: str = None,
    transparent: bool = False,
    glow_color: str = None,
    glow_size: int = 0,
    glow_falloff: float = 2.0,   # new parameter
    outline_color: str = None,
    outline_width: int = 0
):
    # Load chosen font
    font_obj = load_font(font, font_size)

    # Measure text size
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Add padding
    width = text_width + padding * 2
    height = text_height + padding * 2

    # Base image for stacking layers
    base = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # --- Glow with falloff ---
    if glow_color and int(glow_size) > 0:
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).text((padding, padding), text, font=font_obj, fill=255)

        mask_np = np.array(mask)
        dist = distance_transform_edt(mask_np == 0)

        falloff = np.clip(1 - (dist / int(glow_size)), 0, 1)
        falloff = falloff ** float(glow_falloff)  # exponent controls steepness
        alpha = (falloff * 255).astype(np.uint8)

        glow_layer = Image.new("RGBA", (width, height), ImageColor.getrgb(glow_color) + (0,))
        glow_layer.putalpha(Image.fromarray(alpha))
        base = Image.alpha_composite(base, glow_layer)

    # --- Outline + fill (solid text) ---
    outline_px = int(outline_width) if outline_color else 0
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text(
        (padding, padding),
        text,
        font=font_obj,
        fill=color,
        stroke_width=outline_px,
        stroke_fill=outline_color if outline_px > 0 else None
    )

    # --- Gradient fill ---
    if grad_start and grad_end and grad_shape:
        start_rgb = ImageColor.getrgb(grad_start)
        end_rgb   = ImageColor.getrgb(grad_end)   # <-- correct variable name

        fill_mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(fill_mask).text((padding, padding), text, font=font_obj, fill=255)

        gradient = Image.new("RGBA", (width, height))
        grad_draw = ImageDraw.Draw(gradient)

        if grad_shape == "vertical":
            for y in range(height):
                ratio = y / height
                r = int(start_rgb[0]*(1-ratio) + end_rgb[0]*ratio)
                g = int(start_rgb[1]*(1-ratio) + end_rgb[1]*ratio)
                b = int(start_rgb[2]*(1-ratio) + end_rgb[2]*ratio)
                grad_draw.line([(0,y),(width,y)], fill=(r,g,b,255))

        elif grad_shape == "horizontal_left":
            for x in range(width):
                ratio = x / width
                r = int(start_rgb[0]*(1-ratio) + end_rgb[0]*ratio)
                g = int(start_rgb[1]*(1-ratio) + end_rgb[1]*ratio)
                b = int(start_rgb[2]*(1-ratio) + end_rgb[2]*ratio)
                grad_draw.line([(x,0),(x,height)], fill=(r,g,b,255))

        elif grad_shape == "horizontal_right":
            for x in range(width):
                ratio = 1 - (x / width)
                r = int(start_rgb[0]*(1-ratio) + end_rgb[0]*ratio)
                g = int(start_rgb[1]*(1-ratio) + end_rgb[1]*ratio)
                b = int(start_rgb[2]*(1-ratio) + end_rgb[2]*ratio)
                grad_draw.line([(x,0),(x,height)], fill=(r,g,b,255))

        elif grad_shape == "radial":
            cx, cy = width//2, height//2
            max_dist = math.sqrt(cx**2 + cy**2)
            for y in range(height):
                for x in range(width):
                    dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                    ratio = min(dist/max_dist, 1)
                    r = int(start_rgb[0]*(1-ratio) + end_rgb[0]*ratio)
                    g = int(start_rgb[1]*(1-ratio) + end_rgb[1]*ratio)
                    b = int(start_rgb[2]*(1-ratio) + end_rgb[2]*ratio)
                    gradient.putpixel((x,y),(r,g,b,255))

        gradient.putalpha(fill_mask)
        base = Image.alpha_composite(base, text_layer)   # outline
        base = Image.alpha_composite(base, gradient)     # gradient fill
    else:
        base = Image.alpha_composite(base, text_layer)

    # Trim
    if trim:
        bbox = base.getbbox()
        if bbox:
            base = base.crop(bbox)

    # Background composite
    if transparent:
        final_img = base
    else:
        bg_rgba = ImageColor.getrgb(bg_color) + (255,)
        bg_img = Image.new("RGBA", base.size, bg_rgba)
        final_img = Image.alpha_composite(bg_img, base)

    # Return PNG
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
