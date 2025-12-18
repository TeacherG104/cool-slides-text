from fastapi import FastAPI, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, json, math

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Font map
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
                      glow_color: str = None, glow_size: int = 0,
                      outline_color: str = None, outline_size: int = 0,
                      gradient_colors=None, gradient_type="vertical"):
    font_obj = load_font(font_name, size)
    width, height = 600, 200
    mask = Image.new("L",(width,height),0)
    draw = ImageDraw.Draw(mask)
    bbox = draw.textbbox((0,0), text, font=font_obj)
    x = (width-(bbox[2]-bbox[0]))//2
    y = (height-(bbox[3]-bbox[1]))//2
    draw.text((x,y), text, fill=255, font=font_obj)

    # Base image
    if gradient_colors:
        gradient = make_gradient(width,height,gradient_colors,gradient_type)
        img = Image.composite(gradient, Image.new("RGBA",(width,height),(255,255,255,0)), mask)
    else:
        img = Image.new("RGBA",(width,height),(255,255,255,0))
        ImageDraw.Draw(img).text((x,y), text, fill="#000000", font=font_obj)

    # Outline
    if outline_color and outline_size > 0:
        outline_img = Image.new("RGBA", img.size, (255,255,255,0))
        outline_draw = ImageDraw.Draw(outline_img)
        for dx in range(-outline_size, outline_size+1):
            for dy in range(-outline_size, outline_size+1):
                if dx!=0 or dy!=0:
                    outline_draw.text((x+dx,y+dy), text, font=font_obj, fill=outline_color)
        img = Image.alpha_composite(outline_img, img)

    # Glow
    if glow_color and glow_size > 0:
        glow_img = Image.new("RGBA", img.size, (255,255,255,0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((x,y), text, font=font_obj, fill=glow_color)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_size))
        img = Image.alpha_composite(img, glow_img)

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
    glowColor: str = Query(None),
    glowSize: int = Query(0),
    outlineColor: str = Query(None),
    outlineSize: int = Query(0),
    gradientType: str = Query("vertical"),
    gradientColors: str = Query(None)
):
    try:
        colors = json.loads(gradientColors) if gradientColors else None
        img = render_text_image(text, font, size,
                                glow_color=glowColor, glow_size=glowSize,
                                outline_color=outlineColor, outline_size=outlineSize,
                                gradient_colors=colors, gradient_type=gradientType)
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
        glow_color = payload.get("glowColor")
        glow_size = int(payload.get("glowSize", 0))
        outline_color = payload.get("outlineColor")
        outline_size = int(payload.get("outlineSize", 0))
        gradient_type = payload.get("gradientType", "vertical")
        gradient_colors = payload.get("gradientColors")

        img = render_text_image(text, font, size,
                                glow_color=glow_color, glow_size=glow_size,
                                outline_color=outline_color, outline_size=outline_size,
                                gradient_colors=gradient_colors, gradient_type=gradient_type)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
