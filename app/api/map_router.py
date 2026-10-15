from fastapi import APIRouter, Query, Response
from app.services.map_service import render_map_tile

router = APIRouter()


@router.get("/tile")
@router.get("/map_image")
async def get_map_tile(
        lat: float = Query(...),
        lon: float = Query(...),
        end_lat: float = Query(None),
        end_lon: float = Query(None),
        dest_lat: float = Query(None),
        dest_lon: float = Query(None),
        zoom: int = Query(16),
        width: int = Query(320),
        height: int = Query(240)
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
    return Response(content=img_bytes, media_type="image/jpeg")