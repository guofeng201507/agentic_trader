import asyncio
import signal
import sys
from typing import Dict, List
from loguru import logger
from .config import settings
from .twitter_monitor import TwitterMonitor
from .sentiment_analyzer import SentimentAnalyzer
from .technical_analyzer import TechnicalAnalyzer
from .exchange_manager import ExchangeManager
from .decision_engine import DecisionEngine
from .token_detector import TokenDetector

class CryptoKOLTrader:
    def __init__(self):
        self.running = True
        self.setup_logging()
        
        # Initialize components
        self.twitter_monitor = TwitterMonitor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()
        self.exchange_manager = ExchangeManager()
        self.decision_engine = DecisionEngine()
        self.token_detector = TokenDetector()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        logger.remove()
        logger.add(
            "logs/crypto_trader.log",
            rotation="1 day",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}"
        )
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{module}</cyan> | {message}"
        )
        logger.info("Crypto KOL Trader initialized")
    
    def signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def process_tweet(self, tweet_data: Dict) -> None:
        try:
            username = tweet_data['username']
            detected_tokens = tweet_data['detected_tokens']
            
            logger.info(f"Processing tweet from {username} mentioning: {detected_tokens}")
            
            # Process each detected token
            for token in detected_tokens:
                if not self.token_detector.is_hot_token(token):
                    logger.debug(f"Skipping {token} - not in hot tokens list")
                    continue
                
                # Get trading symbol for exchanges
                binance_symbol = self.token_detector.get_trading_symbol(token, 'binance')
                okx_symbol = self.token_detector.get_trading_symbol(token, 'okx')
                
                # Analyze sentiment using LLM
                sentiment_data = await self.sentiment_analyzer.analyze_sentiment(
                    tweet_data['text'], [token]
                )
                
                if not sentiment_data or sentiment_data.get('analysis_method') == 'fallback':
                    logger.warning(f"Sentiment analysis failed for {token}")
                    continue
                
                # Perform technical analysis (try Binance first, fallback to OKX)
                technical_data = None
                preferred_exchange = 'binance' if 'binance' in self.exchange_manager.get_available_exchanges() else 'okx'
                
                if preferred_exchange == 'binance':
                    technical_data = await self.technical_analyzer.comprehensive_analysis(binance_symbol, 'binance')
                
                if not technical_data or 'error' in technical_data:
                    logger.info(f"Trying OKX for {token} technical analysis")
                    technical_data = await self.technical_analyzer.comprehensive_analysis(okx_symbol, 'okx')
                    preferred_exchange = 'okx'
                
                if not technical_data or 'error' in technical_data:
                    logger.error(f"Technical analysis failed for {token} on both exchanges")
                    continue
                
                # Make trading decision
                decision = self.decision_engine.make_trading_decision(
                    tweet_data, sentiment_data, technical_data, token
                )
                
                logger.info(f"Decision for {token}: {decision.action} "
                           f"(confidence: {decision.confidence:.2f}, size: ${decision.position_size_usdt:.2f})")
                
                # Execute trade if decision warrants it
                if self.decision_engine.should_execute_trade(decision):
                    await self.execute_trade(token, decision, preferred_exchange)
                else:
                    logger.info(f"Trade not executed for {token}: {decision.reasoning}")
                
                # Add delay between tokens to avoid rate limits
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
    
    async def execute_trade(self, token: str, decision, exchange_name: str) -> None:
        try:
            # Get the appropriate trading symbol
            symbol = self.token_detector.get_trading_symbol(token, exchange_name)
            
            # Check if we should actually trade (additional safety check)
            if decision.risk_level == 'high' and decision.confidence < 0.8:
                logger.warning(f"Skipping high-risk trade for {token}")
                return
            
            # Prepare sentiment data for position sizing
            sentiment_data = {
                'position_size_multiplier': min(decision.confidence * 1.5, 2.0)
            }
            
            logger.info(f"Executing {decision.action} trade for {token} on {exchange_name}")
            logger.info(f"Reasoning: {decision.reasoning}")
            
            # Execute the trade
            trade_result = await self.exchange_manager.execute_trade(
                symbol=symbol,
                side=decision.action,
                amount_usdt=decision.position_size_usdt,
                sentiment_data=sentiment_data,
                exchange_name=exchange_name
            )
            
            if trade_result['success']:
                logger.success(f"Trade executed successfully: {trade_result}")
                
                # Record the trade for cooldown tracking
                self.decision_engine.record_trade(token)
                
                # Log trade details
                order = trade_result.get('order', {})
                logger.info(f"Order details: ID={order.get('id')}, "
                           f"Status={order.get('status')}, "
                           f"Price={trade_result.get('price'):.4f}, "
                           f"Quantity={trade_result.get('quantity'):.6f}")
            else:
                logger.error(f"Trade execution failed: {trade_result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error executing trade for {token}: {e}")
    
    async def monitor_and_trade(self) -> None:
        logger.info("Starting KOL monitoring and trading...")
        
        while self.running:
            try:
                # Monitor Twitter for new tweets
                processed_tweets = await self.twitter_monitor.monitor_kols()
                
                if not processed_tweets:
                    logger.debug("No new tweets with crypto mentions found")
                    await asyncio.sleep(settings.twitter_rate_limit_delay)
                    continue
                
                # Process each tweet
                for tweet_data in processed_tweets:
                    if not self.running:
                        break
                    
                    # Check if tweet is significant enough
                    if self.twitter_monitor.is_significant_tweet(tweet_data):
                        await self.process_tweet(tweet_data)
                    else:
                        logger.debug(f"Tweet from {tweet_data['username']} not significant enough")
                
                # Wait before next monitoring cycle
                await asyncio.sleep(settings.twitter_rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def health_check(self) -> Dict:
        """Check the health of all components"""
        health_status = {
            'timestamp': asyncio.get_event_loop().time(),
            'twitter_api': False,
            'exchanges': {},
            'sentiment_analyzer': False
        }
        
        try:
            # Check Twitter API
            try:
                # Try to get user info for one of our KOLs
                user_id = self.twitter_monitor.get_user_id('elonmusk')
                health_status['twitter_api'] = user_id is not None
            except:
                pass
            
            # Check exchanges
            for exchange_name in self.exchange_manager.get_available_exchanges():
                try:
                    balance = await self.exchange_manager.get_account_balance(exchange_name)
                    health_status['exchanges'][exchange_name] = bool(balance)
                except:
                    health_status['exchanges'][exchange_name] = False
            
            # Check sentiment analyzer (basic test)
            try:
                test_sentiment = await self.sentiment_analyzer.analyze_sentiment(
                    "Bitcoin is going to the moon! 🚀", ["BTC"]
                )
                health_status['sentiment_analyzer'] = test_sentiment.get('analysis_method') != 'fallback'
            except:
                pass
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
        
        return health_status
    
    async def run(self) -> None:
        """Main entry point"""
        try:
            # Perform initial health check
            health = await self.health_check()
            logger.info(f"System health check: {health}")
            
            # Verify we have at least one working exchange
            working_exchanges = [k for k, v in health['exchanges'].items() if v]
            if not working_exchanges:
                logger.error("No working exchanges found! Please check your API credentials.")
                return
            
            logger.info(f"Working exchanges: {working_exchanges}")
            
            # Start the main monitoring loop
            await self.monitor_and_trade()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            logger.info("Crypto KOL Trader shutting down")

async def main():
    """Entry point for the application"""
    trader = CryptoKOLTrader()
    await trader.run()

if __name__ == "__main__":
    asyncio.run(main())