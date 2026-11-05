from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    secret_key: str = "development-only-change-me"
    database_url: str = "sqlite:///./attendance.db"
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeThisAdminPassword123!"
    access_token_expire_minutes: int = 60
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

settings = Settings()
