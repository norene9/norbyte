from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "Norbyte API"
    debug: bool = False
    database_url: str
    secret_key: str
    port: int = 8000

    class Config:
        env_file = ".env"  # reads from .env file automatically

settings = Settings()