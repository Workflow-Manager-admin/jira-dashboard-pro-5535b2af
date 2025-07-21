"""
Configuration management for Jira Dashboard Pro API
Handles environment variables and application settings
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Security Settings
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    session_timeout_hours: int = Field(default=8, env="SESSION_TIMEOUT_HOURS")
    
    # CORS Settings
    allowed_origins: str = Field(default="*", env="ALLOWED_ORIGINS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    max_requests_per_minute: int = Field(default=60, env="MAX_REQUESTS_PER_MINUTE")
    
    # Application URLs
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list"""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
