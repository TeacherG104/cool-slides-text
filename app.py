import io, os, math, json
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont, ImageFilter

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ------------------------------------------------------------
# FONT LOADING
# ------------------------------------------------------------
def resolve_font_path(font_path: str) -> str:
    if font_path.startswith("/"):
        font_path = font_path[1:]
    abs_path = os.path.join(os.getcwd(), font_path)
    if not os.path.exists(abs_path):
        print(f"[FONT ERROR] Font not found: {abs_path}")
        return None
    return abs_path

def load_font(font_path: str, size: int):
    resolved = resolve_font_path(font_path)
    if resolved is None:
        print("[FONT WARNING] Falling back to default font.")
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(resolved, size=size)
    except Exception as e:
        print(f"[FONT ERROR] Could not load font: {e}")
        return ImageFont.load_default()

# ------------------------------------------------------------
# COLOR + GRADIENT UTILS
# ------------------------------------------------------------
def hex_to_rgb(hex_color: str):
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def make_multi_stop_gradient(w: int, h: int, colors: List[str], gradient_type: str):
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
            if gradient_type == "horizontal":
                t = x / (w - 1)
            elif gradient_type == "vertical":
                t = y / (h - 1)
            elif gradient_type == "diagonal":
                t = (x + y) / (w + h - 2)
            elif gradient_type == "radial":
                cx, cy = w / 2, h / 2
                dist = math.hypot(x - cx, y - cy)
                maxd = math.hypot(cx, cy)
                t = dist / maxd
            else:
                t = x / (w - 1)
            px[x, y] = interp(t) + (255,)
    return img

# ------------------------------------------------------------
# RENDER ENGINE
# ------------------------------------------------------------
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
    font = load_font(font_path, size)
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = max(int(glow_size * 2), int(outline_size * 2), 20)
    W, H = tw + pad * 2, th + pad * 2
    x, y = pad, pad
    bg = (0, 0, 0, 0) if transparent else hex_to_rgb(background_color) + (255,)
    img = Image.new("RGBA", (W, H), bg)

    # GLOW
    if glow_color and glow_size > 0 and glow_intensity > 0:
        base_mask = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(base_mask)
        d.text((x, y), text, font=font, fill=255)
        radii = [glow_size * 0.25, glow_size * 0.6, glow_size]
        alphas = [int(255 * glow_intensity), int(255 * glow_intensity * 0.6), int(255 * glow_intensity * 0.3)]
        for r, a in zip(radii, alphas):
            blur = base_mask.filter(ImageFilter.GaussianBlur(r))
            layer = Image.new("RGBA", (W, H), hex_to_rgb(glow_color) + (0,))
            layer.putalpha(blur.point(lambda p: min(p, a)))
            img = Image.alpha_composite(img, layer)

    # OUTLINE
    if outline_color and outline_size > 0:
        outline_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(outline_img)
        steps = int(outline_size)
        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                if dx != 0 or dy != 0:
                    od.text((x + dx, y + dy), text, font=font, fill=outline_color)
        img = Image.alpha_composite(img, outline_img)

    # TEXT FILL
    d = ImageDraw.Draw(img)
    if gradient_type != "none" and gradient_colors:
        gx0, gy0, gx1, gy1 = d.textbbox((x, y), text, font=font)
        gw, gh = gx1 - gx0, gy1 - gy0
        gradient = make_multi_stop_gradient(gw, gh, gradient_colors, gradient_type)
        mask = Image.new("L", (gw, gh), 0)
        md = ImageDraw.Draw(mask)
        md.text((0, 0), text, font=font, fill=255)
        img.paste(gradient, (gx0, gy0), mask)
    else:
        d.text((x, y), text, font=font, fill=text_color)

    return img

# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------
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
    gradientColors: str = Query("[]"),
    transparent: bool = Query(False),
    backgroundColor: str = Query("#000000"),
    glowColor: Optional[str] = Query(None),
    glowSize: float = Query(0.0),
    glowIntensity: float = Query(0.0),
    outlineColor: Optional[str] = Query(None),
    outlineSize: float = Query(0.0),
):
    try:
        colors = json.loads(gradientColors)
        if not isinstance(colors, list): colors = []
    except: colors = []
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
