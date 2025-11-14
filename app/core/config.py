from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings and configuration"""
    
    # Application related
    APP_NAME: str = "C2PA Video Signing Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # File Storage related
    UPLOAD_DIR: str = "./files"
    MAX_FILE_SIZE_MB: int = 500
    
    # C2PA related
    CERT_PATH: str = "./certificates/certificate.pem"
    PRIVATE_KEY_PATH: str = "./certificates/private_key.pem"
    MANIFEST_DIR: str = "./manifests"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()

settings = get_settings()

# Ensure necessary directories exist on startup
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.MANIFEST_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.CERT_PATH), exist_ok=True)