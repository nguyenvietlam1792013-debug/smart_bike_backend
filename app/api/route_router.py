from fastapi import APIRouter, Query, HTTPException
import httpx

router = APIRouter()

OSRM_BASE_URL = "http://localhost:5000"


@router.get("")
async def get_route(
        start_lat: float = Query(..., description="Vĩ độ bắt đầu"),
        start_lon: float = Query(..., description="Kinh độ bắt đầu"),
        end_lat: float = Query(..., description="Vĩ độ điểm đến"),
        end_lon: float = Query(..., description="Kinh độ điểm đến")
):
    # Đổi profile từ 'biking' sang 'driving' để bắt buộc tuân thủ đường 1 chiều
    # OSRM yêu cầu định dạng tọa độ là: {longitude},{latitude}
    osrm_url = f"{OSRM_BASE_URL}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson&steps=true"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(osrm_url, timeout=5.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Không thể kết nối tới OSRM local")

            data = resp.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                return {"status": "error", "message": "Không tìm thấy tuyến đường"}

            route = data["routes"][0]
            legs = route.get("legs", [])
            steps = legs[0].get("steps", []) if legs else []

            next_step = None
            if len(steps) > 1:
                st = steps[1]
                next_step = {
                    "instruction": f"{st.get('maneuver', {}).get('type', '')} {st.get('maneuver', {}).get('modifier', '')}".strip(),
                    "name": st.get("name", ""),
                    "distance": round(st.get("distance", 0), 1)
                }

            return {
                "status": "success",
                "total_distance_m": route.get("distance", 0),
                "total_duration_s": route.get("duration", 0),
                "geometry": route.get("geometry"),
                "next_step": next_step,
                "all_steps": steps
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))