import re
import json
import openai
from typing import Dict, List, Optional
from loguru import logger
import asyncio
import aiohttp
from .config import settings

class SentimentAnalyzer:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
        self.deepseek_api_key = settings.deepseek_api_key
        self.deepseek_base_url = "https://api.deepseek.com/v1"
        
    async def analyze_sentiment(self, text: str, tokens: List[str]) -> Dict[str, float]:
        # Try DeepSeek first (cheaper), fallback to OpenAI GPT-4
        try:
            result = await self._analyze_with_deepseek(text, tokens)
            if result:
                return result
        except Exception as e:
            logger.warning(f"DeepSeek analysis failed: {e}, falling back to OpenAI")
        
        try:
            return await self._analyze_with_openai(text, tokens)
        except Exception as e:
            logger.error(f"Both sentiment analysis methods failed: {e}")
            return self._fallback_sentiment()
    
    async def _analyze_with_deepseek(self, text: str, tokens: List[str]) -> Optional[Dict]:
        prompt = self._build_sentiment_prompt(text, tokens)
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a crypto market sentiment analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 200
            }
            
            async with session.post(f"{self.deepseek_base_url}/chat/completions", 
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    return self._parse_sentiment_response(content)
                else:
                    logger.error(f"DeepSeek API error: {response.status}")
                    return None
    
    async def _analyze_with_openai(self, text: str, tokens: List[str]) -> Dict:
        prompt = self._build_sentiment_prompt(text, tokens)
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a crypto market sentiment analysis expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        content = response.choices[0].message.content
        return self._parse_sentiment_response(content)
    
    def _build_sentiment_prompt(self, text: str, tokens: List[str]) -> str:
        return f"""
Analyze the sentiment of this crypto-related social media post for the tokens: {', '.join(tokens)}

Post: "{text}"

Please provide a JSON response with the following structure:
{{
    "overall_sentiment": <float between -1.0 and 1.0>,
    "confidence": <float between 0.0 and 1.0>,
    "classification": "<bullish|bearish|neutral>",
    "impact_level": "<low|medium|high>",
    "trading_signal": "<strong_buy|buy|hold|sell|strong_sell>",
    "key_factors": ["<factor1>", "<factor2>", ...],
    "token_specific": {{
        "{tokens[0] if tokens else 'BTC'}": {{"sentiment": <float>, "confidence": <float>}}
    }}
}}

Consider:
1. Crypto-specific terminology and slang
2. Emojis and their crypto context (🚀=bullish, 📉=bearish)
3. Author influence and follower engagement
4. Market timing and context
5. Technical analysis mentions
6. Fundamental analysis references

Respond only with the JSON, no additional text.
"""
    
    def _parse_sentiment_response(self, content: str) -> Dict:
        try:
            # Clean the response and extract JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            result = json.loads(content)
            
            # Validate and sanitize the response
            return {
                'overall_sentiment': max(-1.0, min(1.0, float(result.get('overall_sentiment', 0.0)))),
                'confidence': max(0.0, min(1.0, float(result.get('confidence', 0.5)))),
                'classification': result.get('classification', 'neutral'),
                'impact_level': result.get('impact_level', 'low'),
                'trading_signal': result.get('trading_signal', 'hold'),
                'key_factors': result.get('key_factors', []),
                'token_specific': result.get('token_specific', {}),
                'analysis_method': 'llm'
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse sentiment response: {e}")
            return self._fallback_sentiment()
    
    def _fallback_sentiment(self) -> Dict:
        return {
            'overall_sentiment': 0.0,
            'confidence': 0.1,
            'classification': 'neutral',
            'impact_level': 'low',
            'trading_signal': 'hold',
            'key_factors': ['analysis_failed'],
            'token_specific': {},
            'analysis_method': 'fallback'
        }
    
    def should_trade(self, sentiment: Dict, min_confidence: float = 0.6) -> bool:
        return (
            sentiment['confidence'] >= min_confidence and
            sentiment['impact_level'] in ['medium', 'high'] and
            sentiment['trading_signal'] in ['strong_buy', 'buy', 'strong_sell', 'sell']
        )
    
    def get_position_size_multiplier(self, sentiment: Dict) -> float:
        """Returns a multiplier for position size based on confidence and impact"""
        base_multiplier = 1.0
        
        if sentiment['impact_level'] == 'high':
            base_multiplier *= 1.5
        elif sentiment['impact_level'] == 'low':
            base_multiplier *= 0.5
        
        confidence_multiplier = sentiment['confidence']
        
        return min(2.0, base_multiplier * confidence_multiplier)