from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from app.services.osrm_service import (
    get_route_from_osrm,
    get_cyd_route_from_osrm,
    OSRMConnectionError,
    OSRMTimeoutError,
    OSRMNoRouteError,
    OSRMServiceError,
    get_http_client
)
from app.schemas.navigation import RouteResponse, CYDRouteResponse
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=RouteResponse, summary="Tính toán lộ trình chi tiết cho Web Dashboard & Simulator")
async def get_route(
    start_lat: float = Query(..., description="Vĩ độ bắt đầu (GPS hiện tại) / Start latitude"),
    start_lon: float = Query(..., description="Kinh độ bắt đầu / Start longitude"),
    end_lat: float = Query(..., description="Vĩ độ điểm đến / End latitude"),
    end_lon: float = Query(..., description="Kinh độ điểm đến / End longitude"),
    profile: Optional[str] = Query(None, description="Profile định tuyến OSRM: 'driving' hoặc 'biking'"),
    lang: str = Query("vi", description="Ngôn ngữ câu chỉ dẫn: 'vi' (Tiếng Việt) hoặc 'en' (English)")
):
    try:
        return await get_route_from_osrm(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            profile=profile,
            lang=lang
        )
    except OSRMNoRouteError:
        msg = "No route found between points" if lang.lower().startswith("en") else "Không tìm thấy tuyến đường hợp lệ giữa hai vị trí này"
        return RouteResponse(
            status="error",
            total_distance_m=0.0,
            total_duration_s=0.0,
            message=msg,
            next_step=None,
            all_steps=[]
        )
    except OSRMConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{e.message}. Vui lòng kiểm tra container OSRM trên Docker."
        )
    except OSRMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=e.message
        )
    except OSRMServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/cyd", response_model=CYDRouteResponse, summary="Dữ liệu điều hướng JSON rút gọn (<200 bytes) cho ESP32 CYD")
async def get_route_cyd(
    start_lat: float = Query(..., description="Vĩ độ GPS hiện tại của xe đạp / Current GPS latitude"),
    start_lon: float = Query(..., description="Kinh độ GPS hiện tại của xe đạp / Current GPS longitude"),
    end_lat: float = Query(..., description="Vĩ độ điểm đích / Target destination latitude"),
    end_lon: float = Query(..., description="Kinh độ điểm đích / Target destination longitude"),
    profile: Optional[str] = Query(None, description="Profile OSRM tùy chọn / Optional routing profile"),
    lang: str = Query("vi", description="Ngôn ngữ câu chỉ dẫn: 'vi' (Tiếng Việt) hoặc 'en' (English)")
):
    try:
        return await get_cyd_route_from_osrm(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            profile=profile,
            lang=lang
        )
    except OSRMNoRouteError:
        msg = "No route found" if lang.lower().startswith("en") else "Không tìm thấy đường"
        return CYDRouteResponse(
            status="no_route",
            icon_id=1,
            step_dist=0.0,
            step_name="",
            step_instruction=msg,
            total_dist=0.0,
            total_time=0.0,
            next_icon_id=0,
            message=msg
        )
    except OSRMConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )
    except OSRMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=e.message
        )
    except OSRMServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health", summary="Kiểm tra trạng thái kết nối tới máy chủ OSRM")
async def check_osrm_health():
    client = get_http_client()
    try:
        test_url = f"{settings.OSRM_BASE_URL}/nearest/v1/{settings.DEFAULT_ROUTING_PROFILE}/105.8542,21.0285"
        resp = await client.get(test_url, timeout=2.0)
        osrm_ok = (resp.status_code == 200)
    except Exception:
        osrm_ok = False

    return {
        "status": "online" if osrm_ok else "osrm_offline",
        "osrm_base_url": settings.OSRM_BASE_URL,
        "default_profile": settings.DEFAULT_ROUTING_PROFILE,
        "connected": osrm_ok
    }