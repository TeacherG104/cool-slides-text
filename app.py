from fastapi import FastAPI, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

app = FastAPI()

# Enable CORS so sidebar JS can call endpoints directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # during development allow all; later restrict to Google domains if desired
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Map sidebar font keys to actual .ttf files in your repo
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
            print(f"Trying to load font: {path}")  # helpful debug log
            return ImageFont.truetype(path, size)
        except Exception as e:
            print(f"Font load failed: {e}")
            return ImageFont.load_default()
    return ImageFont.load_default()

def render_text_image(text: str, color: str, font_name: str,
                      glow_color: str = None, glow_size: int = 0,
                      outline_color: str = None, outline_size: int = 0):
    font_obj = load_font(font_name, 64)
    width, height = 600, 200
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font_obj)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (width - w) // 2
    y = (height - h) // 2

    # Outline effect: draw text multiple times around the main position
    if outline_color and outline_size > 0:
        for dx in range(-outline_size, outline_size + 1):
            for dy in range(-outline_size, outline_size + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font_obj, fill=outline_color)

    # Glow effect: draw blurred background text
    if glow_color and glow_size > 0:
        glow_img = Image.new("RGBA", img.size, (255, 255, 255, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((x, y), text, font=font_obj, fill=glow_color)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_size))
        img = Image.alpha_composite(img, glow_img)

    # Main text
    draw.text((x, y), text, font=font_obj, fill=color)

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
    color: str = Query("#000000"),
    font: str = Query("Arial"),
    glowColor: str = Query(None),
    glowSize: int = Query(0),
    outlineColor: str = Query(None),
    outlineSize: int = Query(0)
):
    try:
        img = render_text_image(text, color, font,
                                glow_color=glowColor, glow_size=glowSize,
                                outline_color=outlineColor, outline_size=outlineSize)
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
        color = payload.get("color", "#000000")
        font = payload.get("font", "Arial")
        glow_color = payload.get("glowColor")
        glow_size = int(payload.get("glowSize", 0))
        outline_color = payload.get("outlineColor")
        outline_size = int(payload.get("outlineSize", 0))

        img = render_text_image(text, color, font,
                                glow_color=glow_color, glow_size=glow_size,
                                outline_color=outline_color, outline_size=outline_size)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
