from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ATT ERP API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://att_erp:att_erp@localhost:5432/att_erp"
    storage_path: str = "../storage"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
