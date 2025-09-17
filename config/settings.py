"""Application configuration settings."""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    # Browserbase Configuration
    browserbase_api_key: str = os.getenv("BROWSERBASE_API_KEY", "")
    browserbase_project_id: str = os.getenv("BROWSERBASE_PROJECT_ID", "")

    # Application Configuration
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Test Execution Settings
    max_parallel_tests: int = int(os.getenv("MAX_PARALLEL_TESTS", "5"))
    test_timeout: int = int(os.getenv("TEST_TIMEOUT", "60000"))
    screenshot_on_failure: bool = (
        os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
    )
    headless_mode: bool = os.getenv("HEADLESS_MODE", "true").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
