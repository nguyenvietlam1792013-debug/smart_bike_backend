FROM python:3.11-slim

WORKDIR /app

# Thiết lập biến môi trường tối ưu cho Python trong Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Cài đặt các gói phụ thuộc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn ứng dụng
COPY app/ ./app/

# Mở cổng API
EXPOSE 8000

# Khởi chạy ứng dụng FastAPI qua Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
