from fastapi import FastAPI, Query, Body
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

def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))

def make_gradient(width, height, colors, gradient_type="vertical"):
    rgb_colors = [hex_to_rgb(c) for c in colors]
    gradient = Image.new("RGBA", (width, height))
    if gradient_type in ["vertical", "horizontal"]:
        steps = height if gradient_type=="vertical" else width
        for i in range(steps):
            ratio = i / steps
            idx = int(ratio * (len(rgb_colors)-1))
            c1, c2 = rgb_colors[idx], rgb_colors[min(idx+1, len(rgb_colors)-1)]
            local_ratio = (ratio * (len(rgb_colors)-1)) % 1
            r = int(c1[0]*(1-local_ratio) + c2[0]*local_ratio)
            g = int(c1[1]*(1-local_ratio) + c2[1]*local_ratio)
            b = int(c1[2]*(1-local_ratio) + c2[2]*local_ratio)
            if gradient_type=="vertical":
                ImageDraw.Draw(gradient).line([(0,i),(width,i)], fill=(r,g,b,255))
            else:
                ImageDraw.Draw(gradient).line([(i,0),(i,height)], fill=(r,g,b,255))
    elif gradient_type.startswith("slant"):
        for y in range(height):
            for x in range(width):
                ratio = (x+y)/(width+height) if "right" in gradient_type else (width-x+y)/(width+height)
                idx = int(ratio * (len(rgb_colors)-1))
                c1, c2 = rgb_colors[idx], rgb_colors[min(idx+1, len(rgb_colors)-1)]
                local_ratio = (ratio * (len(rgb_colors)-1)) % 1
                r = int(c1[0]*(1-local_ratio) + c2[0]*local_ratio)
                g = int(c1[1]*(1-local_ratio) + c2[1]*local_ratio)
                b = int(c1[2]*(1-local_ratio) + c2[2]*local_ratio)
                gradient.putpixel((x,y),(r,g,b,255))
    elif gradient_type=="radial":
        cx, cy = width//2, height//2
        max_dist = math.hypot(width, height)
        for y in range(height):
            for x in range(width):
                dist = math.hypot(x-cx, y-cy)
                ratio = dist/max_dist
                idx = int(ratio * (len(rgb_colors)-1))
                c1, c2 = rgb_colors[idx], rgb_colors[min(idx+1, len(rgb_colors)-1)]
                local_ratio = (ratio * (len(rgb_colors)-1)) % 1
                r = int(c1[0]*(1-local_ratio) + c2[0]*local_ratio)
                g = int(c1[1]*(1-local_ratio) + c2[1]*local_ratio)
                b = int(c1[2]*(1-local_ratio) + c2[2]*local_ratio)
                gradient.putpixel((x,y),(r,g,b,255))
    return gradient

def render_text_image(text: str, font_name: str, size: int,
                      text_color: str = "#000000",
                      gradient_colors=None, gradient_type="vertical",
                      transparent: bool = True, background_color: str = "#ffffff",
                      resize_to_text: bool = False,
                      glow_color: str = None, glow_size: int = 0, glow_intensity: float = 1.0,
                      outline_color: str = None, outline_size: float = 0.0):
    font_obj = load_font(font_name, size)

    # Measure text with extra padding to capture descenders
    tmp_img = Image.new("L", (1,1))
    tmp_draw = ImageDraw.Draw(tmp_img)
    bbox = tmp_draw.textbbox((0,0), text, font=font_obj)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    h += int(size * 0.3)  # extra vertical padding

    padding = size // 2
    width, height = w + padding*2, h + padding*2
    bg = (255,255,255,0) if transparent else hex_to_rgb(background_color) + (255,)
    img = Image.new("RGBA", (width, height), bg)

    x, y = padding, padding

    # Glow behind text
    if glow_color and glow_size > 0:
        glow_img = Image.new("RGBA", img.size, (255,255,255,0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((x,y), text, font=font_obj, fill=glow_color)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_size))
        alpha = glow_img.split()[3].point(lambda p: int(p*glow_intensity))
        glow_img.putalpha(alpha)
        base = Image.alpha_composite(img, glow_img)
        img = base

    # Gradient anchored to text bbox
    if gradient_colors and gradient_type != "none":
        gradient = make_gradient(w, h, gradient_colors, gradient_type)
        text_area = Image.new("RGBA", (w, h), (255,255,255,0))
        text_mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(text_mask).text((0,0), text, font=font_obj, fill=255)
        text_area = Image.composite(gradient, text_area, text_mask)
        img.paste(text_area, (x,y), text_area)
    else:
        ImageDraw.Draw(img).text((x,y), text, fill=text_color, font=font_obj)

    # Outline with finer control
    if outline_color and outline_size > 0:
        outline_img = Image.new("RGBA", img.size, (255,255,255,0))
        outline_draw = ImageDraw.Draw(outline_img)
        steps = int(outline_size)
        for dx in range(-steps, steps+1):
            for dy in range(-steps, steps+1):
                if dx!=0 or dy!=0:
                    outline_draw.text((x+dx,y+dy), text, font=font_obj, fill=outline_color)
        img = Image.alpha_composite(outline_img, img)

    # Resize background to text bounding box
    if resize_to_text:
        img = img.crop((x, y, x+w, y+h))

    return img

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
        gradient_colors = payload.get("gradientColors")  # expects list like ["#ff0000","#0000ff"]

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
