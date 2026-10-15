from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from app.api import route_router, map_router

app = FastAPI(title="Smart Bike Backend")

# Khai báo thư mục chứa file HTML
templates = Jinja2Templates(directory="app/templates")

# Đăng ký các router API
app.include_router(route_router.router, prefix="/api/v1/route", tags=["route"])
app.include_router(map_router.router, prefix="/api/v1/map", tags=["map"])
app.include_router(map_router.router, prefix="/api/v1", tags=["map_legacy"])

@app.get("/")
async def read_root(request: Request):
    # Fix cho Starlette/FastAPI trên Python 3.14: truyền request trực tiếp dạng keyword argument
    return templates.TemplateResponse(request=request, name="index.html")