import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Academic Performance Analytics System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "academic-analytics-amu-mca-secret-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./academic_analytics.db")
    
    # Judge0 API Configuration
    JUDGE0_API_URL: str = os.getenv("JUDGE0_API_URL", "https://judge0-ce.p.rapidapi.com")
    JUDGE0_API_KEY: str = os.getenv("JUDGE0_API_KEY", "")
    JUDGE0_HOST: str = os.getenv("JUDGE0_HOST", "judge0-ce.p.rapidapi.com")

settings = Settings()
