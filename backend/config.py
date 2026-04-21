from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = ""




    groq_model: str = "llama-3.3-70b-versatile"
    backend_port: int = 8000
    chroma_persist_dir: str = "./store/chroma"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()