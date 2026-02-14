"""Sentiment analysis module for Smart Invest."""

from aim.sentiment.scorer import SentimentScorer, update_sentiment_to_database

__all__ = ["SentimentScorer", "update_sentiment_to_database"]
