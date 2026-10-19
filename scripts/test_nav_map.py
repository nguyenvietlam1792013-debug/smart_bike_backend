import httpx

# Cấu hình URL backend và tọa độ thử nghiệm (Mặc định: Hồ Hoàn Kiếm -> Nhà hát Lớn Hà Nội)
BASE_URL = "http://127.0.0.1:8000/api/v1"

START_LAT = 21.0285  # Vĩ độ xuất phát (GPS hiện tại)
START_LON = 105.8542  # Kinh độ xuất phát

END_LAT = 21.0245  # Vĩ độ điểm đích
END_LON = 105.8576  # Kinh độ điểm đích


def test_route_api():
    print("=" * 50)
    print("1. Đang kiểm tra API Route Chỉ Đường (/route)...")
    url = f"{BASE_URL}/route"
    params = {
        "start_lat": START_LAT,
        "start_lon": START_LON,
        "end_lat": END_LAT,
        "end_lon": END_LON
    }

    try:
        response = httpx.get(url, params=params, timeout=5.0)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"-> Trạng thái OSRM: {data.get('status')}")
            print(f"-> Tổng khoảng cách: {data.get('total_distance_m')} mét")
            print(f"-> Thời gian di chuyển: {round(data.get('total_duration_s', 0) / 60, 1)} phút")

            next_step = data.get("next_step")
            if next_step:
                print(
                    f"-> Hướng rẽ tiếp theo: {next_step.get('instruction')} ({next_step.get('name')}) - {next_step.get('distance')}m")
            print("=> TEST ROUTE API SUCCESSFUL!\n")
        else:
            print(f"Lỗi API: {response.text}")
    except Exception as e:
        print(f" Không thể kết nối tới Backend: {e}\n")


def test_map_image_api():
    print("=" * 50)
    print("2. Đang kiểm tra API Render Ảnh Bản Đồ Nav Map (/map_image)...")
    url = f"{BASE_URL}/map_image"
    params = {
        "lat": START_LAT,
        "lon": START_LON,
        "end_lat": END_LAT,
        "end_lon": END_LON,
        "zoom": 16,
        "width": 320,
        "height": 240
    }

    output_filename = "nav_map_test.jpg"

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            image_bytes = response.content

            # Lưu ảnh ra đĩa
            with open(output_filename, "wb") as f:
                f.write(image_bytes)

            file_size_kb = len(image_bytes) / 1024
            print(f"-> Đã tải thành công ảnh JPEG kích thước: {file_size_kb:.2f} KB")
            print(f"-> Đã lưu ảnh vào file: {output_filename}")
            print("=> TEST MAP IMAGE API SUCCESSFUL!\n")
        else:
            print(f"Lỗi API: {response.text}")
    except Exception as e:
        print(f" Không thể tải ảnh từ Backend: {e}\n")


if __name__ == "__main__":
    print(" Đang bắt đầu kiểm tra tính năng Navigation Map...")
    test_route_api()
    test_map_image_api()