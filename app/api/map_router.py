from typing import Optional
from fastapi import APIRouter, Query, Response
from app.services.map_service import render_map_tile, get_cache_stats

router = APIRouter()


@router.get("/tile", summary="Lấy ảnh tile bản đồ (JPEG) cho màn hình xe đạp ESP32 CYD")
@router.get("/map_image", summary="Alias lấy ảnh bản đồ (hỗ trợ backward compatibility)")
async def get_map_tile(
    lat: float = Query(..., description="Vĩ độ hiện tại của xe đạp"),
    lon: float = Query(..., description="Kinh độ hiện tại của xe đạp"),
    end_lat: Optional[float] = Query(None, description="Vĩ độ điểm đến"),
    end_lon: Optional[float] = Query(None, description="Kinh độ điểm đến"),
    dest_lat: Optional[float] = Query(None, description="Alias cho end_lat"),
    dest_lon: Optional[float] = Query(None, description="Alias cho end_lon"),
    zoom: int = Query(16, ge=1, le=19, description="Mức phóng to bản đồ (mặc định 16)"),
    width: int = Query(320, ge=64, le=800, description="Chiều rộng khung ảnh (mặc định 320)"),
    height: int = Query(240, ge=64, le=600, description="Chiều cao khung ảnh (mặc định 240)")
):
    target_end_lat = end_lat if end_lat is not None else dest_lat
    target_end_lon = end_lon if end_lon is not None else dest_lon

    img_bytes = await render_map_tile(
        lat=lat,
        lon=lon,
        end_lat=target_end_lat,
        end_lon=target_end_lon,
        zoom=zoom,
        width=width,
        height=height
    )

    return Response(
        content=img_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=60",
            "Content-Disposition": "inline; filename=map_tile.jpg"
        }
    )


@router.get("/cache/stats", summary="Thống kê trạng thái bộ nhớ đệm tile OSM")
async def cache_stats():
    return await get_cache_stats()