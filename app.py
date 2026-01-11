import io, os, math, json
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============================================================
# FASTAPI + CORS
# ============================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# FONT LOADING (Render-safe)
# ============================================================

def resolve_font_path(font_path: str) -> Optional[str]:
    """Convert /fonts/... to absolute path inside Render."""
    if font_path.startswith("/"):
        font_path = font_path[1:]
    abs_path = os.path.join(os.getcwd(), font_path)
    if not os.path.exists(abs_path):
        print(f"[FONT ERROR] Missing font: {abs_path}")
        return None
    return abs_path

def load_font(font_path: str, size: int):
    resolved = resolve_font_path(font_path)
    if resolved is None:
        print("[FONT WARNING] Using fallback font.")
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(resolved, size=size)
    except Exception as e:
        print(f"[FONT ERROR] Could not load font: {e}")
        return ImageFont.load_default()

# ============================================================
# COLOR + GRADIENT UTILITIES
# ============================================================

def hex_to_rgb(h: str):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def make_multi_stop_gradient(w: int, h: int, colors: List[str], gtype: str):
    stops = [hex_to_rgb(c) for c in colors]
    n = len(stops)
    img = Image.new("RGBA", (w, h))
    px = img.load()

    def interp(t):
        t = max(0, min(t, 1))
        i = int(t * (n - 1))
        f = t * (n - 1) - i
        c1, c2 = stops[i], stops[min(i + 1, n - 1)]
        return tuple(int(c1[j] + (c2[j] - c1[j]) * f) for j in range(3))

    for y in range(h):
        for x in range(w):
            if gtype == "horizontal":
                t = x / (w - 1)
            elif gtype == "vertical":
                t = y / (h - 1)
            elif gtype == "diagonal":
                t = (x + y) / (w + h - 2)
            elif gtype == "radial":
                cx, cy = w / 2, h / 2
                dist = math.hypot(x - cx, y - cy)
                maxd = math.hypot(cx, cy)
                t = dist / maxd
            else:
                t = x / (w - 1)
            px[x, y] = interp(t) + (255,)
    return img

# ============================================================
# RENDER ENGINE (Crisp/Soft + Safe Glow Padding)
# ============================================================

def render_text_image(
    text: str,
    font_path: str,
    size: int,
    text_color: str,
    gradient_type: str,
    gradient_colors: list,
    transparent: bool,
    background_color: str,
    glow_color: str,
    glow_size: float,
    glow_intensity: float,
    outline_color: str,
    outline_size: float,
):
    # ------------------------------------------------------------
    # 1. Load font
    # ------------------------------------------------------------
    font = ImageFont.truetype(font_path, size)

    # ------------------------------------------------------------
    # 2. Measure text
    # ------------------------------------------------------------
    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    text_w, text_h = x1 - x0, y1 - y0

    pad = max(20, int(size * 0.25))
    width = text_w + pad * 2
    height = text_h + pad * 2

    # ------------------------------------------------------------
    # 3. Create base image
    # ------------------------------------------------------------
    if transparent:
        base_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        bg = ImageColor.getrgb(background_color)
        base_image = Image.new("RGBA", (width, height), bg)

    # ------------------------------------------------------------
    # 4. Create crisp text mask
    # ------------------------------------------------------------
    text_mask = Image.new("L", (width, height), 0)
    md = ImageDraw.Draw(text_mask)
    md.text((pad, pad), text, font=font, fill=255)

    mask_crisp = text_mask  # no blur

    # ------------------------------------------------------------
    # 5. Create soft mask (gradient only)
    # ------------------------------------------------------------
    if gradient_type != "none":
        mask_soft = mask_crisp.filter(ImageFilter.GaussianBlur(radius=2))
    else:
        mask_soft = mask_crisp

    # ------------------------------------------------------------
    # 6. Apply gradient OR solid fill
    # ------------------------------------------------------------
    if gradient_type != "none":
        gradient_img = create_gradient_fill(
            width,
            height,
            gradient_type,
            gradient_colors
        )
        base_image.paste(gradient_img, (0, 0), mask_soft)
    else:
        solid = Image.new("RGBA", (width, height), text_color)
        base_image.paste(solid, (0, 0), mask_crisp)

    # ------------------------------------------------------------
    # 7. Outline (crisp)
    # ------------------------------------------------------------
    if outline_size > 0 and outline_color:
        outline_layer = create_outline_layer(
            mask_crisp,
            outline_color,
            outline_size
        )
        base_image.alpha_composite(outline_layer)

    # ------------------------------------------------------------
    # 8. Glow (crisp)
    # ------------------------------------------------------------
    if glow_size > 0 and glow_intensity > 0 and glow_color:
        glow_layer = create_glow_layer(
            mask_crisp,
            glow_color,
            glow_size,
            glow_intensity
        )
        base_image.alpha_composite(glow_layer)

    # ------------------------------------------------------------
    # 9. Return final image
    # ------------------------------------------------------------
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
    # Handle empty text safely (preview typing, etc.)
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
    except:
        colors = []
    colors = [str(c) for c in colors if c]

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
