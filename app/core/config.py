#imports for the settings
from pydantic_settings import BaseSettings, SettingsConfigDict

#create the settings class
class Settings(BaseSettings):
    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env")

#create the settings instance
settings = Settings()
