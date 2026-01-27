from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
