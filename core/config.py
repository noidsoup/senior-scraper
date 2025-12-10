"""
Configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # WordPress Configuration
    wp_url: str = "https://aplaceforseniorscms.kinsta.cloud"
    wp_username: Optional[str] = None
    wp_password: Optional[str] = None
    wp_user: Optional[str] = None  # Alias for wp_username
    wp_pass: Optional[str] = None  # Alias for wp_password
    
    # Senior Place Configuration
    sp_username: Optional[str] = None
    sp_password: Optional[str] = None
    
    # Scraping Behavior
    max_pages_per_state: int = 0  # 0 = unlimited
    request_delay_ms: int = 500
    max_retries: int = 3
    max_concurrent_enrichment: int = 3
    
    # Paths
    output_dir: str = "monthly_updates"
    cache_dir: str = ".cache"
    log_dir: str = "web_interface/logs"
    
    # Frontend
    frontend_base_url: str = "https://communities.aplaceforseniors.org"
    
    # Database
    database_path: str = "senior_scraper.db"
    
    # Notifications
    email_enabled: bool = False
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    
    slack_enabled: bool = False
    slack_webhook: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # 'json' or 'text'
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def wp_user_final(self) -> Optional[str]:
        """Get WordPress username from either wp_username or wp_user"""
        return self.wp_username or self.wp_user
    
    @property
    def wp_pass_final(self) -> Optional[str]:
        """Get WordPress password from either wp_password or wp_pass"""
        return self.wp_password or self.wp_pass
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings


def reload_settings():
    """Reload settings from environment (useful for testing)"""
    global _settings
    _settings = None
    return get_settings()

