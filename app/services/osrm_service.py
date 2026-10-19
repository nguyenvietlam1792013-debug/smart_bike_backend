import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.schemas.navigation import RouteResponse, StepInstruction, CYDRouteResponse


class OSRMServiceError(Exception):
    """Lỗi chung từ OSRM Service"""
    def __init__(self, message: str, code: str = "OSRM_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class OSRMConnectionError(OSRMServiceError):
    """Không thể kết nối tới máy chủ OSRM"""
    def __init__(self, message: str = "Không thể kết nối tới dịch vụ OSRM (Port 5000)"):
        super().__init__(message, code="OSRM_CONNECTION_FAILED")


class OSRMTimeoutError(OSRMServiceError):
    """Yêu cầu OSRM bị quá thời gian chờ (timeout)"""
    def __init__(self, message: str = "Yêu cầu tính toán tuyến đường OSRM bị quá thời gian"):
        super().__init__(message, code="OSRM_TIMEOUT")


class OSRMNoRouteError(OSRMServiceError):
    """Không tìm thấy tuyến đường giữa 2 tọa độ"""
    def __init__(self, message: str = "Không tìm thấy tuyến đường hợp lệ giữa hai điểm"):
        super().__init__(message, code="ROUTE_NOT_FOUND")


# Singleton AsyncClient dùng chung để tận dụng Keep-Alive Connection Pool
_http_client: Optional[httpx.AsyncClient] = None
_client_loop = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client, _client_loop
    import asyncio
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _http_client is None or _http_client.is_closed or _client_loop != current_loop:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.OSRM_TIMEOUT_SECONDS, connect=3.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
        _client_loop = current_loop
    return _http_client


async def close_http_client():
    global _http_client, _client_loop
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
        _client_loop = None


def get_cyd_icon_id(m_type: str, m_modifier: str) -> int:
    """
    Ánh xạ maneuver từ OSRM sang ID số nguyên hiển thị trên ESP32 CYD:
    1 = Đi thẳng
    2 = Rẽ phải
    3 = Rẽ trái
    4 = Ngoặt phải (sharp right)
    5 = Ngoặt trái (sharp left)
    6 = Quay đầu (uturn)
    7 = Đến đích (arrive)
    """
    m_type = (m_type or "").lower()
    m_modifier = (m_modifier or "").lower()

    if m_type == "arrive":
        return 7
    if "uturn" in m_modifier:
        return 6
    if "sharp left" in m_modifier:
        return 5
    if "sharp right" in m_modifier:
        return 4
    if "left" in m_modifier:
        return 3
    if "right" in m_modifier:
        return 2
    return 1


def format_instruction(m_type: str, m_modifier: str, name: str, lang: str = "vi") -> str:
    """Tạo câu chỉ dẫn song ngữ / Generate bilingual turn instructions (VI & EN)"""
    m_type = (m_type or "").lower()
    m_modifier = (m_modifier or "").lower()
    has_name = bool(name and name.strip() and name not in ["Đường không tên", "Unnamed Road"])

    if lang.lower().startswith("en"):
        road_name = f" onto {name}" if has_name else ""
        if m_type == "arrive":
            return "Arrived at destination"
        if "uturn" in m_modifier:
            return f"Make a U-turn{road_name}"
        if "sharp left" in m_modifier:
            return f"Turn sharp left{road_name}"
        if "sharp right" in m_modifier:
            return f"Turn sharp right{road_name}"
        if "slight left" in m_modifier:
            return f"Keep slight left{road_name}"
        if "slight right" in m_modifier:
            return f"Keep slight right{road_name}"
        if "left" in m_modifier:
            return f"Turn left{road_name}"
        if "right" in m_modifier:
            return f"Turn right{road_name}"
        if m_type in ["roundabout", "rotary"]:
            return f"Enter the roundabout{road_name}"
        if m_type == "depart":
            return f"Head out{road_name}"
        return f"Continue straight{road_name}"
    else:
        road_name = f" vào {name}" if has_name else ""
        if m_type == "arrive":
            return "Đã đến điểm đích"
        if "uturn" in m_modifier:
            return f"Quay đầu xe{road_name}"
        if "sharp left" in m_modifier:
            return f"Ngoặt gấp sang trái{road_name}"
        if "sharp right" in m_modifier:
            return f"Ngoặt gấp sang phải{road_name}"
        if "slight left" in m_modifier:
            return f"Chếch sang trái{road_name}"
        if "slight right" in m_modifier:
            return f"Chếch sang phải{road_name}"
        if "left" in m_modifier:
            return f"Rẽ trái{road_name}"
        if "right" in m_modifier:
            return f"Rẽ phải{road_name}"
        if m_type in ["roundabout", "rotary"]:
            return f"Vào bùng binh{road_name}"
        if m_type == "depart":
            return f"Xuất phát{road_name}"
        return f"Đi thẳng{road_name}"


def format_instruction_vi(m_type: str, m_modifier: str, name: str) -> str:
    """Tương thích ngược với mã cũ"""
    return format_instruction(m_type, m_modifier, name, lang="vi")


async def fetch_osrm_raw(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: Optional[str] = None,
    overview: str = "full",
    geometries: str = "geojson",
    steps: bool = True
) -> Dict[str, Any]:
    """Gửi yêu cầu tới OSRM Server và xử lý ngoại lệ mạng"""
    active_profile = profile or settings.DEFAULT_ROUTING_PROFILE
    # OSRM định dạng tọa độ: {lon},{lat}
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/{active_profile}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview={overview}&geometries={geometries}&steps={'true' if steps else 'false'}"
    )

    client = get_http_client()
    try:
        resp = await client.get(url)
    except httpx.ConnectError:
        raise OSRMConnectionError()
    except httpx.TimeoutException:
        raise OSRMTimeoutError()
    except Exception as exc:
        raise OSRMServiceError(f"Lỗi kết nối OSRM: {str(exc)}")

    if resp.status_code == 400:
        try:
            err_data = resp.json()
            if err_data.get("code") in ["NoRoute", "NoSegment"]:
                raise OSRMNoRouteError(err_data.get("message", "Không tìm thấy tuyến đường hợp lệ giữa hai vị trí"))
            raise OSRMServiceError(f"OSRM từ chối yêu cầu: {err_data.get('message', 'Tọa độ không hợp lệ')}", code=err_data.get("code", "INVALID_QUERY"))
        except (ValueError, KeyError):
            pass

    if resp.status_code != 200:
        raise OSRMServiceError(f"OSRM trả về lỗi HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise OSRMNoRouteError()

    return data


async def get_route_from_osrm(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: Optional[str] = None,
    lang: str = "vi"
) -> RouteResponse:
    """Lấy dữ liệu lộ trình đầy đủ (kèm GeoJSON geometry) cho Web Leaflet và Simulator"""
    data = await fetch_osrm_raw(
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
        profile=profile,
        overview="full",
        geometries="geojson",
        steps=True
    )

    route = data["routes"][0]
    total_dist = route.get("distance", 0.0)
    total_duration = route.get("duration", 0.0)
    geometry = route.get("geometry")

    legs = route.get("legs", [])
    raw_steps = legs[0].get("steps", []) if legs else []

    parsed_steps: List[StepInstruction] = []
    default_road_name = "Unnamed Road" if lang.lower().startswith("en") else "Đường không tên"
    for step in raw_steps:
        maneuver = step.get("maneuver", {})
        m_type = maneuver.get("type", "unknown")
        m_modifier = maneuver.get("modifier", "")
        step_name = step.get("name") or default_road_name

        icon_id = get_cyd_icon_id(m_type, m_modifier)
        instruction_text = format_instruction(m_type, m_modifier, step_name, lang=lang)

        parsed_steps.append(StepInstruction(
            instruction=instruction_text,
            icon_id=icon_id,
            type=m_type,
            modifier=m_modifier,
            distance=round(step.get("distance", 0.0), 1),
            name=step_name
        ))

    # next_step cho giao diện: bước rẽ tiếp theo
    next_step = None
    if len(parsed_steps) > 1:
        next_step = parsed_steps[1]
    elif parsed_steps:
        next_step = parsed_steps[0]

    return RouteResponse(
        status="success",
        total_distance_m=round(total_dist, 1),
        total_duration_s=round(total_duration, 1),
        geometry=geometry,
        next_step=next_step,
        all_steps=parsed_steps
    )


async def get_cyd_route_from_osrm(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: Optional[str] = None,
    lang: str = "vi"
) -> CYDRouteResponse:
    """
    Trích xuất dữ liệu điều hướng siêu gọn nhẹ (< 200 bytes) tối ưu riêng cho ESP32 CYD.
    Tắt overview=false để giảm thiểu tải CPU và băng thông mạng.
    Hỗ trợ đa ngôn ngữ qua tham số lang ('vi' hoặc 'en').
    """
    data = await fetch_osrm_raw(
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
        profile=profile,
        overview="false",
        geometries="geojson",
        steps=True
    )

    route = data["routes"][0]
    total_dist = round(route.get("distance", 0.0), 1)
    total_time = round(route.get("duration", 0.0), 1)

    legs = route.get("legs", [])
    raw_steps = legs[0].get("steps", []) if legs else []

    is_en = lang.lower().startswith("en")

    if not raw_steps:
        return CYDRouteResponse(
            status="success",
            icon_id=1,
            step_dist=0.0,
            step_name="Calculating" if is_en else "Đang tính toán",
            step_instruction="Continue straight" if is_en else "Đi thẳng",
            total_dist=total_dist,
            total_time=total_time,
            next_icon_id=0
        )

    # Nếu có từ 2 bước trở lên: bước tiếp theo là raw_steps[1]
    if len(raw_steps) > 1:
        curr_step = raw_steps[0]
        target_step = raw_steps[1]
        maneuver = target_step.get("maneuver", {})
        m_type = maneuver.get("type", "turn")
        m_modifier = maneuver.get("modifier", "")
        step_name = target_step.get("name") or ("Next segment" if is_en else "Đoạn tiếp theo")

        # Khoảng cách đến khúc rẽ chính là quãng đường đi trên step hiện tại
        step_dist = round(curr_step.get("distance", 0.0), 1)
        if step_dist == 0.0:
            step_dist = round(target_step.get("distance", 0.0), 1)

        icon_id = get_cyd_icon_id(m_type, m_modifier)
        step_instruction = format_instruction(m_type, m_modifier, step_name, lang=lang)

        # Tính toán trước icon của bước kế tiếp sau đó
        next_icon_id = 0
        if len(raw_steps) > 2:
            next_m = raw_steps[2].get("maneuver", {})
            next_icon_id = get_cyd_icon_id(next_m.get("type", ""), next_m.get("modifier", ""))
        elif len(raw_steps) == 2:
            next_icon_id = 7  # Bước kế là đích
    else:
        # Chỉ có 1 bước (sắp tới đích)
        target_step = raw_steps[0]
        icon_id = 7
        step_dist = round(target_step.get("distance", 0.0), 1)
        step_name = target_step.get("name") or ("Destination" if is_en else "Điểm đến")
        step_instruction = "Approaching destination" if is_en else "Sắp đến điểm đích"
        next_icon_id = 7

    return CYDRouteResponse(
        status="success",
        icon_id=icon_id,
        step_dist=step_dist,
        step_name=step_name,
        step_instruction=step_instruction,
        total_dist=total_dist,
        total_time=total_time,
        next_icon_id=next_icon_id
    )