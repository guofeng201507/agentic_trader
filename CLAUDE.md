# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sophisticated cryptocurrency trading bot that monitors Twitter KOLs (Key Opinion Leaders) and executes spot trades based on sentiment analysis and technical indicators. The bot integrates with Twitter API, LLM services (DeepSeek/OpenAI), and crypto exchanges (Binance/OKX).

## Project Structure

```
crypto-kol-trader/
├── src/crypto_trader/          # Main package
│   ├── main.py                 # Application orchestrator
│   ├── config.py               # Configuration management
│   ├── twitter_monitor.py      # Twitter API integration
│   ├── sentiment_analyzer.py   # LLM-powered sentiment analysis
│   ├── token_detector.py       # Crypto token detection
│   ├── technical_analyzer.py   # Technical analysis (RSI, MACD, etc.)
│   ├── exchange_manager.py     # Trading execution (Binance/OKX)
│   └── decision_engine.py      # Trading decision logic
├── run_trader.py              # Main entry point
├── logs/                      # Application logs
├── .env.example              # Environment variables template
├── pyproject.toml            # Dependencies and config
└── README.md                 # Documentation
```

## Development Setup

- **Install in development mode**: `pip install -e .`
- **Python version**: Requires Python >= 3.10
- **Configuration**: Copy `.env.example` to `.env` and add API credentials

## Common Commands

- **Run the trading bot**: `python run_trader.py`
- **Install dependencies**: `pip install -e .`
- **Test configuration**: Check that `.env` file has all required API keys

## Key Dependencies

- `tweepy`: Twitter API integration
- `ccxt`: Cryptocurrency exchange APIs
- `openai`: OpenAI GPT-4o integration
- `ta`: Technical analysis indicators
- `pandas/numpy`: Data processing
- `loguru`: Structured logging
- `pydantic`: Configuration validation

## Architecture Notes

- **Async Design**: Uses asyncio for concurrent operations
- **Modular Components**: Each major function is in separate modules
- **Risk Management**: Built-in safety features and position limits
- **Multi-Exchange**: Supports both Binance and OKX
- **LLM Integration**: Primary sentiment analysis via DeepSeek/OpenAI
- **Error Handling**: Comprehensive logging and fallback mechanisms

## API Requirements

- Twitter API v2 credentials (Bearer token)
- Binance and/or OKX API keys for trading
- OpenAI API key for GPT-4o
- DeepSeek API key (optional, fallback to OpenAI)

## Development Guidelines

- Always test with sandbox/testnet environments first
- Monitor logs in `logs/crypto_trader.log`
- Check health status via the built-in health check system
- Be cautious with API rate limits across all services
- Use appropriate position sizing and risk management