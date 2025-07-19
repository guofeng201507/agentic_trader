import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from .config import settings

@dataclass
class TradingDecision:
    action: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0.0 to 1.0
    position_size_usdt: float
    reasoning: List[str]
    risk_level: str  # 'low', 'medium', 'high'
    timeframe: str  # 'immediate', 'short', 'medium'

class DecisionEngine:
    def __init__(self):
        self.recent_trades = {}  # Track recent trades to avoid spam
        self.cooldown_period = 300  # 5 minutes between trades for same token
        
    def make_trading_decision(self, tweet_data: Dict, sentiment_data: Dict, 
                            technical_data: Dict, token: str) -> TradingDecision:
        try:
            # Check if we're in cooldown for this token
            if self._is_in_cooldown(token):
                return self._create_hold_decision("Token in cooldown period")
            
            # Analyze all factors
            sentiment_score = self._analyze_sentiment_factors(sentiment_data)
            technical_score = self._analyze_technical_factors(technical_data)
            social_score = self._analyze_social_factors(tweet_data)
            risk_score = self._calculate_risk_score(sentiment_data, technical_data, tweet_data)
            
            # Combine scores
            final_score = self._combine_scores(sentiment_score, technical_score, social_score)
            
            # Make decision based on combined analysis
            decision = self._generate_decision(final_score, sentiment_data, technical_data, 
                                             tweet_data, token, risk_score)
            
            # Apply risk management filters
            decision = self._apply_risk_management(decision, technical_data, sentiment_data)
            
            logger.info(f"Trading decision for {token}: {decision.action} "
                       f"(confidence: {decision.confidence:.2f}, risk: {decision.risk_level})")
            
            return decision
            
        except Exception as e:
            logger.error(f"Failed to make trading decision: {e}")
            return self._create_hold_decision("Decision engine error")
    
    def _analyze_sentiment_factors(self, sentiment_data: Dict) -> float:
        if not sentiment_data or sentiment_data.get('analysis_method') == 'fallback':
            return 0.0
        
        sentiment = sentiment_data.get('overall_sentiment', 0.0)
        confidence = sentiment_data.get('confidence', 0.0)
        impact = sentiment_data.get('impact_level', 'low')
        
        # Weight sentiment by confidence and impact
        impact_multiplier = {'low': 0.5, 'medium': 1.0, 'high': 1.5}.get(impact, 1.0)
        
        return sentiment * confidence * impact_multiplier
    
    def _analyze_technical_factors(self, technical_data: Dict) -> float:
        if not technical_data or 'error' in technical_data:
            return 0.0
        
        score = 0.0
        factors = 0
        
        # RSI analysis
        rsi = technical_data.get('rsi', 50)
        if rsi < 30:  # Oversold
            score += 0.3
        elif rsi > 70:  # Overbought
            score -= 0.3
        factors += 1
        
        # MACD analysis
        macd_data = technical_data.get('macd', {})
        if macd_data.get('macd', 0) > macd_data.get('macd_signal', 0):
            score += 0.2
        else:
            score -= 0.2
        factors += 1
        
        # Support/Resistance analysis
        sr_data = technical_data.get('support_resistance', {})
        support_dist = sr_data.get('support_distance', 0)
        resistance_dist = sr_data.get('resistance_distance', 0)
        
        if support_dist < 0.02:  # Near support
            score += 0.25
        elif resistance_dist < 0.02:  # Near resistance
            score -= 0.25
        factors += 1
        
        # Volume analysis
        volume_data = technical_data.get('volume_analysis', {})
        volume_ratio = volume_data.get('volume_ratio', 1.0)
        if volume_ratio > 1.5:  # High volume
            score += 0.15
        factors += 1
        
        # Moving averages
        ma_data = technical_data.get('moving_averages', {})
        current_price = technical_data.get('current_price', 0)
        sma_20 = ma_data.get('sma_20', current_price)
        
        if current_price > sma_20:
            score += 0.1
        else:
            score -= 0.1
        factors += 1
        
        return score / factors if factors > 0 else 0.0
    
    def _analyze_social_factors(self, tweet_data: Dict) -> float:
        score = 0.0
        
        # Tweet engagement
        metrics = tweet_data.get('metrics', {})
        likes = metrics.get('like_count', 0)
        retweets = metrics.get('retweet_count', 0)
        
        engagement_score = (likes + retweets * 2) / 1000  # Normalize
        score += min(engagement_score, 0.3)  # Cap at 0.3
        
        # KOL influence (based on username)
        username = tweet_data.get('username', '')
        influence_multiplier = {
            'elonmusk': 2.0,
            'VitalikButerin': 1.8,
            'CZ_Binance': 1.5,
            'satoshilite': 1.3,
            'DocumentingBTC': 1.2,
            'PlanB_99': 1.2,
            'APompliano': 1.1
        }.get(username, 1.0)
        
        score *= influence_multiplier
        
        # Tweet recency
        tweet_age = time.time() - tweet_data.get('timestamp', 0)
        if tweet_age < 300:  # Less than 5 minutes
            score *= 1.2
        elif tweet_age < 3600:  # Less than 1 hour
            score *= 1.0
        else:
            score *= 0.8
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_risk_score(self, sentiment_data: Dict, technical_data: Dict, 
                            tweet_data: Dict) -> float:
        risk = 0.0
        
        # Market volatility risk
        volatility = technical_data.get('volatility', 0)
        if volatility > 5:  # High volatility
            risk += 0.3
        
        # Sentiment confidence risk
        confidence = sentiment_data.get('confidence', 1.0)
        if confidence < 0.6:
            risk += 0.2
        
        # Technical uncertainty risk
        signals = technical_data.get('trading_signals', {})
        conflicting_signals = 0
        total_signals = 0
        
        for signal in signals.values():
            if signal not in ['neutral', 'hold']:
                total_signals += 1
                if 'sell' in signal or 'bear' in signal or 'over' in signal:
                    conflicting_signals += 1
        
        if total_signals > 0 and conflicting_signals / total_signals > 0.5:
            risk += 0.2
        
        # Recent price movement risk
        price_change = abs(technical_data.get('price_change_24h', 0))
        if price_change > 10:  # Large recent movement
            risk += 0.2
        
        return min(risk, 1.0)
    
    def _combine_scores(self, sentiment: float, technical: float, social: float) -> float:
        # Weighted combination with sentiment having highest weight
        weights = {'sentiment': 0.5, 'technical': 0.3, 'social': 0.2}
        
        return (sentiment * weights['sentiment'] + 
                technical * weights['technical'] + 
                social * weights['social'])
    
    def _generate_decision(self, final_score: float, sentiment_data: Dict, 
                         technical_data: Dict, tweet_data: Dict, token: str, 
                         risk_score: float) -> TradingDecision:
        
        reasoning = []
        
        # Determine action based on score
        if final_score >= 0.3:
            action = 'buy'
            reasoning.append(f"Strong positive signal (score: {final_score:.2f})")
        elif final_score >= 0.1:
            action = 'buy'
            reasoning.append(f"Moderate positive signal (score: {final_score:.2f})")
        elif final_score <= -0.3:
            action = 'sell'
            reasoning.append(f"Strong negative signal (score: {final_score:.2f})")
        elif final_score <= -0.1:
            action = 'sell'
            reasoning.append(f"Moderate negative signal (score: {final_score:.2f})")
        else:
            action = 'hold'
            reasoning.append(f"Neutral signal (score: {final_score:.2f})")
        
        # Calculate confidence
        confidence = min(abs(final_score) + 0.3, 1.0)
        
        # Adjust confidence based on risk
        confidence *= (1 - risk_score * 0.5)
        
        # Determine position size
        base_amount = settings.default_trade_amount_usdt
        position_multiplier = sentiment_data.get('position_size_multiplier', 1.0)
        position_size = base_amount * position_multiplier * confidence
        
        # Risk level
        if risk_score < 0.3:
            risk_level = 'low'
        elif risk_score < 0.6:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        # Add specific reasoning
        if sentiment_data.get('impact_level') == 'high':
            reasoning.append("High impact social sentiment")
        
        if technical_data.get('trading_signals', {}).get('overall') != 'hold':
            reasoning.append(f"Technical signals: {technical_data.get('trading_signals', {})}")
        
        if tweet_data.get('username') in ['elonmusk', 'VitalikButerin']:
            reasoning.append("High-influence KOL tweet")
        
        return TradingDecision(
            action=action,
            confidence=confidence,
            position_size_usdt=position_size,
            reasoning=reasoning,
            risk_level=risk_level,
            timeframe='immediate'
        )
    
    def _apply_risk_management(self, decision: TradingDecision, technical_data: Dict, 
                             sentiment_data: Dict) -> TradingDecision:
        
        # Risk filters
        if decision.risk_level == 'high' and decision.confidence < 0.7:
            decision.action = 'hold'
            decision.reasoning.append("High risk, low confidence - holding")
        
        # Market conditions filter
        rsi = technical_data.get('rsi', 50)
        if decision.action == 'buy' and rsi > 80:
            decision.action = 'hold'
            decision.reasoning.append("Extremely overbought - avoiding buy")
        elif decision.action == 'sell' and rsi < 20:
            decision.action = 'hold'
            decision.reasoning.append("Extremely oversold - avoiding sell")
        
        # Position size limits
        max_position = settings.max_position_size_usdt
        if decision.position_size_usdt > max_position:
            decision.position_size_usdt = max_position
            decision.reasoning.append("Position size capped at maximum")
        
        # Minimum position size
        min_position = 10.0  # $10 minimum
        if decision.position_size_usdt < min_position and decision.action != 'hold':
            decision.action = 'hold'
            decision.reasoning.append("Position size below minimum threshold")
        
        return decision
    
    def _is_in_cooldown(self, token: str) -> bool:
        last_trade_time = self.recent_trades.get(token, 0)
        return time.time() - last_trade_time < self.cooldown_period
    
    def _create_hold_decision(self, reason: str) -> TradingDecision:
        return TradingDecision(
            action='hold',
            confidence=0.0,
            position_size_usdt=0.0,
            reasoning=[reason],
            risk_level='low',
            timeframe='immediate'
        )
    
    def record_trade(self, token: str):
        """Record that a trade was executed for cooldown tracking"""
        self.recent_trades[token] = time.time()
    
    def should_execute_trade(self, decision: TradingDecision, min_confidence: float = 0.6) -> bool:
        return (
            decision.action in ['buy', 'sell'] and
            decision.confidence >= min_confidence and
            decision.position_size_usdt > 0
        )