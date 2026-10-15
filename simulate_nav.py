import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Tọa độ mô phỏng: Hồ Hoàn Kiếm -> Hồ Tây (Đường Thanh Niên)
START_LAT, START_LON = 21.0285, 105.8542
END_LAT, END_LON = 21.0480, 105.8360
SPEED_KMH = 60.0  # Vận tốc mô phỏng (km/h)


def run_simulation():
    print("🚀 Đang chạy mô phỏng lộ trình Hồ Hoàn Kiếm -> Hồ Tây...")

    # 1. Trích xuất danh sách các điểm rẽ và tính thời gian ở 60 km/h
    route_url = f"{BASE_URL}/route"
    params_route = {
        "start_lat": START_LAT,
        "start_lon": START_LON,
        "end_lat": END_LAT,
        "end_lon": END_LON
    }

    try:
        resp_route = httpx.get(route_url, params=params_route, timeout=10.0)
        if resp_route.status_code != 200:
            print(f"❌ Lỗi lấy lộ trình: {resp_route.text}")
            return

        route_data = resp_route.json()

        # Tính toán thời gian di chuyển lý thuyết ở 60 km/h (16.67 m/s)
        total_dist_m = route_data.get("total_distance_m", 0)
        speed_ms = SPEED_KMH / 3.6
        simulated_duration_s = round(total_dist_m / speed_ms, 1) if speed_ms > 0 else 0

        # Cấu trúc dữ liệu JSON để kiểm tra
        simulation_result = {
            "simulation_metadata": {
                "start_location": "Hồ Hoàn Kiếm (21.0285, 105.8542)",
                "end_location": "Hồ Tây (21.0480, 105.8360)",
                "speed_kmh": SPEED_KMH,
                "total_distance_meters": total_dist_m,
                "simulated_duration_sec": simulated_duration_s,
                "simulated_duration_min": round(simulated_duration_s / 60, 2)
            },
            "turn_by_turn_instructions": route_data.get("all_steps", [])
        }

        # Xuất ra file JSON
        json_filename = "route_hoankiem_to_hotay.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(simulation_result, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã xuất danh sách các điểm rẽ ra file: {json_filename}")

    except Exception as e:
        print(f"❌ Lỗi kết nối API Route: {e}")
        return

    # 2. Render ảnh bản đồNavMap kèm đường kẻ màu xanh nước biển
    map_url = f"{BASE_URL}/map_image"
    params_map = {
        "lat": START_LAT,
        "lon": START_LON,
        "end_lat": END_LAT,
        "end_lon": END_LON,
        "zoom": 14,  # Mức zoom 14 để hiển thị trọn vẹn lộ trình từ Hồ Gươm ra Hồ Tây
        "width": 320,
        "height": 240
    }

    try:
        resp_map = httpx.get(map_url, params=params_map, timeout=10.0)
        if resp_map.status_code == 200:
            map_filename = "navmap_hoankiem_hotay.jpg"
            with open(map_filename, "wb") as f:
                f.write(resp_map.content)
            print(f"✅ Đã tải và lưu ảnh NavMap màu xanh nước biển: {map_filename}")
        else:
            print(f"❌ Lỗi render ảnh bản đồ: {resp_map.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối API Map Image: {e}")


if __name__ == "__main__":
    run_simulation()