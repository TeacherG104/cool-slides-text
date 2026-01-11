import io
import os
import json
from typing import Optional, List
from urllib.parse import unquote

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor

# ============================================================
# APP SETUP
# ============================================================

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# HELPER: LOAD FONT SAFELY
# ============================================================

def resolve_font_path(font_path: str) -> str:
    """
    - Decode URL-encoded font names (spaces, commas, etc.)
    - Map /fonts/... to local filesystem path under project
    """
    font_path = unquote(font_path)

    if font_path.startswith("/fonts/"):
        local_font = font_path.lstrip("/")  # "fonts/HennyPenny-Regular.ttf"
        font_path = os.path.join(BASE_DIR, local_font)

    return font_path


# ============================================================
# HELPER: CREATE GRADIENT FILL
# ============================================================

def create_gradient_fill(
    width: int,
    height: int,
    gradient_type: str,
    colors: List[str]
) -> Image.Image:
    """
    Simple multi-stop linear gradient.
    gradient_type can be "linear-horizontal", "linear-vertical", or fallback.
    """
    if not colors:
        colors = ["#ffffff", "#000000"]

    if len(colors) == 1:
        colors = [colors[0], colors[0]]

    stops = [ImageColor.getrgb(c) for c in colors]

    if gradient_type == "linear-vertical":
        grad = Image.new("RGB", (1, height))
        draw = ImageDraw.Draw(grad)
        steps = height
        for y in range(steps):
            t = y / max(steps - 1, 1)
            idx = int(t * (len(stops) - 1))
            t_local = (t * (len(stops) - 1)) - idx
            c1 = stops[idx]
            c2 = stops[min(idx + 1, len(stops) - 1)]
            r = int(c1[0] + (c2[0] - c1[0]) * t_local)
            g = int(c1[1] + (c2[1] - c1[1]) * t_local)
            b = int(c1[2] + (c2[2] - c1[2]) * t_local)
            draw.point((0, y), (r, g, b))
        grad = grad.resize((width, height))
    else:
        # default horizontal
        grad = Image.new("RGB", (width, 1))
        draw = ImageDraw.Draw(grad)
        steps = width
        for x in range(steps):
            t = x / max(steps - 1, 1)
            idx = int(t * (len(stops) - 1))
            t_local = (t * (len(stops) - 1)) - idx
            c1 = stops[idx]
            c2 = stops[min(idx + 1, len(stops) - 1)]
            r = int(c1[0] + (c2[0] - c1[0]) * t_local)
            g = int(c1[1] + (c2[1] - c1[1]) * t_local)
            b = int(c1[2] + (c2[2] - c1[2]) * t_local)
            draw.point((x, 0), (r, g, b))
        grad = grad.resize((width, height))

    return grad.convert("RGBA")


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
    # --------------------------------------------------------
    # 1. Resolve font path & load font
    # --------------------------------------------------------
    font_path = resolve_font_path(font_path)
    font = ImageFont.truetype(font_path, size)

    # --------------------------------------------------------
    # 2. Measure text
    # --------------------------------------------------------
    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    text_w, text_h = x1 - x0, y1 - y0

    pad = max(20, int(size * 0.3))
    width = text_w + pad * 2
    height = text_h + pad * 2

    # --------------------------------------------------------
    # 3. Base image
    # --------------------------------------------------------
    if transparent:
        base_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        bg = ImageColor.getrgb(background_color)
        base_image = Image.new("RGBA", (width, height), bg)

    # --------------------------------------------------------
    # 4. Crisp text mask
    # --------------------------------------------------------
    text_mask = Image.new("L", (width, height), 0)
    md = ImageDraw.Draw(text_mask)

    text_y = (height - text_h) // 2 - 2
    md.text((pad, text_y), text, font=font, fill=255)

    mask_crisp = text_mask

    # --------------------------------------------------------
    # 5. Soft mask (gradient only)
    # --------------------------------------------------------
    has_gradient = gradient_type != "none" and bool(gradient_colors)

    if has_gradient:
        mask_soft = mask_crisp.filter(ImageFilter.GaussianBlur(radius=2))
    else:
        mask_soft = mask_crisp

    # --------------------------------------------------------
    # 6. Text fill
    # --------------------------------------------------------
    if has_gradient:
        grad_img = create_gradient_fill(
            width,
            height,
            gradient_type,
            gradient_colors
        )
        base_image.paste(grad_img, (0, 0), mask_soft)
    else:
        solid_color = ImageColor.getrgb(text_color)
        solid = Image.new("RGBA", (width, height), solid_color)
        base_image.paste(solid, (0, 0), mask_crisp)

    # --------------------------------------------------------
    # 7. Outline (tight, crisp, semi-transparent)
    # --------------------------------------------------------
    if outline_size > 0 and outline_color:
        radius = int(round(outline_size))

        if radius > 0:
            expanded = Image.new("L", (width, height), 0)

            offsets = [
                (dx, dy)
                for dx in range(-radius, radius + 1)
                for dy in range(-radius, radius + 1)
                if dx * dx + dy * dy <= radius * radius
            ]

            for dx, dy in offsets:
                expanded.paste(mask_crisp, (dx, dy), mask_crisp)

            outline = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            oc = ImageColor.getrgb(outline_color)
            op = outline.load()
            ep = expanded.load()

            for y in range(height):
                for x in range(width):
                    a = ep[x, y]
                    if a > 0:
                        a_scaled = int(a * 0.5)
                        op[x, y] = oc + (a_scaled,)

            base_image = Image.alpha_composite(outline, base_image)

    # --------------------------------------------------------
    # 8. Glow
    # --------------------------------------------------------
    if glow_size > 0 and glow_color:
        radius = max(1.0, float(glow_size))
        blurred = mask_crisp.filter(ImageFilter.GaussianBlur(radius=radius))

        intensity = glow_intensity if glow_intensity > 0 else min(3.0, size / 60.0)

        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gc = ImageColor.getrgb(glow_color)
        gp = glow.load()
        bp = blurred.load()

        for y in range(height):
            for x in range(width):
                a = bp[x, y]
                if a > 0:
                    a_scaled = int(max(0, min(255, a * intensity)))
                    gp[x, y] = gc + (a_scaled,)

        base_image.alpha_composite(glow)

    # --------------------------------------------------------
    # 9. Crop to true alpha bounds
    # --------------------------------------------------------
    bbox = base_image.getbbox()
    if bbox:
        expand = int(glow_size * 2) if glow_size > 0 else 0
        x0, y0, x1, y1 = bbox
        x0 = max(0, x0 - expand)
        y0 = max(0, y0 - expand)
        x1 = min(width, x1 + expand)
        y1 = min(height, y1 + expand)
        base_image = base_image.crop((x0, y0, x1, y1))

    return base_image


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/ping", response_class=PlainTextResponse)
def ping():
    return "pong"


@app.get("/render")
def render(
    text: str = Query("Hello"),
    font: str = Query("/fonts/Pacifico-Regular.ttf"),
    size: int = Query(120),
    textColor: str = Query("#000000"),
    gradientType: str = Query("none"),
    gradientColors: str = Query("[]"),
    transparent: bool = Query(False),
    backgroundColor: str = Query("#ffffff"),
    glowColor: Optional[str] = Query(None),
    glowSize: float = Query(0.0),
    glowIntensity: float = Query(0.0),
    outlineColor: Optional[str] = Query(None),
    outlineSize: float = Query(0.0),
):
    # Handle empty text safely
    if not text:
        empty = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        buf = io.BytesIO()
        empty.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    # Parse gradient colors
    try:
        colors = json.loads(gradientColors)
        if not isinstance(colors, list):
            colors = []
    except Exception:
        colors = []
    colors = [str(c) for c in colors if c]

    # Normalize empty strings to None for colors
    if not glowColor:
        glowColor = None
    if not outlineColor:
        outlineColor = None

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

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
