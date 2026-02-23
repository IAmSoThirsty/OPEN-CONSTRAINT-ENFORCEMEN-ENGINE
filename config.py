"""
Configuration module following 12-factor app principles.
All configuration is driven by environment variables.
"""
import os
from typing import Optional


class Config:
    """Application configuration from environment variables."""

    # Server configuration
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000'))
    WORKERS: int = int(os.getenv('WORKERS', '4'))

    # Policy configuration
    POLICIES_DIR: str = os.getenv('POLICIES_DIR', 'policies')

    # Audit logging configuration
    AUDIT_LOG_DIR: str = os.getenv('AUDIT_LOG_DIR', 'audit_logs')

    # System context configuration
    MAX_THRESHOLD: int = int(os.getenv('MAX_THRESHOLD', '1000'))

    # Request limits
    MAX_CONTENT_LENGTH: int = int(os.getenv('MAX_CONTENT_LENGTH', '1048576'))  # 1MB
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))  # seconds

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_DEFAULT: str = os.getenv('RATE_LIMIT_DEFAULT', '100 per minute')
    RATE_LIMIT_STORAGE_URL: Optional[str] = os.getenv('RATE_LIMIT_STORAGE_URL')

    # Logging configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', 'json')  # json or text

    # Observability
    METRICS_ENABLED: bool = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'

    # Security
    SIMULATION_MAX_DEPTH: int = int(os.getenv('SIMULATION_MAX_DEPTH', '100'))
    SIMULATION_TIMEOUT: float = float(os.getenv('SIMULATION_TIMEOUT', '5.0'))  # seconds

    @classmethod
    def validate(cls) -> None:
        """Validate configuration values."""
        assert cls.WORKERS > 0, "WORKERS must be positive"
        assert cls.MAX_CONTENT_LENGTH > 0, "MAX_CONTENT_LENGTH must be positive"
        assert cls.REQUEST_TIMEOUT > 0, "REQUEST_TIMEOUT must be positive"
        assert cls.MAX_THRESHOLD > 0, "MAX_THRESHOLD must be positive"
        assert cls.LOG_LEVEL in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert cls.LOG_FORMAT in ['json', 'text']
