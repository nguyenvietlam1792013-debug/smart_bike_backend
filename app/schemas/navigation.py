from pydantic import BaseModel
from typing import List, Optional

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
    next_step: Optional[StepInstruction] = None
    all_steps: List[StepInstruction] = []