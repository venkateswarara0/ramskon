import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ramskon_secret_2024")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")