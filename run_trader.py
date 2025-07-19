#!/usr/bin/env python3
"""
Crypto KOL Trading Bot Entry Point

This script runs the main crypto trading bot that monitors Twitter KOLs
and executes trades based on sentiment analysis and technical indicators.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from crypto_trader.main import main

if __name__ == "__main__":
    print("🚀 Starting Crypto KOL Trading Bot...")
    print("📊 Monitoring Twitter KOLs for crypto sentiment...")
    print("💰 Ready to execute trades based on analysis...")
    print("Press Ctrl+C to stop the bot\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        sys.exit(1)