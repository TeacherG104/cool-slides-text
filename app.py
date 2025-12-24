print(">>> THIS IS THE NEW DEPLOYED VERSION <<<")

from fastapi import FastAPI, Query, Body, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, json, math, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Serve the fonts directory
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Serve the fonts folder
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FONT_MAP = {
    "henny": "fonts/HennyPenny-Regular.ttf",
    "honk": "fonts/Honk-Regular-VariableFont_MORF,SHLN.ttf",
    "metamorphous": "fonts/Metamorphous-Regular.ttf",
    "monoton": "fonts/Monoton-Regular.ttf",
    "moolahlah": "fonts/MooLahLah-Regular.ttf",
    "mysteryquest": "fonts/MysteryQuest-Regular.ttf",
    "nabla": "fonts/Nabla-Regular-VariableFont_EDPT,EHLT.ttf",
    "pacifico": "fonts/Pacifico-Regular.ttf",
    "transformers": "fonts/Transformers Movie.ttf",
    "uncial": "fonts/UncialAntiqua-Regular.ttf",
}

def load_font(font_name: str, size: int = 64):
    path = FONT_MAP.get(font_name.lower())
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception as e:
            print(f"Font load failed: {e}")
            return ImageFont.load_default()
    return ImageFont.load_default()

def hex_to_rgb(value: str):
    if not value:
        return (255, 255, 255)

    value = value.strip().lstrip('#')

    # Expand shorthand hex (#fff → #ffffff)
    if len(value) == 3:
        value = ''.join(c*2 for c in value)

    # Must be exactly 6 characters now
    if len(value) != 6:
        return (255, 255, 255)

    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return (r, g, b)

def make_gradient(w, h, colors, gtype):
    c1 = hex_to_rgb(colors[0])
    c2 = hex_to_rgb(colors[1])

    grad = Image.new("RGBA", (w, h))
    px = grad.load()

    if gtype == "horizontal":
        for x in range(w):
            t = x / (w - 1)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            for y in range(h):
                px[x, y] = (r, g, b, 255)

    elif gtype == "vertical":
        for y in range(h):
            t = y / (h - 1)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            for x in range(w):
                px[x, y] = (r, g, b, 255)

    elif gtype == "diagonal":
        for x in range(w):
            for y in range(h):
                t = (x + y) / (w + h - 2)
                r = int(c1[0] * (1 - t) + c2[0] * t)
                g = int(c1[1] * (1 - t) + c2[1] * t)
                b = int(c1[2] * (1 - t) + c2[2] * t)
                px[x, y] = (r, g, b, 255)

    elif gtype == "radial":
        cx, cy = w / 2, h / 2
        maxd = math.sqrt(cx * cx + cy * cy)
        for x in range(w):
            for y in range(h):
                dx = x - cx
                dy = y - cy
                d = math.sqrt(dx * dx + dy * dy)
                t = min(1.0, d / maxd)
                r = int(c1[0] * (1 - t) + c2[0] * t)
                g = int(c1[1] * (1 - t) + c2[1] * t)
                b = int(c1[2] * (1 - t) + c2[2] * t)
                px[x, y] = (r, g, b, 255)

    return grad

def render_text_image(
    text: str,
    font_name: str,
    size: int,
    text_color: str = "#000000",
    gradient_colors=None,
    gradient_type: str = "vertical",
    transparent: bool = True,
    background_color: str = "#ffffff",
    glow_color: str = None,
    glow_size: int = 0,
    glow_intensity: float = 1.0,
    outline_color: str = None,
    outline_size: float = 0.0,
    resize_to_text: bool = False
):
    print("START RENDER")

    # Debug params
    print(
        "PARAMS:",
        "text_color=", text_color,
        "gradient_colors=", gradient_colors,
        "gradient_type=", gradient_type,
        "transparent=", transparent,
        "background_color=", background_color,
        "glow_color=", glow_color,
        "glow_size=", glow_size,
        "glow_intensity=", glow_intensity,
        "outline_color=", outline_color,
        "outline_size=", outline_size,
        "resize_to_text=", resize_to_text
    )

    # Load font
    font_obj = ImageFont.truetype(font_name, size)

    # Measure text
    tmp = Image.new("L", (1, 1))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=font_obj)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    h += int(size * 0.3)

    padding = size // 2
    width, height = w + padding * 2, h + padding * 2
    x, y = padding, padding

    # Transparent base
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # ---------------------------------------------------------
    # 1. OUTLINE FIRST
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
    # 2. TEXT FILL (GRADIENT OR SOLID)
    # ---------------------------------------------------------
    if gradient_colors and gradient_type != "none":
        gradient = make_gradient(w, h, gradient_colors, gradient_type)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).text((0, 0), text, font=font_obj, fill=255)

        text_area = Image.composite(
            gradient,
            Image.new("RGBA", (w, h), (255, 255, 255, 0)),
            mask
        )
        img.paste(text_area, (x, y), text_area)

    else:
        # Normal solid text fill
        ImageDraw.Draw(img).text((x, y), text, fill=text_color, font=font_obj)

   # ---------------------------------------------------------
    # 3. MULTI-LAYER GLOW (FALLOFF)
    # ---------------------------------------------------------
    if glow_color and glow_size > 0:
        print(">>> MULTI-LAYER GLOW <<<")
    
        glow_layers = []
        base_mask = Image.new("L", img.size, 0)
        mask_draw = ImageDraw.Draw(base_mask)
        mask_draw.text((x, y), text, font=font_obj, fill=255)
    
        # Three blur radii for falloff
        radii = [
            glow_size * 0.25,
            glow_size * 0.6,
            glow_size
        ]
    
        # Corresponding opacities
        alphas = [
            int(255 * glow_intensity * 1.0),
            int(255 * glow_intensity * 0.6),
            int(255 * glow_intensity * 0.3)
        ]
    
        for r, a in zip(radii, alphas):
            blurred = base_mask.filter(ImageFilter.GaussianBlur(radius=r))
            layer = Image.new("RGBA", img.size, hex_to_rgb(glow_color) + (0,))
            layer.putalpha(blurred.point(lambda p: min(p, a)))
            glow_layers.append(layer)
    
        # Composite glow layers under text
        for g in glow_layers:
            img = Image.alpha_composite(img, g)
    # ---------------------------------------------------------
    # 4. BACKGROUND (if not transparent)
    # ---------------------------------------------------------
    if not transparent:
        bg = Image.new("RGBA", img.size, hex_to_rgb(background_color) + (255,))
        img = Image.alpha_composite(bg, img)

    # ---------------------------------------------------------
    # 5. RESIZE (optional)
    # ---------------------------------------------------------
    if resize_to_text:
        pad = glow_size * 2 + outline_size * 2
        img = img.crop((x - pad, y - pad, x + w + pad, y + h + pad))

    print("END RENDER")
    return img
@app.get("/test")
def test():
    img = render_text_image(
        text="TEST",
        font_name="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        size=120,
        text_color="#ffffff",
        gradient_colors=["#ff0000", "#8000ff"],
        gradient_type="vertical",
        transparent=False,
        background_color="#000000",
        glow_color="#00ffff",
        glow_size=5,
        glow_intensity=1.0,
        outline_color="#ffffff",
        outline_size=6,
        resize_to_text=False
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(
    content=buf.getvalue(),
    media_type="image/png",
    headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
)

@app.get("/testGlow")
def test_glow():
    # Generate glow-only version of the text
    img = render_text_image(
        text="GLOW",
        font_name="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        size=160,
        text_color="#000000",          # ignored because no text fill
        gradient_colors=None,          # no gradient
        gradient_type="none",
        transparent=True,              # keep transparent so glow is visible
        background_color="#000000",    # ignored because transparent=True
        glow_color="#00ffff",          # bright cyan glow
        glow_size=10,                  # large halo for visibility
        glow_intensity=1.0,
        outline_color=None,            # no outline
        outline_size=0,
        resize_to_text=False           # keep full canvas so glow isn't clipped
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.get("/fonttest")
def fonttest():
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 120)
        print("FONT OK:", f)
        return {"status": "font loaded"}
    except Exception as e:
        print("FONT ERROR:", e)
        return {"status": "font failed", "error": str(e)}

@app.get("/")
def root():
    return {"message": "Service is running"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/render")
def render_preview(
    text: str = Query(...),
    font: str = Query("Arial"),
    size: int = Query(64),
    textColor: str = Query("#000000"),
    glowColor: str = Query(None),
    glowSize: int = Query(0),
    glowIntensity: float = Query(1.0),
    outlineColor: str = Query(None),
    outlineSize: float = Query(0.0),
    gradientType: str = Query("vertical"),
    gradientColors: str = Query(None),
    transparent: bool = Query(True),
    backgroundColor: str = Query("#ffffff"),
    resizeToText: bool = Query(False)
):
    try:
        # Convert URL-style font path to local filesystem path
        font_path = font
        if font_path.startswith("/fonts/"):
            local_font = font_path.lstrip("/")  # remove leading slash
            font_path = os.path.join(BASE_DIR, local_font)

        colors = json.loads(gradientColors) if gradientColors else None

        img = render_text_image(
            text, font_path, size,
            text_color=textColor,
            glow_color=glowColor, glow_size=glowSize, glow_intensity=glowIntensity,
            outline_color=outlineColor, outline_size=outlineSize,
            gradient_colors=colors, gradient_type=gradientType,
            transparent=transparent, background_color=backgroundColor,
            resize_to_text=resizeToText
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/render")
def render_insert(payload: dict = Body(...)):
    try:
        text = payload.get("text", "")
        font = payload.get("font", "Arial")
        size = int(payload.get("size", 64))
        text_color = payload.get("textColor", "#000000")

        glow_color = payload.get("glowColor")
        glow_size = int(payload.get("glowSize", 0))
        glow_intensity = float(payload.get("glowIntensity", 1.0))

        outline_color = payload.get("outlineColor")
        outline_size = float(payload.get("outlineSize", 0.0))

        gradient_type = payload.get("gradientType", "vertical")
        gradient_colors = payload.get("gradientColors")

        transparent = bool(payload.get("transparent", True))
        background_color = payload.get("backgroundColor", "#ffffff")
        resize_to_text = bool(payload.get("resizeToText", False))

        # Convert URL-style font path to local filesystem path
        font_path = font
        if font_path.startswith("/fonts/"):
            local_font = font_path.lstrip("/")
            font_path = os.path.join(BASE_DIR, local_font)

        img = render_text_image(
            text, font_path, size,
            text_color=text_color,
            gradient_colors=gradient_colors, gradient_type=gradient_type,
            transparent=transparent, background_color=background_color,
            resize_to_text=resize_to_text,
            glow_color=glow_color, glow_size=glow_size, glow_intensity=glow_intensity,
            outline_color=outline_color, outline_size=outline_size
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
