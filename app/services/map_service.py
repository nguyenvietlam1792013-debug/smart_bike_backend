import math
import io
import httpx
from PIL import Image, ImageDraw


def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def tile_to_latlon(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


async def render_map_tile(lat: float, lon: float, end_lat: float = None, end_lon: float = None, zoom: int = 16,
                          width: int = 320, height: int = 240) -> bytes:
    xtile, ytile = latlon_to_tile(lat, lon, zoom)

    # Tính vị trí tâm điểm trong tile
    nw_lat, nw_lon = tile_to_latlon(xtile, ytile, zoom)
    se_lat, se_lon = tile_to_latlon(xtile + 1, ytile + 1, zoom)

    px = int((lon - nw_lon) / (se_lon - nw_lon) * 256)
    py = int((lat - nw_lat) / (se_lat - nw_lat) * 256)

    # Tải tile bản đồ chính từ OpenStreetMap
    tile_url = f"https://tile.openstreetmap.org/{zoom}/{xtile}/{ytile}.png"
    headers = {"User-Agent": "SmartBikeApp/1.0"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(tile_url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                base_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            else:
                base_img = Image.new("RGB", (256, 256), color=(40, 40, 40))
    except Exception:
        base_img = Image.new("RGB", (256, 256), color=(40, 40, 40))

    # Cắt xới theo kích thước mong muốn (width, height)
    crop_x1 = max(0, px - width // 2)
    crop_y1 = max(0, py - height // 2)

    # Render canvas chính
    canvas = Image.new("RGB", (width, height), color=(30, 30, 30))
    canvas.paste(base_img, (-crop_x1, -crop_y1))

    draw = ImageDraw.Draw(canvas)

    # Vẽ vị trí GPS hiện tại (Chấm đỏ)
    center_x = px - crop_x1
    center_y = py - crop_y1
    r = 6
    draw.ellipse((center_x - r, center_y - r, center_x + r, center_y + r), fill=(255, 0, 0), outline=(255, 255, 255),
                 width=2)

    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=85)
    return output.getvalue()