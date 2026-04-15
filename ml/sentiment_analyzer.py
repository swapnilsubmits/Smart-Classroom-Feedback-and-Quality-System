"""
Sentiment analysis module using TextBlob and NLTK.
Provides lightweight NLP for feedback categorization and sentiment scoring.
"""

from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
import re

# Download required NLTK data
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')
    nltk.download('punkt')

sia = SentimentIntensityAnalyzer()


def analyze_sentiment(feedback_text):
    """
    Analyze sentiment of feedback text.
    
    Returns:
        dict: {
            'polarity': float (-1 to 1),
            'subjectivity': float (0 to 1),
            'label': 'negative' | 'neutral' | 'positive',
            'confidence': float (0 to 1)
        }
    """
    # TextBlob analysis
    blob = TextBlob(feedback_text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    
    # VADER sentiment intensity
    scores = sia.polarity_scores(feedback_text)
    
    # Classify sentiment
    if polarity > 0.1:
        label = 'positive'
        confidence = scores['pos']
    elif polarity < -0.1:
        label = 'negative'
        confidence = scores['neg']
    else:
        label = 'neutral'
        confidence = scores['neu']
    
    return {
        'polarity': polarity,
        'subjectivity': subjectivity,
        'label': label,
        'confidence': confidence,
        'vader_compound': scores['compound']
    }


"""
Sentiment analysis module using TextBlob and NLTK.
Provides lightweight NLP for feedback categorization and sentiment scoring.
"""

from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
import re

# Download required NLTK data
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')
    nltk.download('punkt')

sia = SentimentIntensityAnalyzer()


def analyze_sentiment(feedback_text):
    """
    Analyze sentiment of feedback text.

    Returns:
        dict: {
            'polarity': float (-1 to 1),
            'subjectivity': float (0 to 1),
            'label': 'negative' | 'neutral' | 'positive',
            'confidence': float (0 to 1)
        }
    """
    # TextBlob analysis
    blob = TextBlob(feedback_text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    # VADER sentiment intensity
    scores = sia.polarity_scores(feedback_text)

    # Classify sentiment
    if polarity > 0.1:
        label = 'positive'
        confidence = scores['pos']
    elif polarity < -0.1:
        label = 'negative'
        confidence = scores['neg']
    else:
        label = 'neutral'
        confidence = scores['neu']

    return {
        'polarity': polarity,
        'subjectivity': subjectivity,
        'label': label,
        'confidence': confidence,
        'vader_compound': scores['compound']
    }


def extract_key_topics(feedback_text):
    """
    Extract key topics/concerns from feedback.
    Simple keyword-based approach.
    """
    keywords = {
        'teaching': ['teach', 'explain', 'lecture', 'instruction', 'pedagogy'],
        'content': ['content', 'material', 'curriculum', 'topic', 'subject'],
        'clarity': ['clear', 'unclear', 'confusing', 'understandable'],
        'engagement': ['engage', 'boring', 'interesting', 'interactive', 'motivated'],
        'pace': ['pace', 'speed', 'slow', 'fast', 'rushed'],
    }

    text_lower = feedback_text.lower()
    topics = []

    for topic, words in keywords.items():
        if any(word in text_lower for word in words):
            topics.append(topic)

    return topics


def detect_flagged_feedback(feedback_data, avg_rating=None):
    """
    Detect potentially unreliable or suspicious feedback.

    Args:
        feedback_data: dict with feedback structure
        avg_rating: float, course average rating for comparison

    Returns:
        dict: {'flagged': bool, 'reason': str, 'severity': 'low'|'medium'|'high'}
    """
    reasons = []
    severity = 'low'

    # Check for extreme ratings compared to average
    if avg_rating is not None:
        overall_rating = feedback_data.get('overall_experience', {}).get('rating', 3)
        rating_diff = abs(overall_rating - avg_rating)
        if rating_diff > 2.5:
            reasons.append("extreme rating (more than 2.5 points from average)")
            severity = 'high'
        elif rating_diff > 2:
            reasons.append("significant rating deviation from course average")
            if severity == 'low':
                severity = 'medium'

    # Check for very short feedback text
    text = feedback_data.get('overall_experience', {}).get('text', '').strip()
    text_length = len(text)
    if text_length < 5:
        reasons.append("extremely short feedback text (< 5 characters)")
        severity = 'high'
    elif text_length < 15:
        reasons.append("very short feedback text (< 15 characters)")
        if severity == 'low':
            severity = 'medium'

    # Check for spam-like content (repetitive words, excessive punctuation)
    if text:
        words = text.lower().split()
        if words:
            # Count repetitive words
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            max_repetition = max(word_counts.values())
            if max_repetition > len(words) * 0.4:
                reasons.append("highly repetitive content")
                if severity == 'low':
                    severity = 'medium'

            # Excessive punctuation
            punctuation_count = sum(1 for char in text if char in '!@#$%^&*()_+-=[]{}|;:,.<>?')
            if punctuation_count > len(text) * 0.25:
                reasons.append("excessive punctuation (>25% of content)")
                if severity == 'low':
                    severity = 'medium'

            # Check for all caps (shouting)
            if len(text) > 10 and text.isupper():
                reasons.append("all caps text (possible shouting)")
                if severity == 'low':
                    severity = 'medium'

    # Enhanced abusive language detection
    abusive_words = [
        'stupid', 'idiot', 'dumb', 'crap', 'shit', 'damn', 'hell', 'fuck', 'asshole',
        'bastard', 'bitch', 'moron', 'retard', 'loser', 'pathetic', 'worthless',
        'terrible', 'awful', 'horrible', 'suck', 'sucks', 'hate', 'worst'
    ]
    text_lower = text.lower()
    found_abusive = [word for word in abusive_words if word in text_lower]
    if found_abusive:
        reasons.append(f"potentially abusive language detected: {', '.join(found_abusive[:3])}")
        severity = 'high'

    # Check for all minimum ratings (suspicious pattern)
    ratings = []
    rating_categories = [
        'teaching_quality', 'student_engagement', 'content_understanding',
        'doubt_support', 'overall_experience'
    ]

    for category in rating_categories:
        cat_data = feedback_data.get(category, {})
        if isinstance(cat_data, dict):
            # Handle nested ratings
            for key, value in cat_data.items():
                if isinstance(value, int) and 1 <= value <= 5:
                    ratings.append(value)
                elif isinstance(value, str):
                    # Convert participation levels to numeric
                    participation_map = {
                        'very_active': 5, 'active': 4, 'neutral': 3,
                        'passive': 2, 'inactive': 1
                    }
                    if value in participation_map:
                        ratings.append(participation_map[value])
                    # Convert resolution effectiveness to numeric
                    resolution_map = {
                        'excellent': 5, 'good': 4, 'average': 3,
                        'poor': 2, 'no_support': 1
                    }
                    if value in resolution_map:
                        ratings.append(resolution_map[value])
        elif isinstance(cat_data, int) and 1 <= cat_data <= 5:
            ratings.append(cat_data)

    # Check for suspicious rating patterns
    if ratings:
        if all(r <= 2 for r in ratings):
            reasons.append("consistently low ratings across all categories")
            if severity == 'low':
                severity = 'medium'

        if all(r == 5 for r in ratings):
            reasons.append("perfect ratings across all categories")
            if severity == 'low':
                severity = 'medium'

        # Check for alternating pattern (1,5,1,5,1,5...)
        if len(ratings) >= 3:
            alternating = True
            for i in range(1, len(ratings)):
                if abs(ratings[i] - ratings[i-1]) < 3:  # Should alternate between high/low
                    alternating = False
                    break
            if alternating:
                reasons.append("suspicious alternating rating pattern")
                if severity == 'low':
                    severity = 'medium'

    # Check for nonsensical text (random characters, no spaces)
    if text and len(text) > 20:
        words = text.split()
        if len(words) == 1 and not any(char.isspace() for char in text):
            reasons.append("text appears to be random characters or spam")
            severity = 'high'

    return {
        'flagged': len(reasons) > 0,
        'reason': '; '.join(reasons) if reasons else '',
        'severity': severity
    }
