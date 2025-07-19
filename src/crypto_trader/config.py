import os
from typing import List, Dict
from pydantic import BaseSettings, validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Twitter API credentials
    twitter_bearer_token: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""
    
    # Exchange API credentials
    binance_api_key: str = ""
    binance_secret_key: str = ""
    okx_api_key: str = ""
    okx_secret_key: str = ""
    okx_passphrase: str = ""
    
    # LLM API credentials
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    
    # Trading configuration
    default_trade_amount_usdt: float = 100.0
    max_position_size_usdt: float = 1000.0
    stop_loss_percentage: float = 0.02  # 2%
    take_profit_percentage: float = 0.05  # 5%
    
    # KOL monitoring
    kol_usernames: List[str] = [
        "elonmusk",
        "VitalikButerin", 
        "satoshilite",
        "CZ_Binance",
        "DocumentingBTC",
        "PlanB_99",
        "APompliano"
    ]
    
    # Crypto tokens to monitor
    monitored_tokens: List[str] = [
        "BTC", "BITCOIN",
        "ETH", "ETHEREUM", 
        "SOL", "SOLANA",
        "ADA", "CARDANO",
        "DOT", "POLKADOT",
        "LINK", "CHAINLINK",
        "MATIC", "POLYGON",
        "AVAX", "AVALANCHE",
        "LUNA", "TERRA",
        "ATOM", "COSMOS"
    ]
    
    # Sentiment thresholds
    bullish_sentiment_threshold: float = 0.1
    bearish_sentiment_threshold: float = -0.1
    
    # Technical analysis
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # Rate limiting
    twitter_rate_limit_delay: int = 60  # seconds
    api_rate_limit_delay: float = 0.5   # seconds
    
    class Config:
        env_file = ".env"

settings = Settings()