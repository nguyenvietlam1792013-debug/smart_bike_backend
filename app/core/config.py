from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Bike Backend"
    API_V1_STR: str = "/api/v1"
    OSRM_BASE_URL: str = "http://localhost:5000"

    class Config:
        case_sensitive = True

settings = Settings()