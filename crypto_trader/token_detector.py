import re
from typing import List, Set, Dict
from .config import settings

class TokenDetector:
    def __init__(self):
        self.token_patterns = self._build_token_patterns()
        self.symbol_mapping = self._build_symbol_mapping()
    
    def _build_token_patterns(self) -> Dict[str, re.Pattern]:
        patterns = {}
        
        for token in settings.monitored_tokens:
            # Create pattern for token mentions
            # Matches $TOKEN, #TOKEN, TOKEN (as whole word)
            pattern = rf'\b(?:\$|#)?{re.escape(token)}\b'
            patterns[token] = re.compile(pattern, re.IGNORECASE)
        
        # Additional patterns for common crypto mentions
        additional_patterns = {
            'BTC': re.compile(r'\b(?:\$|#)?(?:BTC|BITCOIN)\b', re.IGNORECASE),
            'ETH': re.compile(r'\b(?:\$|#)?(?:ETH|ETHEREUM)\b', re.IGNORECASE),
            'SOL': re.compile(r'\b(?:\$|#)?(?:SOL|SOLANA)\b', re.IGNORECASE),
            'ADA': re.compile(r'\b(?:\$|#)?(?:ADA|CARDANO)\b', re.IGNORECASE),
            'DOT': re.compile(r'\b(?:\$|#)?(?:DOT|POLKADOT)\b', re.IGNORECASE),
            'LINK': re.compile(r'\b(?:\$|#)?(?:LINK|CHAINLINK)\b', re.IGNORECASE),
            'MATIC': re.compile(r'\b(?:\$|#)?(?:MATIC|POLYGON)\b', re.IGNORECASE),
            'AVAX': re.compile(r'\b(?:\$|#)?(?:AVAX|AVALANCHE)\b', re.IGNORECASE),
        }
        
        patterns.update(additional_patterns)
        return patterns
    
    def _build_symbol_mapping(self) -> Dict[str, str]:
        return {
            'BITCOIN': 'BTC',
            'ETHEREUM': 'ETH', 
            'SOLANA': 'SOL',
            'CARDANO': 'ADA',
            'POLKADOT': 'DOT',
            'CHAINLINK': 'LINK',
            'POLYGON': 'MATIC',
            'AVALANCHE': 'AVAX',
            'TERRA': 'LUNA',
            'COSMOS': 'ATOM'
        }
    
    def detect_tokens(self, text: str) -> List[str]:
        detected = set()
        text_upper = text.upper()
        
        # Check for each token pattern
        for token, pattern in self.token_patterns.items():
            if pattern.search(text):
                # Normalize to symbol if it's a full name
                normalized_token = self.symbol_mapping.get(token, token)
                detected.add(normalized_token)
        
        # Additional context-aware detection
        detected.update(self._detect_contextual_mentions(text_upper))
        
        return list(detected)
    
    def _detect_contextual_mentions(self, text: str) -> Set[str]:
        detected = set()
        
        # Common crypto-related phrases
        bullish_phrases = [
            'TO THE MOON', 'HODL', 'DIAMOND HANDS', 'BUY THE DIP',
            'BULLISH', 'PUMP', 'MOON', 'ROCKET', '🚀', '💎', '🙌'
        ]
        
        bearish_phrases = [
            'DUMP', 'CRASH', 'BEARISH', 'SELL', 'SHORT', 'BEAR MARKET',
            'CORRECTION', 'DIP', 'RED', 'BLOOD', '📉', '💀'
        ]
        
        # If bullish/bearish language is detected, look for nearby token mentions
        has_crypto_sentiment = any(phrase in text for phrase in bullish_phrases + bearish_phrases)
        
        if has_crypto_sentiment:
            # Look for token symbols that might be mentioned without explicit markers
            words = re.findall(r'\b[A-Z]{2,5}\b', text)
            for word in words:
                if word in settings.monitored_tokens:
                    detected.add(word)
        
        return detected
    
    def get_trading_symbol(self, token: str, exchange: str = 'binance') -> str:
        token = token.upper()
        
        # Standard USDT pairs
        if exchange.lower() == 'binance':
            return f"{token}USDT"
        elif exchange.lower() == 'okx':
            return f"{token}-USDT"
        
        return f"{token}USDT"
    
    def is_hot_token(self, token: str) -> bool:
        hot_tokens = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'LINK', 'MATIC', 'AVAX']
        return token.upper() in hot_tokens