import ccxt
import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from .config import settings

class TechnicalAnalyzer:
    def __init__(self):
        self.exchanges = self._setup_exchanges()
        
    def _setup_exchanges(self) -> Dict:
        exchanges = {}
        
        try:
            # Binance setup
            if settings.binance_api_key:
                exchanges['binance'] = ccxt.binance({
                    'apiKey': settings.binance_api_key,
                    'secret': settings.binance_secret_key,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
        except Exception as e:
            logger.warning(f"Failed to setup Binance: {e}")
        
        try:
            # OKX setup
            if settings.okx_api_key:
                exchanges['okx'] = ccxt.okx({
                    'apiKey': settings.okx_api_key,
                    'secret': settings.okx_secret_key,
                    'password': settings.okx_passphrase,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
        except Exception as e:
            logger.warning(f"Failed to setup OKX: {e}")
        
        return exchanges
    
    async def get_market_data(self, symbol: str, timeframe: str = '1h', 
                             limit: int = 100, exchange: str = 'binance') -> Optional[pd.DataFrame]:
        try:
            if exchange not in self.exchanges:
                logger.error(f"Exchange {exchange} not configured")
                return None
            
            exchange_obj = self.exchanges[exchange]
            ohlcv = exchange_obj.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol}: {e}")
            return None
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        try:
            rsi = ta.momentum.RSIIndicator(close=df['close'], window=period)
            return rsi.rsi().iloc[-1]
        except Exception as e:
            logger.error(f"Failed to calculate RSI: {e}")
            return 50.0  # Neutral RSI
    
    def find_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
        try:
            highs = df['high'].rolling(window=window, center=True).max()
            lows = df['low'].rolling(window=window, center=True).min()
            
            # Find recent support and resistance levels
            resistance_levels = []
            support_levels = []
            
            for i in range(window, len(df) - window):
                if df['high'].iloc[i] == highs.iloc[i]:
                    resistance_levels.append(df['high'].iloc[i])
                if df['low'].iloc[i] == lows.iloc[i]:
                    support_levels.append(df['low'].iloc[i])
            
            current_price = df['close'].iloc[-1]
            
            # Find nearest support and resistance
            resistance_levels = [r for r in resistance_levels if r > current_price]
            support_levels = [s for s in support_levels if s < current_price]
            
            nearest_resistance = min(resistance_levels) if resistance_levels else current_price * 1.05
            nearest_support = max(support_levels) if support_levels else current_price * 0.95
            
            return {
                'current_price': current_price,
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'support_distance': (current_price - nearest_support) / current_price,
                'resistance_distance': (nearest_resistance - current_price) / current_price
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate support/resistance: {e}")
            return {'current_price': 0, 'nearest_support': 0, 'nearest_resistance': 0}
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, float]:
        try:
            return {
                'sma_20': df['close'].rolling(window=20).mean().iloc[-1],
                'sma_50': df['close'].rolling(window=50).mean().iloc[-1],
                'ema_12': df['close'].ewm(span=12).mean().iloc[-1],
                'ema_26': df['close'].ewm(span=26).mean().iloc[-1],
            }
        except Exception as e:
            logger.error(f"Failed to calculate moving averages: {e}")
            return {}
    
    def calculate_macd(self, df: pd.DataFrame) -> Dict[str, float]:
        try:
            macd_indicator = ta.trend.MACD(close=df['close'])
            return {
                'macd': macd_indicator.macd().iloc[-1],
                'macd_signal': macd_indicator.macd_signal().iloc[-1],
                'macd_histogram': macd_indicator.macd_diff().iloc[-1]
            }
        except Exception as e:
            logger.error(f"Failed to calculate MACD: {e}")
            return {}
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, window: int = 20, 
                                 std_dev: int = 2) -> Dict[str, float]:
        try:
            bb_indicator = ta.volatility.BollingerBands(close=df['close'], 
                                                       window=window, window_dev=std_dev)
            current_price = df['close'].iloc[-1]
            upper_band = bb_indicator.bollinger_hband().iloc[-1]
            lower_band = bb_indicator.bollinger_lband().iloc[-1]
            
            return {
                'bb_upper': upper_band,
                'bb_middle': bb_indicator.bollinger_mavg().iloc[-1],
                'bb_lower': lower_band,
                'bb_position': (current_price - lower_band) / (upper_band - lower_band)
            }
        except Exception as e:
            logger.error(f"Failed to calculate Bollinger Bands: {e}")
            return {}
    
    def analyze_volume(self, df: pd.DataFrame) -> Dict[str, float]:
        try:
            volume_sma = df['volume'].rolling(window=20).mean()
            current_volume = df['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            return {
                'current_volume': current_volume,
                'avg_volume_20': avg_volume,
                'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1.0,
                'volume_trend': 'increasing' if current_volume > avg_volume * 1.5 else 'normal'
            }
        except Exception as e:
            logger.error(f"Failed to analyze volume: {e}")
            return {}
    
    async def comprehensive_analysis(self, symbol: str, exchange: str = 'binance') -> Dict:
        df = await self.get_market_data(symbol, timeframe='1h', limit=200, exchange=exchange)
        
        if df is None or len(df) < 50:
            logger.warning(f"Insufficient data for {symbol}")
            return {'error': 'insufficient_data'}
        
        try:
            analysis = {
                'symbol': symbol,
                'timestamp': df.index[-1],
                'current_price': df['close'].iloc[-1],
                'rsi': self.calculate_rsi(df),
                'support_resistance': self.find_support_resistance(df),
                'moving_averages': self.calculate_moving_averages(df),
                'macd': self.calculate_macd(df),
                'bollinger_bands': self.calculate_bollinger_bands(df),
                'volume_analysis': self.analyze_volume(df),
                'price_change_24h': ((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24]) * 100,
                'volatility': df['close'].pct_change().std() * 100
            }
            
            # Add trading signals
            analysis['trading_signals'] = self._generate_trading_signals(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to perform comprehensive analysis: {e}")
            return {'error': 'analysis_failed'}
    
    def _generate_trading_signals(self, analysis: Dict) -> Dict[str, str]:
        signals = {}
        
        try:
            rsi = analysis.get('rsi', 50)
            macd = analysis.get('macd', {})
            bb = analysis.get('bollinger_bands', {})
            sr = analysis.get('support_resistance', {})
            ma = analysis.get('moving_averages', {})
            
            # RSI signals
            if rsi < settings.rsi_oversold:
                signals['rsi'] = 'oversold_buy'
            elif rsi > settings.rsi_overbought:
                signals['rsi'] = 'overbought_sell'
            else:
                signals['rsi'] = 'neutral'
            
            # MACD signals
            if macd.get('macd', 0) > macd.get('macd_signal', 0):
                signals['macd'] = 'bullish'
            else:
                signals['macd'] = 'bearish'
            
            # Bollinger Bands signals
            bb_pos = bb.get('bb_position', 0.5)
            if bb_pos < 0.1:
                signals['bollinger'] = 'oversold'
            elif bb_pos > 0.9:
                signals['bollinger'] = 'overbought'
            else:
                signals['bollinger'] = 'neutral'
            
            # Support/Resistance signals
            if sr.get('support_distance', 0) < 0.02:  # Within 2% of support
                signals['support_resistance'] = 'near_support'
            elif sr.get('resistance_distance', 0) < 0.02:  # Within 2% of resistance
                signals['support_resistance'] = 'near_resistance'
            else:
                signals['support_resistance'] = 'neutral'
            
            # Overall signal
            buy_signals = sum(1 for s in signals.values() if 'buy' in s or s in ['bullish', 'oversold', 'near_support'])
            sell_signals = sum(1 for s in signals.values() if 'sell' in s or s in ['bearish', 'overbought', 'near_resistance'])
            
            if buy_signals > sell_signals:
                signals['overall'] = 'buy'
            elif sell_signals > buy_signals:
                signals['overall'] = 'sell'
            else:
                signals['overall'] = 'hold'
            
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate trading signals: {e}")
            return {'overall': 'hold'}
    
    def is_good_entry_point(self, analysis: Dict, sentiment: str) -> bool:
        try:
            signals = analysis.get('trading_signals', {})
            rsi = analysis.get('rsi', 50)
            
            if sentiment == 'bullish':
                return (
                    rsi < 70 and  # Not overbought
                    signals.get('overall') in ['buy', 'hold'] and
                    signals.get('support_resistance') != 'near_resistance'
                )
            elif sentiment == 'bearish':
                return (
                    rsi > 30 and  # Not oversold
                    signals.get('overall') in ['sell', 'hold'] and
                    signals.get('support_resistance') != 'near_support'
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to determine entry point: {e}")
            return False