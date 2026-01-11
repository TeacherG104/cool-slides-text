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
# FONT LOADING (Render‑safe)
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
# RENDER ENGINE (Thin‑Font Optimized)
# ============================================================

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
):
    # Load font
    font = load_font(font_path, size)

    # Measure text
    tmp = Image.new("RGBA", (10, 10))
    dtmp = ImageDraw.Draw(tmp)
    bbox = dtmp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Padding
    pad = max(int(glow_size * 2), int(outline_size * 2), 20)
    W, H = tw + pad * 2, th + pad * 2
    x, y = pad, pad

    # Background
    bg = (0, 0, 0, 0) if transparent else hex_to_rgb(background_color) + (255,)
    img = Image.new("RGBA", (W, H), bg)

    # ============================================================
    # GLOW (behind everything)
    # ============================================================
    if glow_color and glow_size > 0 and glow_intensity > 0:
        base_mask = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(base_mask)
        d.text((x, y), text, font=font, fill=255)

        radii = [glow_size * 0.25, glow_size * 0.6, glow_size]
        alphas = [
            int(255 * glow_intensity),
            int(255 * glow_intensity * 0.6),
            int(255 * glow_intensity * 0.3),
        ]

        for r, a in zip(radii, alphas):
            blur = base_mask.filter(ImageFilter.GaussianBlur(r))
            layer = Image.new("RGBA", (W, H), hex_to_rgb(glow_color) + (0,))
            layer.putalpha(blur.point(lambda p: min(p, a)))
            img = Image.alpha_composite(img, layer)

    # ============================================================
    # OUTLINE (middle layer)
    # ============================================================
    if outline_color and outline_size > 0:
        outline_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(outline_img)

        # Thin‑font fix: clamp outline to 20% of font size
        max_outline = max(1, int(size * 0.20))
        steps = min(int(outline_size), max_outline)

        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                if dx != 0 or dy != 0:
                    od.text((x + dx, y + dy), text, font=font, fill=outline_color)

        img = Image.alpha_composite(img, outline_img)

        # ============================================================
        # TEXT FILL (top layer)
        # ============================================================
        d = ImageDraw.Draw(img)
    
        # Determine crisp vs soft mode based on outline usage
        outline_enabled = outline_color and outline_size > 0
    
        if gradient_type != "none" and gradient_colors:
            # Exact bbox
            gx0, gy0, gx1, gy1 = d.textbbox((x, y), text, font=font)
            gw, gh = gx1 - gx0, gy1 - gy0
    
            # If outline is ON → crisp mode (no expansion)
            # If outline is OFF → soft mode (expand mask)
            expand = 0 if outline_enabled else 2
    
            gw2, gh2 = gw + expand * 2, gh + expand * 2
    
            gradient = make_multi_stop_gradient(gw2, gh2, gradient_colors, gradient_type)
    
            # Mask
            mask = Image.new("L", (gw2, gh2), 0)
            md = ImageDraw.Draw(mask)
            md.text((expand, expand), text, font=font, fill=255)
    
            # Feather only when outline is OFF
            if not outline_enabled:
                mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    
            img.paste(gradient, (gx0 - expand, gy0 - expand), mask)
    
        else:
            # Solid color text (always crisp)
            d.text((x, y), text, font=font, fill=text_color)

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
    # ============================================================
    # SAFETY: handle empty text so preview never crashes
    # ============================================================
    if not text:
        empty = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        buf = io.BytesIO()
        empty.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    # Parse gradient colors safely
    try:
        colors = json.loads(gradientColors)
        if not isinstance(colors, list):
            colors = []
    except:
        colors = []
    colors = [str(c) for c in colors if c]

    # Render the text image
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

    # Return PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
