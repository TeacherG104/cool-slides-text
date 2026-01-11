import io
import math
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================================================
# FASTAPI APP SETUP
# =========================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can tighten this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# UTILS
# =========================================================

def hex_to_rgb(hex_color: str):
    """Convert #RRGGBB or #RGB to (R, G, B)."""
    hex_color = hex_color.strip()
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]

    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])

    if len(hex_color) != 6:
        return (255, 255, 255)

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(font_path, size=size)
    except Exception:
        # Fallback to PIL default if font not found
        return ImageFont.load_default()


def make_multi_stop_gradient(width: int, height: int, colors: List[str], gradient_type: str) -> Image.Image:
    """
    Create a multi-stop gradient image of size (width, height).

    colors: list of hex strings, e.g. ["#ff0000", "#00ff00", "#0000ff"].
    gradient_type: "horizontal", "vertical", "diagonal", "radial"
    """
    if not colors:
        colors = ["#ffffff", "#000000"]
    if len(colors) == 1:
        colors = [colors[0], colors[0]]

    # Convert colors to RGB
    stops_rgb = [hex_to_rgb(c) for c in colors]
    num_stops = len(stops_rgb)

    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    def interp_color(t: float):
        """Interpolate along the list of color stops for position t in [0, 1]."""
        if t <= 0:
            return stops_rgb[0]
        if t >= 1:
            return stops_rgb[-1]

        scaled = t * (num_stops - 1)
        i = int(math.floor(scaled))
        frac = scaled - i

        c1 = stops_rgb[i]
        c2 = stops_rgb[i + 1]

        r = int(c1[0] + (c2[0] - c1[0]) * frac)
        g = int(c1[1] + (c2[1] - c1[1]) * frac)
        b = int(c1[2] + (c2[2] - c1[2]) * frac)
        return (r, g, b)

    for y in range(height):
        for x in range(width):
            if gradient_type == "horizontal":
                t = x / (width - 1) if width > 1 else 0.0
            elif gradient_type == "vertical":
                t = y / (height - 1) if height > 1 else 0.0
            elif gradient_type == "diagonal":
                t = (x + y) / (width + height - 2) if (width + height) > 2 else 0.0
            elif gradient_type == "radial":
                cx = (width - 1) / 2.0
                cy = (height - 1) / 2.0
                dx = x - cx
                dy = y - cy
                dist = math.sqrt(dx * dx + dy * dy)
                max_dist = math.sqrt(cx * cx + cy * cy)
                t = dist / max_dist if max_dist > 0 else 0.0
                t = min(max(t, 0.0), 1.0)
            else:
                # Fallback to horizontal if unknown type
                t = x / (width - 1) if width > 1 else 0.0

            pixels[x, y] = interp_color(t) + (255,)

    return img


def measure_text_box(text: str, font_obj: ImageFont.FreeTypeFont):
    """Measure text bounding box using a scratch image."""
    tmp_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp_img)
    bbox = d.textbbox((0, 0), text, font=font_obj)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h


# =========================================================
# CORE RENDER FUNCTION
# =========================================================

def render_text_image(
    text: str,
    font_path: str,
    size: int,
    text_color: str,
    gradient_type: str,
    gradient_colors: List[str],
    transparent: bool,
    background_color: str,
    glow_color: Optional[str],
    glow_size: float,
    glow_intensity: float,
    outline_color: Optional[str],
    outline_size: float,
) -> Image.Image:
    # Load font
    font_obj = load_font(font_path, size)

    # Measure text
    text_width, text_height = measure_text_box(text, font_obj)

    # Add padding so glow/outline don’t clip
    padding = max(int(glow_size * 2), int(outline_size * 2), 20)
    width = text_width + padding * 2
    height = text_height + padding * 2

    # Text position
    x = padding
    y = padding

    # Base image
    base_bg = (0, 0, 0, 0) if transparent else hex_to_rgb(background_color) + (255,)
    img = Image.new("RGBA", (width, height), base_bg)

    # ---------------------------------------------------------
    # 1. MULTI-LAYER GLOW (BEHIND EVERYTHING)
    # ---------------------------------------------------------
    if glow_color and glow_size > 0 and glow_intensity > 0:
        glow_layers = []
        base_mask = Image.new("L", img.size, 0)
        mask_draw = ImageDraw.Draw(base_mask)
        mask_draw.text((x, y), text, font=font_obj, fill=255)

        radii = [
            glow_size * 0.25,
            glow_size * 0.6,
            glow_size,
        ]

        alphas = [
            int(255 * glow_intensity * 1.0),
            int(255 * glow_intensity * 0.6),
            int(255 * glow_intensity * 0.3),
        ]

        for r, a in zip(radii, alphas):
            blurred = base_mask.filter(ImageFilter.GaussianBlur(radius=r))
            layer = Image.new("RGBA", img.size, hex_to_rgb(glow_color) + (0,))
            layer.putalpha(blurred.point(lambda p: min(p, a)))
            glow_layers.append(layer)

        for g in glow_layers:
            img = Image.alpha_composite(img, g)

    # ---------------------------------------------------------
    # 2. OUTLINE (MIDDLE LAYER)
    # ---------------------------------------------------------
    if outline_color and outline_size > 0:
        outline_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(outline_img)
        steps = int(outline_size)

        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                if dx != 0 or dy != 0:
                    od.text((x + dx, y + dy), text, font=font_obj, fill=outline_color)

        img = Image.alpha_composite(img, outline_img)

    # ---------------------------------------------------------
    # 3. TEXT FILL (TOP LAYER: GRADIENT OR SOLID)
    # ---------------------------------------------------------
    draw = ImageDraw.Draw(img)

    if gradient_type and gradient_type != "none" and gradient_colors:
        # Gradient area exactly the size of the text bounding box
        gradient_img = make_multi_stop_gradient(text_width, text_height, gradient_colors, gradient_type)

        # Mask for the text
        mask = Image.new("L", (text_width, text_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((0, 0), text, font=font_obj, fill=255)

        text_area = Image.composite(
            gradient_img,
            Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0)),
            mask,
        )
        img.paste(text_area, (x, y), text_area)
    else:
        # Solid text color
        draw.text((x, y), text, font=font_obj, fill=text_color)

    return img


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/ping", response_class=PlainTextResponse)
def ping():
    return "pong"


@app.get("/render")
def render(
    text: str = Query("Hello"),
    font: str = Query("/fonts/Pacifico-Regular.ttf"),
    size: int = Query(120),
    textColor: str = Query("#ffffff"),
    gradientType: str = Query("none"),
    gradientColors: str = Query("[]"),  # JSON string from client
    transparent: bool = Query(False),
    backgroundColor: str = Query("#000000"),
    resizeToText: bool = Query(False),  # kept for compatibility, not used here
    glowColor: Optional[str] = Query(None),
    glowSize: float = Query(0.0),
    glowIntensity: float = Query(0.0),
    outlineColor: Optional[str] = Query(None),
    outlineSize: float = Query(0.0),
):
    # Parse gradient colors JSON string safely
    import json

    try:
        colors = json.loads(gradientColors)
        if not isinstance(colors, list):
            colors = []
    except Exception:
        colors = []

    # Normalize colors to strings
    colors = [str(c) for c in colors if c]

    # Render the image
    img = render_text_image(
        text=text,
        font_path=font,
        size=size,
        text_color=textColor,
        gradient_type=gradientType,
        gradient_colors=colors,
        transparent=transparent,
        background_color=backgroundColor,
        glow_color=glowColor,
        glow_size=glowSize,
        glow_intensity=glowIntensity,
        outline_color=outlineColor,
        outline_size=outlineSize,
    )

    # Return as PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
