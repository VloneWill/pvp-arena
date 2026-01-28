#imports for the settings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#create the settings class
class Settings(BaseSettings):
    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60

    #database url (env-driven, sqlite fallback)
    database_url: str = Field(default="sqlite:///./pvp_arena.db", alias="DATABASE_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

#create the settings instance
settings = Settings()
