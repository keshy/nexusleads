"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # GitHub (optional - can be set via UI settings)
    GITHUB_TOKEN: str = ""
    
    # Azure OpenAI (optional - can be set via UI settings)
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    
    # OpenAI (optional - can be set via UI settings)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # Serper (optional - can be set via UI settings)
    SERPER_API_KEY: str = ""
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    CORS_ORIGINS: str = ""
    
    # Application
    APP_NAME: str = "PLG Lead Sourcer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    @property
    def origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        origins = self.CORS_ORIGINS or self.ALLOWED_ORIGINS
        return [origin.strip() for origin in origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
