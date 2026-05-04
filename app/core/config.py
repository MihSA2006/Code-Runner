from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    # API
    APP_NAME: str        = os.getenv("APP_NAME", "CodeRunner")
    APP_VERSION: str     = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool          = os.getenv("DEBUG", "True") == "True"

    # Execution
    MAX_EXECUTION_TIME: int = int(os.getenv("MAX_EXECUTION_TIME", "10"))
    MAX_MEMORY: str         = os.getenv("MAX_MEMORY", "128m")
    MAX_CPU: float          = float(os.getenv("MAX_CPU", "0.5"))

    # Rate limiting
    RATE_LIMIT_EXECUTE: str = os.getenv("RATE_LIMIT_EXECUTE", "10/minute")
    RATE_LIMIT_RESULT: str  = os.getenv("RATE_LIMIT_RESULT", "60/minute")

    # Code limits
    MAX_CODE_LENGTH: int   = int(os.getenv("MAX_CODE_LENGTH", "50000"))
    MAX_OUTPUT_LENGTH: int = int(os.getenv("MAX_OUTPUT_LENGTH", "10000"))

    # Database
    DATABASE_URL: str  = os.getenv("DATABASE_URL", "./coderunner.db")
    TOKEN_EXPIRY: int  = int(os.getenv("TOKEN_EXPIRY", "300"))

    # Cleanup
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "60"))

    # Langages supportés
    SUPPORTED_LANGUAGES = ["python", "java", "javascript", "c", "cpp"]

settings = Settings()
