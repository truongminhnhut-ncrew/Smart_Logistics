"""
config.py — Pydantic Settings from environment variables.

All configuration is read from .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment."""

    # ── MongoDB ──────────────────────────────────
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_db: str = Field(default="shiptrack", env="MONGODB_DB")

    # ── Kafka ────────────────────────────────────
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic_gps: str = Field(default="gps_stream", env="KAFKA_TOPIC_GPS")
    kafka_consumer_group: str = Field(default="shiptrack-consumer", env="KAFKA_CONSUMER_GROUP")

    # ── Redis ────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_gps_ttl: int = Field(default=10, env="REDIS_GPS_TTL")

    # ── Backend ──────────────────────────────────
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=8000, env="BACKEND_PORT")
    cors_origins: str = Field(default="http://localhost:3000", env="CORS_ORIGINS")

    # ── Data Generator ───────────────────────────
    backend_ws_url: str = Field(default="ws://localhost:8000/ws/ingest", env="BACKEND_WS_URL")
    simulator_shipper_count: int = Field(default=30, env="SIMULATOR_SHIPPER_COUNT")
    simulator_gps_interval: float = Field(default=1.0, env="SIMULATOR_GPS_INTERVAL")

    # ── Business Rules ───────────────────────────
    gps_timeout_seconds: int = Field(default=30, env="GPS_TIMEOUT_SECONDS")
    max_speed_kmph: int = Field(default=80, env="MAX_SPEED_KMPH")
    max_retry_assign: int = Field(default=5, env="MAX_RETRY_ASSIGN")
    idle_warning_seconds: int = Field(default=120, env="IDLE_WARNING_SECONDS")
    delay_alert_minutes: int = Field(default=15, env="DELAY_ALERT_MINUTES")

    # ── Frontend ─────────────────────────────────
    vite_api_url: str = Field(default="http://localhost:8000", env="VITE_API_URL")
    vite_ws_url: str = Field(default="ws://localhost:8000/ws", env="VITE_WS_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
