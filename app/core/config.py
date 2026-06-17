from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MODEL_NAME: str = "all-MiniLM-L6-v2"
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()