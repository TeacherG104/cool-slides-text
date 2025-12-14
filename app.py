from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
import io, math

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

    # Transparent layer for text
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    # --- Outline effect ---
    if outline_color and outline_width > 0:
        outline_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        outline_draw = ImageDraw.Draw(outline_layer)
        for dx in range(-outline_width, outline_width+1):
            for dy in range(-outline_width, outline_width+1):
                outline_draw.text((padding+dx, padding+dy), text, font=font_obj, fill=outline_color)
        text_layer = Image.alpha_composite(text_layer, outline_layer)

    # --- Gradient or solid fill ---
    if grad_start and grad_end and grad_shape:
        start_rgb = ImageColor.getrgb(grad_start)
        end_rgb = ImageColor.getrgb(grad_end)

        # Create mask for text
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((padding, padding), text, font=font_obj, fill=255)

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

        gradient.putalpha(mask)
        text_layer = Image.alpha_composite(text_layer, gradient)
    else:
        # Solid color text
        text_draw.text((padding, padding), text, font=font_obj, fill=color)

        # --- Glow effect ---
    if glow_color and glow_size > 0:
        # Create mask of text
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((padding, padding), text, font=font_obj, fill=255)

        # Expand mask outward before blur
        expanded = mask.filter(ImageFilter.MaxFilter(glow_size*2+1))

        # Tint with glow color
        glow_layer = Image.new("RGBA", (width, height), hex_to_rgba(glow_color))
        glow_layer.putalpha(expanded)

        # Blur to soften edges
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_size))

        # Composite glow behind text
        combined = Image.new("RGBA", (width, height), (0,0,0,0))
        combined = Image.alpha_composite(combined, glow_layer)
        combined = Image.alpha_composite(combined, text_layer)
        text_layer = combined

    # Composite onto background AFTER trimming
    if transparent:
        final_img = text_layer
    else:
        bg_rgba = hex_to_rgba(bg_color)
        bg_img = Image.new("RGBA", text_layer.size, bg_rgba)
        final_img = Image.alpha_composite(bg_img, text_layer)

    # Return PNG
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
