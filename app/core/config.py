from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LSA_N_COMPONENTS: int = 128
    TFIDF_MAX_FEATURES: int = 10000
    BATCH_TOP_K: int = 100
    APP_ENV: str = "production"

    class Config:
        env_file = ".env"

settings = Settings()
