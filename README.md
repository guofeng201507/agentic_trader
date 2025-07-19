# Crypto KOL Trading Bot

A sophisticated cryptocurrency trading bot that monitors Twitter Key Opinion Leaders (KOLs) and executes spot trades on Binance and OKX based on sentiment analysis and technical indicators.

## Features

- **Twitter KOL Monitoring**: Tracks tweets from influential crypto personalities
- **Advanced Sentiment Analysis**: Uses LLM-powered sentiment analysis (DeepSeek/OpenAI GPT-4o)
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Support/Resistance levels
- **Multi-Exchange Support**: Binance and OKX spot trading
- **Risk Management**: Stop-loss, take-profit, position sizing, cooldown periods
- **Real-time Processing**: Immediate analysis and trading execution

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -e .
   ```

2. **Configure API Keys**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

3. **Run the Bot**
   ```bash
   python run_trader.py
   ```

## Configuration

### Required API Keys

- **Twitter API**: Bearer token and API credentials
- **Exchange APIs**: Binance and/or OKX API keys
- **LLM APIs**: OpenAI and/or DeepSeek API keys

### Monitored KOLs

Default list includes:
- Elon Musk (@elonmusk)
- Vitalik Buterin (@VitalikButerin)
- Charlie Lee (@satoshilite)
- CZ Binance (@CZ_Binance)
- And more...

### Tracked Tokens

- BTC, ETH, SOL, ADA, DOT, LINK, MATIC, AVAX, LUNA, ATOM

## How It Works

1. **Tweet Monitoring**: Continuously monitors KOL tweets for crypto mentions
2. **Token Detection**: Identifies cryptocurrency tokens in tweet content
3. **Sentiment Analysis**: Analyzes tweet sentiment using advanced LLM models
4. **Technical Analysis**: Fetches and analyzes price data, indicators
5. **Decision Engine**: Combines sentiment and technical data for trading decisions
6. **Risk Management**: Applies safety filters and position sizing
7. **Trade Execution**: Places orders on configured exchanges

## Safety Features

- **Cooldown Periods**: Prevents spam trading on same token
- **Position Limits**: Maximum position sizes and risk controls
- **Confidence Thresholds**: Only trades on high-confidence signals
- **Stop-Loss/Take-Profit**: Automatic risk management orders
- **Health Monitoring**: System status checks and error handling

## Project Structure

```
src/crypto_trader/
├── main.py              # Main application orchestrator
├── config.py            # Configuration and settings
├── twitter_monitor.py   # Twitter API integration
├── sentiment_analyzer.py # LLM-powered sentiment analysis
├── token_detector.py    # Crypto token detection
├── technical_analyzer.py # Technical analysis module
├── exchange_manager.py  # Trading execution
└── decision_engine.py   # Trading decision logic
```

## Risk Disclaimer

This bot is for educational purposes. Cryptocurrency trading involves significant financial risk. Never trade with money you can't afford to lose. Always test with small amounts first.

## License

MIT License - see LICENSE file for details.