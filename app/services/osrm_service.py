import httpx
from app.core.config import settings
from app.schemas.navigation import RouteResponse, StepInstruction

def get_cyd_icon_id(m_type: str, m_modifier: str) -> int:
    """Ánh xạ maneuver từ OSRM sang ID số nguyên cho ESP32 CYD"""
    if m_type == "arrive": return 7
    if "uturn" in m_modifier: return 6
    if "sharp left" in m_modifier: return 5
    if "sharp right" in m_modifier: return 4
    if "left" in m_modifier: return 3
    if "right" in m_modifier: return 2
    return 1 # Mặc định đi thẳng

async def get_route_from_osrm(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> RouteResponse:
    url = f"{settings.OSRM_BASE_URL}/route/v1/biking/{start_lon},{start_lat};{end_lon},{end_lat}?steps=true&overview=false"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            if response.status_code != 200:
                return RouteResponse(status="error_osrm_server", total_distance_m=0, total_duration_s=0, next_step=None, all_steps=[])

            data = response.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                return RouteResponse(status="no_route_found", total_distance_m=0, total_duration_s=0, next_step=None, all_steps=[])

            route = data["routes"][0]
            total_distance = route.get("distance", 0.0)
            total_duration = route.get("duration", 0.0)

            steps_list = []
            legs = route.get("legs", [])
            if legs:
                for step in legs[0].get("steps", []):
                    maneuver = step.get("maneuver", {})
                    m_type = maneuver.get("type", "unknown")
                    m_modifier = maneuver.get("modifier", "none")
                    step_name = step.get("name", "Đường không tên")

                    icon_id = get_cyd_icon_id(m_type, m_modifier)

                    steps_list.append(StepInstruction(
                        instruction=f"{m_type} {m_modifier}".strip(),
                        icon_id=icon_id,
                        type=m_type,
                        modifier=m_modifier,
                        distance=round(step.get("distance", 0.0), 1),
                        name=step_name
                    ))

            next_step = steps_list[1] if len(steps_list) > 1 else (steps_list[0] if steps_list else None)

            return RouteResponse(
                status="success",
                total_distance_m=round(total_distance, 1),
                total_duration_s=round(total_duration, 1),
                next_step=next_step,
                all_steps=steps_list
            )
        except Exception as e:
            return RouteResponse(status=f"error: {str(e)}", total_distance_m=0, total_duration_s=0, next_step=None, all_steps=[])