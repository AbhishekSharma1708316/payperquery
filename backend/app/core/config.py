from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "AgentVault"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production-agentvault-secret-key"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/agentvault"
    DB_ECHO: bool = False

    # --- x402 / Algorand (AVM) ---
    X402_FACILITATOR_URL: str = "https://x402.org/facilitator"
    ALGORAND_NETWORK_CAIP2: str = "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI="
    USDC_TESTNET_ASA_ID: int = 10458941

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Policy defaults ---
    DEFAULT_MIN_PROVIDER_REPUTATION: int = 50

    # --- Mock provider (demo) ---
    MOCK_PROVIDER_PAY_TO: str = "MOCKPROVIDERALGORANDADDRESSXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"


@lru_cache
def get_settings() -> Settings:
    return Settings()
