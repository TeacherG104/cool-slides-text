from fastapi import FastAPI, Query, Body, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, json, math

app = FastAPI()

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

def make_gradient(width, height, colors, gradient_type="vertical"):
    rgb_colors = [hex_to_rgb(c) for c in colors]
    gradient = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(gradient)

    if gradient_type in ["vertical", "horizontal"]:
        steps = height if gradient_type == "vertical" else width
        for i in range(steps):
            ratio = i / steps
            idx = int(ratio * (len(rgb_colors) - 1))
            c1, c2 = rgb_colors[idx], rgb_colors[min(idx + 1, len(rgb_colors) - 1)]
            local_ratio = (ratio * (len(rgb_colors) - 1)) % 1
            r = int(c1[0] * (1 - local_ratio) + c2[0] * local_ratio)
            g = int(c1[1] * (1 - local_ratio) + c2[1] * local_ratio)
            b = int(c1[2] * (1 - local_ratio) + c2[2] * local_ratio)

            if gradient_type == "vertical":
                draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
            else:
                draw.line([(i, 0), (i, height)], fill=(r, g, b, 255))

    elif gradient_type.startswith("slant"):
        for y in range(height):
            for x in range(width):
                ratio = (x + y) / (width + height) if "right" in gradient_type else (width - x + y) / (width + height)
                idx = int(ratio * (len(rgb_colors) - 1))
                c1, c2 = rgb_colors[idx], rgb_colors[min(idx + 1, len(rgb_colors) - 1)]
                local_ratio = (ratio * (len(rgb_colors) - 1)) % 1
                r = int(c1[0] * (1 - local_ratio) + c2[0] * local_ratio)
                g = int(c1[1] * (1 - local_ratio) + c2[1] * local_ratio)
                b = int(c1[2] * (1 - local_ratio) + c2[2] * local_ratio)
                gradient.putpixel((x, y), (r, g, b, 255))

    elif gradient_type == "radial":
        cx, cy = width // 2, height // 2
        max_dist = math.hypot(width, height)
        for y in range(height):
            for x in range(width):
                dist = math.hypot(x - cx, y - cy)
                ratio = dist / max_dist
                idx = int(ratio * (len(rgb_colors) - 1))
                c1, c2 = rgb_colors[idx], rgb_colors[min(idx + 1, len(rgb_colors) - 1)]
                local_ratio = (ratio * (len(rgb_colors) - 1)) % 1
                r = int(c1[0] * (1 - local_ratio) + c2[0] * local_ratio)
                g = int(c1[1] * (1 - local_ratio) + c2[1] * local_ratio)
                b = int(c1[2] * (1 - local_ratio) + c2[2] * local_ratio)
                gradient.putpixel((x, y), (r, g, b, 255))

    return gradient

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

    # --- GLOW (mask-based, correct) ---
    if glow_color and glow_size > 0:
        # 1. Create a mask (white text on black)
        glow_mask = Image.new("L", img.size, 0)
        mask_draw = ImageDraw.Draw(glow_mask)
        mask_draw.text((x, y), text, font=font_obj, fill=255)
    
        # 2. Blur the mask
        glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(radius=glow_size))
    
        # 3. Create a colored glow layer
        glow_layer = Image.new("RGBA", img.size, hex_to_rgb(glow_color) + (0,))
        glow_layer.putalpha(glow_mask)
    
        # 4. Composite glow onto the base image
        img = Image.alpha_composite(img, glow_layer)
    # --- OUTLINE ---
    if outline_color and outline_size > 0:
        outline_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(outline_img)
        steps = int(outline_size)

        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                if dx != 0 or dy != 0:
                    od.text((x + dx, y + dy), text, font=font_obj, fill=outline_color)

        img = Image.alpha_composite(img, outline_img)

    # --- TEXT FILL ---
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

    elif glow_color and glow_size > 0 and outline_color is None:
        pass  # glow-only mode

    else:
        ImageDraw.Draw(img).text((x, y), text, fill=text_color, font=font_obj)

    # --- BACKGROUND LAST ---
    if not transparent:
        bg = Image.new("RGBA", img.size, hex_to_rgb(background_color) + (255,))
        img = Image.alpha_composite(bg, img)

    # --- RESIZE ---
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
    return Response(content=buf.getvalue(), media_type="image/png")

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
    return Response(content=buf.getvalue(), media_type="image/png")

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
        colors = json.loads(gradientColors) if gradientColors else None
        img = render_text_image(
            text, font, size,
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

        img = render_text_image(
            text, font, size,
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
