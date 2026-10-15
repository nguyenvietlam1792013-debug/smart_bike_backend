import os
import time
import math
import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"
OSRM_URL = "http://localhost:5000"

START_LAT, START_LON = 21.0285, 105.8542  # Hồ Hoàn Kiếm
END_LAT, END_LON = 21.0480, 105.8360  # Hồ Tây
SPEED_KMH = 60.0  # 60 km/h
SPEED_MS = SPEED_KMH / 3.6  # ~16.67 m/s

# Tạo thư mục chứa frame ảnh
os.makedirs("frames", exist_ok=True)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def interpolate_points(coords, speed_ms):
    """Chia tuyến đường thành danh sách các tọa độ GPS mỗi giây dựa trên vận tốc"""
    path_points = []
    for i in range(len(coords) - 1):
        p1, p2 = coords[i], coords[i + 1]
        lon1, lat1 = p1[0], p1[1]
        lon2, lat2 = p2[0], p2[1]

        dist = haversine(lat1, lon1, lat2, lon2)
        if dist == 0:
            continue

        steps = max(1, int(dist / speed_ms))
        for s in range(steps):
            ratio = s / steps
            curr_lat = lat1 + (lat2 - lat1) * ratio
            curr_lon = lon1 + (lon2 - lon1) * ratio
            path_points.append((curr_lat, curr_lon))

    path_points.append((coords[-1][1], coords[-1][0]))
    return path_points


async def run_frame_simulation():
    print("🚀 Bắt đầu giả lập NavMap 1 frame/giây (60 km/h)...")

    # 1. Lấy tuyến đường GeoJSON từ OSRM
    osrm_geom_url = f"{OSRM_URL}/route/v1/biking/{START_LON},{START_LAT};{END_LON},{END_LAT}?overview=full&geometries=geojson"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(osrm_geom_url, timeout=5.0)
            data = resp.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                print("❌ Lỗi: Server OSRM tại http://localhost:5000 chưa chạy hoặc không tìm thấy đường đi!")
                return
            coords = data["routes"][0]["geometry"]["coordinates"]
        except Exception as e:
            print(f"❌ Không kết nối được OSRM local: {e}")
            print("👉 Hãy đảm bảo OSRM container/service trên WSL đang chạy ở port 5000!")
            return

        # 2. Tạo chuỗi tọa độ giả lập theo thời gian thực (1 giây / bước)
        gps_timeline = interpolate_points(coords, SPEED_MS)
        total_seconds = len(gps_timeline)
        print(f"✅ Đã tạo lộ trình: {total_seconds} giây (tương ứng {total_seconds} frames ảnh).")

        simulation_history = []

        # 3. Chạy vòng lặp từng giây: gọi API backend lấy ảnh + data rẽ
        for sec, (curr_lat, curr_lon) in enumerate(gps_timeline):
            # A. Gọi API lấy thông tin bước rẽ hiện tại
            route_resp = await client.get(
                f"{BASE_URL}/route",
                params={"start_lat": curr_lat, "start_lon": curr_lon, "end_lat": END_LAT, "end_lon": END_LON}
            )
            route_info = route_resp.json() if route_resp.status_code == 200 else {}

            # B. Gọi API render ảnh bản đồ tĩnh tại tọa độ hiện tại
            map_resp = await client.get(
                f"{BASE_URL}/map_image",
                params={
                    "lat": curr_lat,
                    "lon": curr_lon,
                    "end_lat": END_LAT,
                    "end_lon": END_LON,
                    "zoom": 16,
                    "width": 320,
                    "height": 240
                }
            )

            # C. Lưu file ảnh frame
            frame_filename = f"frames/frame_{sec:03d}.jpg"
            if map_resp.status_code == 200:
                with open(frame_filename, "wb") as f:
                    f.write(map_resp.content)

            # D. Ghi log dữ liệu đồng bộ
            log_entry = {
                "second": sec,
                "current_gps": {"lat": round(curr_lat, 6), "lon": round(curr_lon, 6)},
                "speed_kmh": SPEED_KMH,
                "frame_path": frame_filename,
                "navigation": {
                    "total_distance_m": route_info.get("total_distance_m", 0),
                    "next_step": route_info.get("next_step")
                }
            }
            simulation_history.append(log_entry)
            print(
                f" Frame {sec:03d}/{total_seconds}s | GPS: ({curr_lat:.4f}, {curr_lon:.4f}) | Còn: {route_info.get('total_distance_m', 0)}m")

        # 4. Xuất file JSON đồng bộ hoàn chỉnh
        with open("simulation_log.json", "w", encoding="utf-8") as f:
            json.dump(simulation_history, f, ensure_ascii=False, indent=4)

        print("\n🎉 MÔ PHỎNG HOÀN TẤT!")
        print(" Tự động tạo chuỗi ảnh tại thư mục: /frames/frame_XXX.jpg")
        print(" Tự động xuất file log chi tiết: simulation_log.json")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_frame_simulation())