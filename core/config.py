import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration loaded from environment variables."""
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cvify.db")
    
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "")
    
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
