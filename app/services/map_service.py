import math
import io
import asyncio
from collections import OrderedDict
from typing import Optional, Tuple, Dict, Any
import httpx
from PIL import Image, ImageDraw
from app.core.config import settings

# Bộ nhớ đệm LRU cho các tile bản đồ OpenStreetMap
_TILE_CACHE: OrderedDict[Tuple[int, int, int], Image.Image] = OrderedDict()
_CACHE_LOCK = asyncio.Lock()
_MAX_CACHE_SIZE = settings.TILE_CACHE_MAXSIZE

# Singleton AsyncClient cho tải Map Tile
_map_http_client: Optional[httpx.AsyncClient] = None
_map_client_loop = None


def get_map_http_client() -> httpx.AsyncClient:
    global _map_http_client, _map_client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _map_http_client is None or _map_http_client.is_closed or _map_client_loop != current_loop:
        _map_http_client = httpx.AsyncClient(
            headers={"User-Agent": settings.TILE_USER_AGENT},
            timeout=httpx.Timeout(5.0, connect=2.5),
            limits=httpx.Limits(max_keepalive_connections=30, max_connections=50)
        )
        _map_client_loop = current_loop
    return _map_http_client


async def close_map_http_client():
    global _map_http_client, _map_client_loop
    if _map_http_client and not _map_http_client.is_closed:
        await _map_http_client.aclose()
        _map_http_client = None
        _map_client_loop = None


def latlon_to_global_pixels(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    """Chuyển đổi tọa độ GPS (lat, lon) thành tọa độ pixel toàn cầu tại mức zoom tương ứng"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    # Giới hạn vĩ độ Mercator tránh lỗi vô cực
    lat_rad = max(min(lat_rad, math.radians(85.05112878)), math.radians(-85.05112878))
    x = (lon + 180.0) / 360.0 * n * 256.0
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * 256.0
    return x, y


async def fetch_tile_image(zoom: int, xtile: int, ytile: int) -> Image.Image:
    """Lấy ảnh tile 256x256 từ LRU cache hoặc tải từ OpenStreetMap Server"""
    cache_key = (zoom, xtile, ytile)

    async with _CACHE_LOCK:
        if cache_key in _TILE_CACHE:
            # Di chuyển lên đầu danh sách LRU
            _TILE_CACHE.move_to_end(cache_key)
            return _TILE_CACHE[cache_key].copy()

    # Tải tile từ OSM nếu chưa có trong cache
    tile_url = f"https://tile.openstreetmap.org/{zoom}/{xtile}/{ytile}.png"
    client = get_map_http_client()
    try:
        resp = await client.get(tile_url)
        if resp.status_code == 200:
            tile_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        else:
            tile_img = Image.new("RGB", (256, 256), color=(40, 40, 40))
    except Exception:
        tile_img = Image.new("RGB", (256, 256), color=(40, 40, 40))

    async with _CACHE_LOCK:
        _TILE_CACHE[cache_key] = tile_img.copy()
        if len(_TILE_CACHE) > _MAX_CACHE_SIZE:
            # Xóa tile lâu nhất không dùng (FIFO trong LRU)
            _TILE_CACHE.popitem(last=False)

    return tile_img


async def render_map_tile(
    lat: float,
    lon: float,
    end_lat: Optional[float] = None,
    end_lon: Optional[float] = None,
    zoom: int = 16,
    width: int = 320,
    height: int = 240
) -> bytes:
    """
    Render ảnh bản đồ kích thước tùy chọn (mặc định 320x240 cho ESP32 CYD).
    Hệ thống tự động ghép các tile liền kề (multi-tile stitching) để hiển thị mượt mà
    không bị viền đen, và giữ vị trí xe đạp luôn ở chính giữa màn hình.
    """
    center_px_x, center_px_y = latlon_to_global_pixels(lat, lon, zoom)

    # Tọa độ góc trên bên trái của khung hình trên bản đồ toàn cầu
    x0 = center_px_x - (width / 2.0)
    y0 = center_px_y - (height / 2.0)

    # Xác định các tile cần thiết để phủ kín khung hình (thường là lưới 2x2)
    tx_start = int(math.floor(x0 / 256.0))
    tx_end = int(math.floor((x0 + width - 1) / 256.0))
    ty_start = int(math.floor(y0 / 256.0))
    ty_end = int(math.floor((y0 + height - 1) / 256.0))

    # Tải đồng thời tất cả các tile cần thiết
    tile_tasks = []
    tile_coords = []
    for ty in range(ty_start, ty_end + 1):
        for tx in range(tx_start, tx_end + 1):
            tile_coords.append((tx, ty))
            tile_tasks.append(fetch_tile_image(zoom, tx, ty))

    fetched_tiles = await asyncio.gather(*tile_tasks)

    # Tạo canvas và ghép các tile vào vị trí chính xác
    canvas = Image.new("RGB", (width, height), color=(30, 30, 30))
    for (tx, ty), tile_img in zip(tile_coords, fetched_tiles):
        paste_x = int(round(tx * 256.0 - x0))
        paste_y = int(round(ty * 256.0 - y0))
        canvas.paste(tile_img, (paste_x, paste_y))

    draw = ImageDraw.Draw(canvas)

    # Tọa độ tâm màn hình (vị trí hiện tại của xe đạp)
    center_x = width // 2
    center_y = height // 2

    # Nếu có điểm đến và nằm trong vùng hiển thị hoặc gần đó: vẽ điểm đích
    if end_lat is not None and end_lon is not None:
        dest_px_x, dest_px_y = latlon_to_global_pixels(end_lat, end_lon, zoom)
        dest_canvas_x = int(round(dest_px_x - x0))
        dest_canvas_y = int(round(dest_px_y - y0))

        # Nếu điểm đích nằm trong khung hình (hoặc lân cận trong 50px)
        if -50 <= dest_canvas_x <= width + 50 and -50 <= dest_canvas_y <= height + 50:
            # Vẽ đường nối định hướng từ vị trí xe đến điểm đích
            draw.line([(center_x, center_y), (dest_canvas_x, dest_canvas_y)], fill=(0, 102, 255), width=3)
            # Vẽ điểm đích (Chấm tròn xanh lá)
            r_dest = 7
            draw.ellipse(
                (dest_canvas_x - r_dest, dest_canvas_y - r_dest, dest_canvas_x + r_dest, dest_canvas_y + r_dest),
                fill=(40, 180, 40),
                outline=(255, 255, 255),
                width=2
            )

    # Vẽ vị trí xe hiện tại (Chấm đỏ nổi bật có viền trắng)
    r = 6
    draw.ellipse(
        (center_x - r, center_y - r, center_x + r, center_y + r),
        fill=(255, 30, 30),
        outline=(255, 255, 255),
        width=2
    )

    # Xuất ra dữ liệu JPEG chất lượng 85% để truyền tải nhanh qua Wi-Fi ESP32
    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=85)
    return output.getvalue()


async def get_cache_stats() -> Dict[str, Any]:
    """Thống kê trạng thái bộ nhớ đệm tile"""
    async with _CACHE_LOCK:
        return {
            "cached_tiles": len(_TILE_CACHE),
            "max_cache_size": _MAX_CACHE_SIZE
        }