from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class StepInstruction(BaseModel):
    instruction: str
    icon_id: int          # Mã icon: 1=Đi thẳng, 2=Phải, 3=Trái, 4=Ngoặt phải, 5=Ngoặt trái, 6=Quay đầu, 7=Đến đích
    type: str
    modifier: Optional[str] = ""
    distance: float
    name: Optional[str] = ""

class RouteResponse(BaseModel):
    status: str
    total_distance_m: float
    total_duration_s: float
    geometry: Optional[Dict[str, Any]] = None
    next_step: Optional[StepInstruction] = None
    all_steps: List[StepInstruction] = []
    message: Optional[str] = None

class CYDRouteResponse(BaseModel):
    status: str
    icon_id: int               # Mã icon: 1=Đi thẳng, 2=Phải, 3=Trái, 4=Ngoặt phải, 5=Ngoặt trái, 6=Quay đầu, 7=Đến đích
    step_dist: float           # Khoảng cách đến bước tiếp theo (mét)
    step_name: str             # Tên đường tiếp theo
    step_instruction: str      # Hướng dẫn vắn tắt
    total_dist: float          # Tổng quãng đường còn lại (mét)
    total_time: float          # Tổng thời gian ước tính (giây)
    next_icon_id: int          # Mã icon của bước kế tiếp (+1) hoặc 0 nếu sắp tới đích
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    code: str
    message: str