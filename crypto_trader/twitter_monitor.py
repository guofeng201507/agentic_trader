import tweepy
import asyncio
import time
from typing import List, Dict, Optional
from loguru import logger
from .config import settings
from .token_detector import TokenDetector
from .sentiment_analyzer import SentimentAnalyzer

class TwitterMonitor:
    def __init__(self):
        self.setup_twitter_api()
        self.token_detector = TokenDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.last_tweet_ids = {}
        
    def setup_twitter_api(self):
        try:
            # Twitter API v2 with Bearer Token
            self.client = tweepy.Client(
                bearer_token=settings.twitter_bearer_token,
                consumer_key=settings.twitter_api_key,
                consumer_secret=settings.twitter_api_secret,
                access_token=settings.twitter_access_token,
                access_token_secret=settings.twitter_access_token_secret,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise
    
    def get_user_id(self, username: str) -> Optional[str]:
        try:
            user = self.client.get_user(username=username)
            return user.data.id if user.data else None
        except Exception as e:
            logger.error(f"Failed to get user ID for {username}: {e}")
            return None
    
    def get_recent_tweets(self, user_id: str, count: int = 10) -> List[Dict]:
        try:
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=count,
                tweet_fields=['created_at', 'public_metrics', 'context_annotations']
            )
            
            if not tweets.data:
                return []
            
            tweet_data = []
            for tweet in tweets.data:
                tweet_info = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'metrics': tweet.public_metrics,
                    'user_id': user_id
                }
                tweet_data.append(tweet_info)
            
            return tweet_data
            
        except Exception as e:
            logger.error(f"Failed to get tweets for user {user_id}: {e}")
            return []
    
    def process_tweet(self, tweet: Dict, username: str) -> Optional[Dict]:
        text = tweet['text'].upper()
        
        # Detect crypto tokens in the tweet
        detected_tokens = self.token_detector.detect_tokens(text)
        if not detected_tokens:
            return None
        
        # Analyze sentiment
        sentiment_scores = self.sentiment_analyzer.analyze_sentiment(tweet['text'])
        
        # Check if this is a new tweet
        tweet_id = tweet['id']
        if username in self.last_tweet_ids and tweet_id <= self.last_tweet_ids[username]:
            return None
        
        self.last_tweet_ids[username] = tweet_id
        
        processed_tweet = {
            'tweet_id': tweet_id,
            'username': username,
            'text': tweet['text'],
            'created_at': tweet['created_at'],
            'detected_tokens': detected_tokens,
            'sentiment_scores': sentiment_scores,
            'metrics': tweet['metrics'],
            'timestamp': time.time()
        }
        
        logger.info(f"Processed tweet from {username}: {detected_tokens} - Sentiment: {sentiment_scores}")
        return processed_tweet
    
    async def monitor_kols(self) -> List[Dict]:
        all_processed_tweets = []
        
        for username in settings.kol_usernames:
            try:
                user_id = self.get_user_id(username)
                if not user_id:
                    logger.warning(f"Could not find user ID for {username}")
                    continue
                
                tweets = self.get_recent_tweets(user_id, count=5)
                
                for tweet in tweets:
                    processed = self.process_tweet(tweet, username)
                    if processed:
                        all_processed_tweets.append(processed)
                
                # Rate limiting
                await asyncio.sleep(settings.api_rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error monitoring {username}: {e}")
                continue
        
        return all_processed_tweets
    
    def is_significant_tweet(self, tweet: Dict) -> bool:
        metrics = tweet.get('metrics', {})
        retweets = metrics.get('retweet_count', 0)
        likes = metrics.get('like_count', 0)
        
        # Consider tweets with high engagement as more significant
        engagement_score = retweets * 2 + likes
        return engagement_score > 100  # Threshold for significant tweets