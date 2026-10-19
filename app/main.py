from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from app.api import route_router, map_router
from app.services.osrm_service import close_http_client
from app.services.map_service import close_map_http_client
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động ứng dụng
    yield
    # Dọn dẹp tài nguyên và đóng kết nối HTTP pool khi tắt server
    await close_http_client()
    await close_map_http_client()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.1.0",
    description="Hệ thống Backend Điều Hướng & Telemetry cho Thiết Bị Xe Đạp Thông Minh (ESP32 CYD)",
    lifespan=lifespan
)

# Cấu hình thư mục chứa template giao diện
templates = Jinja2Templates(directory="app/templates")

# Đăng ký các router API
app.include_router(route_router.router, prefix="/api/v1/route", tags=["route"])
app.include_router(map_router.router, prefix="/api/v1/map", tags=["map"])
app.include_router(map_router.router, prefix="/api/v1", tags=["map_legacy"])


@app.get("/", summary="Dashboard Điều Hướng & Giả Lập Màn Hình Xe Đạp")
async def read_root(request: Request):
    # Starlette/FastAPI trên Python 3.14: truyền request dạng keyword argument
    return templates.TemplateResponse(request=request, name="index.html")