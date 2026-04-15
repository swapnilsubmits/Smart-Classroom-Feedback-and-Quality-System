# Copilot Instructions for Classroom Feedback System

## Project Overview
This is a full-stack web application for real-time student feedback collection and AI-powered sentiment analysis. The system consists of three main layers: Flask backend API, Frontend UI, and ML sentiment analysis service.

**Key Components:**
- **Backend** (`backend/app.py`): Flask REST API with MongoDB integration
- **Frontend** (`frontend/`): Vanilla JavaScript with Chart.js for analytics
- **ML Pipeline** (`ml/sentiment_analyzer.py`): NLTK + TextBlob sentiment analysis

## Architecture & Data Flow

### Request Flow
1. **Feedback Submission**: Student submits feedback → Frontend sends POST to `/api/feedback/submit`
2. **Storage**: Flask validates and inserts to MongoDB `feedbacks` collection
3. **Sentiment Analysis**: Background job calls `sentiment_analyzer.analyze_sentiment()` (currently synchronous, plan for async)
4. **Analytics Query**: Dashboard calls `/api/analytics/course/<course_id>` with MongoDB aggregation pipeline

### Database Schema (MongoDB)
```javascript
// feedbacks collection
{
  _id: ObjectId,
  course_id: "CS101",
  student_id: "student_abc123",
  feedback_text: "String",
  rating: 1-5,
  sentiment: { polarity, subjectivity, label, confidence },
  topics: ["teaching", "clarity"],  // extracted keywords
  timestamp: Date
}

// analytics collection (cached aggregations)
{
  course_id: "CS101",
  avg_rating: 4.2,
  sentiment_distribution: { positive: 60, neutral: 30, negative: 10 },
  updated_at: Date
}
```

## Critical Patterns & Conventions

### 1. **API Endpoint Structure**
- Pattern: `/api/<resource>/<action>` or `/api/<resource>/<id>`
- All responses: JSON with consistent error format
- All submissions expect JSON payloads with validation
- Example: `POST /api/feedback/submit` with `{course_id, student_id, feedback_text, rating}`

### 2. **Sentiment Analysis Workflow** 
The `sentiment_analyzer.py` module uses hybrid approach:
- **TextBlob**: Polarity (-1 to 1) and subjectivity (0 to 1)
- **NLTK VADER**: Compound score for intensity; handles slang/emojis
- **Classification**: If polarity > 0.1 → positive; < -0.1 → negative; else neutral
- **Topic Extraction**: Keyword matching for categorization (teaching, content, clarity, engagement, pace)

**Pattern**: Always call both engines and combine results for robustness. See `ml/sentiment_analyzer.py:analyze_sentiment()`.

### 3. **Role-Based Logic** (Future component, not yet implemented)
- **Students**: Submit feedback, view personal analytics
- **Faculty**: View course-level dashboards, export reports
- **Admins**: System-wide analytics, user management
- Plan: Middleware check on Flask routes using JWT tokens

### 4. **Frontend Tab Navigation**
Frontend uses simple tab switching with dynamic content loading:
- Show/hide tabs via `showTab(tabName)`
- Load data on demand (e.g., `loadAnalytics()` when dashboard tab opens)
- Store user state in localStorage (student_id, current_course)

## Developer Workflows

### Local Setup
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py  # Runs on http://localhost:5000

# ML (standalone testing)
cd ml
pip install -r requirements.txt
python -c "from sentiment_analyzer import analyze_sentiment; print(analyze_sentiment('Great class!'))"

# Frontend: Open frontend/index.html in browser
# Ensure backend is running at http://localhost:5000
```

### MongoDB Requirements
- Requires running MongoDB instance (local or Atlas)
- Set `MONGO_URI` environment variable (defaults to `mongodb://localhost:27017/`)
- Database auto-creates on first write: `classroom_feedback`

### Testing Sentiment Analysis
Test the sentiment module directly before integrating:
```python
from ml.sentiment_analyzer import analyze_sentiment, extract_key_topics
result = analyze_sentiment("This lecture was confusing and moved too fast")
# Returns: {polarity: -0.4, label: 'negative', confidence: 0.8, ...}
```

## Integration Points & External Dependencies

### External APIs/Services
- **MongoDB**: Primary data store (critical path)
- **TextBlob/NLTK**: Requires initial NLTK data download (handles via `nltk.download()`)
- **Chart.js/Plotly**: Frontend visualization (CDN-loaded)
- **CORS**: Enabled via Flask-CORS for cross-origin frontend requests

### Common Issues & Solutions
1. **NLTK data missing**: Code auto-downloads on first run; may be slow first time
2. **MongoClient timeout**: Ensure MongoDB URI is reachable; check MONGO_URI env var
3. **API CORS errors**: Verify `CORS(app)` in Flask setup
4. **Sentiment inconsistency**: TextBlob polarity varies by text length; always use VADER compound score as tie-breaker

## Database Indexes for Performance
Recommended MongoDB indexes (not yet implemented):
```javascript
db.feedbacks.createIndex({ course_id: 1, timestamp: -1 })
db.feedbacks.createIndex({ student_id: 1 })
db.analytics.createIndex({ course_id: 1 })
```

## Deployment Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Configure `MONGO_URI` to production database
- [ ] Replace `flask.run()` with `gunicorn app:app` (See `requirements.txt` includes gunicorn)
- [ ] Implement JWT authentication for role-based access
- [ ] Add sentiment analysis to async task queue (Celery recommended)
- [ ] Enable dashboard caching (Redis or in-memory)

## Known Limitations & TODOs
- **Sentiment analysis is synchronous**: High-volume feedback will block API. **TODO**: Move to Celery background tasks
- **No authentication yet**: All endpoints are open. **TODO**: Add JWT middleware
- **Frontend is basic**: No filters, sorting on analytics. **TODO**: Add interactive dashboard features
- **Analytics cached only on request**: No pre-computed trends. **TODO**: Implement periodic aggregation job

## File Reference Guide
| File | Purpose |
|------|---------|
| `backend/app.py` | Flask server, routes, MongoDB operations |
| `ml/sentiment_analyzer.py` | Core NLP logic; use functions not refactored calls |
| `frontend/app.js` | API calls & UI logic; localStorage for state |
| `frontend/index.html` | HTML structure; tabs for navigation |
| `backend/requirements.txt` | Python dependencies for backend |
| `ml/requirements.txt` | Separate ML dependencies (can be isolated) |
