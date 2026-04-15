"""
Simplified Flask app for the Smart Classroom Feedback project.
This version meets the beginner-friendly requirements:
- Connects to local MongoDB at mongodb://localhost:27017/
- Uses database `classroom_db` and collection `feedbacks`
- Provides a POST `/submit-feedback` route that accepts JSON
  and stores course, rating, feedback_text, sentiment_score, timestamp
- Performs basic validation and error handling
- Uses TextBlob to compute a sentiment polarity score
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
from textblob import TextBlob
import json
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.sentiment_analyzer import analyze_sentiment, extract_key_topics, detect_flagged_feedback

app = Flask(__name__)
CORS(app)  # allow cross-origin requests from frontend files

# log each request path for debugging
@app.before_request
def log_request():
    app.logger.debug('%s %s', request.method, request.path)

# ------------------------------------------------------------------
# Permanent JSON file storage + MongoDB with fallback
# ------------------------------------------------------------------
FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), 'feedbacks.json')
memory_store = []
use_mongo = False

# Load from JSON file if it exists
def load_from_file():
    global memory_store
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r') as f:
                memory_store = json.load(f)
                app.logger.info('Loaded %d feedbacks from file', len(memory_store))
        except Exception as e:
            app.logger.error('Failed to load JSON file: %s', e)
            memory_store = []
    else:
        memory_store = []

# Save to JSON file
def save_to_file():
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(memory_store, f, default=str, indent=2)
            app.logger.info('Saved %d feedbacks to file', len(memory_store))
    except Exception as e:
        app.logger.error('Failed to save JSON file: %s', e)


def parse_timestamp(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def normalize_feedback_timestamps(feedbacks):
    for feedback in feedbacks:
        if isinstance(feedback.get('timestamp'), str):
            parsed = parse_timestamp(feedback['timestamp'])
            if parsed:
                feedback['timestamp'] = parsed
    return feedbacks


def compute_course_analytics(course_feedbacks, period='all'):
    course_feedbacks = [f for f in course_feedbacks if isinstance(f.get('feedback'), dict) and isinstance(f.get('sentiment'), dict)]
    normalize_feedback_timestamps(course_feedbacks)

    now = datetime.utcnow()
    if period == 'week':
        cutoff = now - timedelta(days=7)
    elif period == 'month':
        cutoff = now - timedelta(days=30)
    elif period == 'semester':
        cutoff = now - timedelta(days=120)
    else:
        cutoff = None

    if cutoff:
        course_feedbacks = [f for f in course_feedbacks if f.get('timestamp') and f['timestamp'] >= cutoff]

    total_feedbacks = len(course_feedbacks)
    if total_feedbacks == 0:
        return None

    avg_overall_rating = sum(f['feedback']['overall_experience']['rating'] for f in course_feedbacks) / total_feedbacks

    categories = {
        'teaching_quality': ['clarity', 'pace', 'explanation'],
        'student_engagement': ['interaction'],
        'content_understanding': ['difficulty', 'clarity']
    }

    category_averages = {}
    for category, fields in categories.items():
        field_averages = {}
        for field in fields:
            values = [f['feedback'][category][field] for f in course_feedbacks if field in f['feedback'][category]]
            if values:
                field_averages[field] = sum(values) / len(values)
        if field_averages:
            category_averages[category] = field_averages

    sentiment_dist = {'positive': 0, 'neutral': 0, 'negative': 0}
    for f in course_feedbacks:
        label = f['sentiment'].get('label')
        if label in sentiment_dist:
            sentiment_dist[label] += 1

    participation_dist = {}
    for f in course_feedbacks:
        part = f['feedback']['student_engagement'].get('participation')
        if part:
            participation_dist[part] = participation_dist.get(part, 0) + 1

    doubt_dist = {}
    for f in course_feedbacks:
        res = f['feedback']['doubt_support'].get('resolution')
        if res:
            doubt_dist[res] = doubt_dist.get(res, 0) + 1

    anonymous_count = sum(1 for f in course_feedbacks if f.get('anonymous', False))
    identified_count = total_feedbacks - anonymous_count

    flagged_feedbacks = [f for f in course_feedbacks if f.get('flagged', False)]
    flagged_count = len(flagged_feedbacks)
    flag_severity_dist = {}
    for f in flagged_feedbacks:
        severity = f.get('flag_severity', 'low')
        flag_severity_dist[severity] = flag_severity_dist.get(severity, 0) + 1

    seven_days_ago = now - timedelta(days=7)
    recent_feedbacks = [f for f in course_feedbacks if f.get('timestamp') and f['timestamp'] >= seven_days_ago]
    recent_count = len(recent_feedbacks)

    daily_submissions = {}
    for f in course_feedbacks:
        day = f.get('timestamp').date() if f.get('timestamp') else None
        if day:
            daily_submissions[day] = daily_submissions.get(day, 0) + 1

    submission_trends = {str(day): count for day, count in sorted(daily_submissions.items())}

    return {
        'course_id': course_feedbacks[0].get('course_id') if course_feedbacks else None,
        'total_feedbacks': total_feedbacks,
        'avg_overall_rating': round(avg_overall_rating, 2),
        'category_averages': category_averages,
        'sentiment_distribution': sentiment_dist,
        'participation_distribution': participation_dist,
        'doubt_support_distribution': doubt_dist,
        'anonymous_breakdown': {
            'anonymous_count': anonymous_count,
            'identified_count': identified_count,
            'anonymous_percentage': round((anonymous_count / total_feedbacks) * 100, 1) if total_feedbacks else 0
        },
        'flagged_stats': {
            'total_flagged': flagged_count,
            'flagged_percentage': round((flagged_count / total_feedbacks) * 100, 1) if total_feedbacks else 0,
            'severity_distribution': flag_severity_dist
        },
        'activity_stats': {
            'recent_feedbacks': recent_count,
            'submission_trends': submission_trends
        },
        'trends': submission_trends,
        'last_updated': datetime.utcnow().isoformat()
    }


# Try MongoDB; fall back to file storage
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.admin.command('ping')
    db = client["classroom_db"]
    feedbacks = db["feedbacks"]
    use_mongo = True
    app.logger.info('Connected to MongoDB')
except Exception as e:
    app.logger.warning('MongoDB unavailable (%s); using file storage', e)
    use_mongo = False
    feedbacks = None
    # Load from file on startup
    load_from_file()


# ------------------------------------------------------------------
# helper function for request validation
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# helper function for request validation
# ------------------------------------------------------------------

def validate_payload(data):
    """Return (clean_data, error_message).
    clean_data is a dict when validation succeeds, otherwise None.
    """
    if not data:
        return None, "Request must contain JSON body"

    course_id = data.get("course_id")
    student_id = data.get("student_id")
    anonymous = data.get("anonymous", False)
    feedback = data.get("feedback")

    missing = []
    if not course_id:
        missing.append("course_id")
    if not anonymous and not student_id:
        missing.append("student_id")
    if not feedback or not isinstance(feedback, dict):
        missing.append("feedback")

    if missing:
        return None, "Missing fields: " + ", ".join(missing)

    # Validate feedback structure
    required_categories = ['teaching_quality', 'student_engagement', 'content_understanding', 'doubt_support', 'overall_experience']
    for category in required_categories:
        if category not in feedback:
            return None, f"Missing feedback category: {category}"

    # Validate ratings are integers 1-5
    rating_fields = [
        'teaching_quality.clarity', 'teaching_quality.pace', 'teaching_quality.explanation',
        'student_engagement.interaction', 'content_understanding.difficulty', 'content_understanding.clarity',
        'overall_experience.rating'
    ]

    for field_path in rating_fields:
        keys = field_path.split('.')
        value = feedback
        for key in keys:
            value = value.get(key)
            if value is None:
                return None, f"Missing rating field: {field_path}"

        if not isinstance(value, int) or value < 1 or value > 5:
            return None, f"Rating {field_path} must be integer 1-5"

    # Validate multiple choice fields
    mc_fields = {
        'student_engagement.participation': ['very_active', 'active', 'neutral', 'passive', 'inactive'],
        'doubt_support.resolution': ['excellent', 'good', 'average', 'poor', 'no_support']
    }

    for field_path, options in mc_fields.items():
        keys = field_path.split('.')
        value = feedback
        for key in keys[:-1]:
            value = value.get(key, {})
        field_value = value.get(keys[-1])

        # Normalize numeric participation values to accepted status labels
        if field_path == 'student_engagement.participation' and isinstance(field_value, int):
            participation_map = {
                5: 'very_active',
                4: 'active',
                3: 'neutral',
                2: 'passive',
                1: 'inactive'
            }
            if field_value in participation_map:
                value[keys[-1]] = participation_map[field_value]
                field_value = participation_map[field_value]

        if not field_value or field_value not in options:
            return None, f"Invalid option for {field_path}. Must be one of: {', '.join(options)}"

    # Validate overall experience text
    overall_text = feedback.get('overall_experience', {}).get('text', '').strip()
    if not overall_text:
        return None, "Overall experience text feedback is required"

    return {
        "course_id": course_id,
        "student_id": student_id if not anonymous else None,
        "anonymous": anonymous,
        "feedback": feedback
    }, None

# ------------------------------------------------------------------
# API endpoint
# ------------------------------------------------------------------

@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    """Receive feedback JSON, validate, compute sentiment, and store."""
    data = request.get_json()
    clean, error = validate_payload(data)
    if error:
        return jsonify({"success": False, "error": error}), 400

    # Check for duplicate submissions
    if not clean["anonymous"]:
        # For identified users: check by student_id and course within last 24 hours
        yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        existing = None
        if use_mongo:
            existing = feedbacks.find_one({
                "student_id": clean["student_id"],
                "course_id": clean["course_id"],
                "timestamp": {"$gte": yesterday}
            })
        else:
            existing = next((f for f in memory_store
                           if f.get("student_id") == clean["student_id"]
                           and f.get("course_id") == clean["course_id"]
                           and datetime.fromisoformat(f["timestamp"]) >= yesterday), None)

        if existing:
            return jsonify({"success": False, "error": "You have already submitted feedback for this course today"}), 409
    else:
        # For anonymous users: use IP + course + time window (more restrictive)
        client_ip = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'unknown')
        # Create a session-like identifier for anonymous users
        session_id = f"{client_ip}_{clean['course_id']}_{datetime.utcnow().strftime('%Y-%m-%d-%H')}"

        # Check for submissions from same IP/course within last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        existing = None
        if use_mongo:
            existing = feedbacks.find_one({
                "anonymous": True,
                "course_id": clean["course_id"],
                "session_id": session_id,
                "timestamp": {"$gte": one_hour_ago}
            })
        else:
            existing = next((f for f in memory_store
                           if f.get("anonymous") == True
                           and f.get("course_id") == clean["course_id"]
                           and f.get("session_id") == session_id
                           and datetime.fromisoformat(f["timestamp"]) >= one_hour_ago), None)

        if existing:
            return jsonify({"success": False, "error": "Anonymous feedback already submitted from this device for this course recently. Please wait before submitting again."}), 429

    # Analyze sentiment and extract topics
    feedback_text = clean["feedback"]["overall_experience"]["text"]
    sentiment = analyze_sentiment(feedback_text)
    topics = extract_key_topics(feedback_text)

    # Get course average rating for flagging
    avg_rating = None
    if use_mongo:
        pipeline = [
            {"$match": {"course_id": clean["course_id"]}},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$feedback.overall_experience.rating"}}}
        ]
        result = list(feedbacks.aggregate(pipeline))
        if result:
            avg_rating = result[0]["avg_rating"]

    # Detect if feedback should be flagged
    flag_info = detect_flagged_feedback(clean["feedback"], avg_rating)

    doc = {
        "course_id": clean["course_id"],
        "student_id": clean["student_id"],
        "anonymous": clean["anonymous"],
        "session_id": session_id if clean["anonymous"] else None,
        "feedback": clean["feedback"],
        "sentiment": sentiment,
        "topics": topics,
        "flagged": flag_info["flagged"],
        "flag_reason": flag_info["reason"],
        "flag_severity": flag_info.get("severity", "low"),
        "timestamp": datetime.utcnow(),
    }

    try:
        if use_mongo:
            result = feedbacks.insert_one(doc)
            return jsonify({"success": True, "id": str(result.inserted_id)}), 201
        else:
            # file storage fallback - persist to JSON file
            doc["_id"] = str(len(memory_store) + 1)
            memory_store.append(doc)
            save_to_file()  # save immediately so data persists
            app.logger.info("Feedback stored in file (id=%s)", doc["_id"])
            return jsonify({"success": True, "id": doc["_id"], "note": "(file-stored - permanent)"}), 201
    except Exception as exc:
        # log exception on server side for debugging
        app.logger.error("Insert failed: %s", exc)
        return (
            jsonify(
                {"success": False, "error": "Database error, try again later."}
            ),
            500,
        )


# simple route to list all feedbacks (used by dashboard)
@app.route("/health", methods=["GET"])
def health_check():
    """Simple API health check for frontend connectivity."""
    return jsonify({"status": "ok", "service": "feedback-backend"}), 200


@app.route("/api/feedback/list", methods=["GET"])
def list_feedbacks():
    """Return feedback documents with optional filtering.
    Supports filtering by course_id, student_id, and flagged status.
    """
    try:
        course_id = request.args.get('course_id')
        student_id = request.args.get('student_id')
        flagged = request.args.get('flagged')

        # Build query filter
        query_filter = {}
        if course_id:
            query_filter['course_id'] = course_id
        if student_id:
            query_filter['student_id'] = student_id
        if flagged is not None:
            query_filter['flagged'] = flagged.lower() == 'true'

        if use_mongo:
            docs = list(feedbacks.find(query_filter))
            for d in docs:
                d["_id"] = str(d.get("_id"))
            return jsonify({"feedbacks": docs})
        else:
            # Filter in-memory store
            filtered_feedbacks = memory_store
            if course_id:
                filtered_feedbacks = [f for f in filtered_feedbacks if f.get('course_id') == course_id]
            if student_id:
                filtered_feedbacks = [f for f in filtered_feedbacks if f.get('student_id') == student_id]
            if flagged is not None:
                is_flagged = flagged.lower() == 'true'
                filtered_feedbacks = [f for f in filtered_feedbacks if f.get('flagged', False) == is_flagged]

            return jsonify({"feedbacks": filtered_feedbacks})
    except Exception as exc:
        app.logger.error("Error listing feedbacks: %s", exc)
        return jsonify({"feedbacks": []}), 500


@app.route("/api/analytics/course/<course_id>", methods=["GET"])
def get_course_analytics(course_id):
    """Return aggregated analytics for a specific course."""
    try:
        period = request.args.get('period', 'all')

        if use_mongo:
            # Get all feedbacks for the course
            course_feedbacks = list(feedbacks.find({"course_id": course_id}))

            if not course_feedbacks:
                return jsonify({"error": "No feedback found for this course"}), 404

            # Filter by time period
            now = datetime.utcnow()
            if period == 'week':
                cutoff = now - timedelta(days=7)
            elif period == 'month':
                cutoff = now - timedelta(days=30)
            elif period == 'semester':
                cutoff = now - timedelta(days=120)  # Approximate 4 months
            else:  # 'all'
                cutoff = None

            if cutoff:
                course_feedbacks = [f for f in course_feedbacks if f["timestamp"] >= cutoff]

            # Calculate aggregations
            total_feedbacks = len(course_feedbacks)
            if total_feedbacks == 0:
                return jsonify({"error": "No feedback found for the selected period"}), 404

            avg_overall_rating = sum(f["feedback"]["overall_experience"]["rating"] for f in course_feedbacks) / total_feedbacks

            # Category-wise averages
            categories = {
                "teaching_quality": ["clarity", "pace", "explanation"],
                "student_engagement": ["interaction"],
                "content_understanding": ["difficulty", "clarity"]
            }

            category_averages = {}
            for category, fields in categories.items():
                field_averages = {}
                for field in fields:
                    values = [f["feedback"][category][field] for f in course_feedbacks if field in f["feedback"][category]]
                    if values:
                        field_averages[field] = sum(values) / len(values)
                if field_averages:
                    category_averages[category] = field_averages

            # Sentiment distribution
            sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
            for f in course_feedbacks:
                label = f["sentiment"]["label"]
                sentiment_dist[label] += 1

            # Participation distribution
            participation_dist = {}
            for f in course_feedbacks:
                part = f["feedback"]["student_engagement"]["participation"]
                participation_dist[part] = participation_dist.get(part, 0) + 1

            # Doubt support distribution
            doubt_dist = {}
            for f in course_feedbacks:
                res = f["feedback"]["doubt_support"]["resolution"]
                doubt_dist[res] = doubt_dist.get(res, 0) + 1

            # Anonymous vs identified breakdown
            anonymous_count = sum(1 for f in course_feedbacks if f.get("anonymous", False))
            identified_count = total_feedbacks - anonymous_count

            # Flagged feedback statistics
            flagged_feedbacks = [f for f in course_feedbacks if f.get("flagged", False)]
            flagged_count = len(flagged_feedbacks)
            flag_severity_dist = {}
            for f in flagged_feedbacks:
                severity = f.get("flag_severity", "low")
                flag_severity_dist[severity] = flag_severity_dist.get(severity, 0) + 1

            # Recent activity (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_feedbacks = [f for f in course_feedbacks if f["timestamp"] >= seven_days_ago]
            recent_count = len(recent_feedbacks)

            # Response rate trends (daily submissions)
            daily_submissions = {}
            for f in course_feedbacks:
                day = f["timestamp"].date()
                daily_submissions[day] = daily_submissions.get(day, 0) + 1

            submission_trends = {str(day): count for day, count in sorted(daily_submissions.items())}

            return jsonify({
                "course_id": course_id,
                "total_feedbacks": total_feedbacks,
                "avg_overall_rating": round(avg_overall_rating, 2),
                "category_averages": category_averages,
                "sentiment_distribution": sentiment_dist,
                "participation_distribution": participation_dist,
                "doubt_support_distribution": doubt_dist,
                "anonymous_breakdown": {
                    "anonymous_count": anonymous_count,
                    "identified_count": identified_count,
                    "anonymous_percentage": round((anonymous_count / total_feedbacks) * 100, 1) if total_feedbacks > 0 else 0
                },
                "flagged_stats": {
                    "total_flagged": flagged_count,
                    "flagged_percentage": round((flagged_count / total_feedbacks) * 100, 1) if total_feedbacks > 0 else 0,
                    "severity_distribution": flag_severity_dist
                },
                "activity_stats": {
                    "recent_feedbacks": recent_count,
                    "submission_trends": submission_trends
                },
                "trends": submission_trends,
                "last_updated": datetime.utcnow().isoformat()
            })

        else:
            course_feedbacks = [f for f in memory_store if f.get("course_id") == course_id]
            analytics = compute_course_analytics(course_feedbacks, period)
            if not analytics:
                return jsonify({"error": "No feedback found for this course"}), 404
            return jsonify(analytics)

    except Exception as exc:
        app.logger.error("Error getting analytics: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


# run the app when executed directly
if __name__ == "__main__":
    app.run(port=5000, debug=True)
