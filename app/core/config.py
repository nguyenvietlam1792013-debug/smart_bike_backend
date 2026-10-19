from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Bike Backend"
    API_V1_STR: str = "/api/v1"
    OSRM_BASE_URL: str = "http://localhost:5000"
    DEFAULT_ROUTING_PROFILE: str = "driving"
    OSRM_TIMEOUT_SECONDS: float = 5.0
    TILE_CACHE_MAXSIZE: int = 512
    TILE_USER_AGENT: str = "SmartBikeBackend/1.0"

    class Config:
        case_sensitive = True

settings = Settings()