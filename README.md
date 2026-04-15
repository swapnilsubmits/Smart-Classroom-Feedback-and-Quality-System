# Smart Classroom Feedback & Quality Monitoring System

A comprehensive web-based platform for real-time student feedback collection and AI-powered sentiment analysis.

## Features
- **Structured & Unstructured Feedback**: Students submit detailed or quick feedback
- **AI-Powered Sentiment Analysis**: Automatic analysis using NLTK/TextBlob
- **Analytics Dashboard**: Real-time trends and sentiment visualization
- **Role-Based Access**: Student, Faculty, and Admin roles with specific permissions
- **Deployable Solution**: Production-ready for institutional use

## Technology Stack
- **Backend**: Flask with MongoDB
- **Frontend**: HTML/CSS/JavaScript with Chart.js/Plotly
- **NLP**: NLTK, TextBlob, HuggingFace Transformers
- **Database**: MongoDB for flexible feedback schema

## Project Structure
```
├── backend/          # Flask API server
├── frontend/         # Web UI
├── ml/               # Sentiment analysis models
└── .github/          # GitHub workflows & instructions
```

## Getting Started 📦

### 1. Prerequisites
- Python 3.10+ (3.14 recommended)
- `pip` installed (comes with Python)
- MongoDB running locally on `localhost:27017` **or** a Docker container (optional)

> **No MongoDB?** The backend will automatically fall back to an in-memory store so you can run the app without a database for quick demos.

### 2. Backend Setup
```powershell
cd backend
python -m venv venv            # create a virtual environment
venv\Scripts\activate          # Windows
pip install -r requirements.txt  # install dependencies
```

### 3. Start MongoDB (optional but recommended)
```powershell
# local install
mongod --dbpath C:\data\db

# or using Docker
docker run -d -p 27017:27017 --name mongo mongo:6
```
If Mongo isn’t running, the server will still start and store feedback in memory.

### 4. Run the Flask Server (EASIEST WAY)
**Just double-click `START_PROJECT.bat`** - It will:
- ✅ Activate your virtual environment automatically
- ✅ Start the Flask server on `http://localhost:5000`
- ✅ Show you clear status messages

**Keep this window open while using the app!**

### Alternative: Manual Setup
```powershell
cd backend
venv\Scripts\activate         # if not already active
python app.py                   # launches API on http://localhost:5000
```

### 5. Frontend
Open `frontend/index.html` in your browser. The app will automatically connect to the backend.

**⚠️ IMPORTANT**: Your submit button will stay disabled until the backend is running. Once you see "✅ Backend connected!" message, the button will be active.

### 6. Optional: ML module test
```powershell
cd ml
pip install -r requirements.txt
python -c "from sentiment_analyzer import analyze_sentiment; print(analyze_sentiment('Great class!'))"
```

### 7. Usage
- Navigate to **Submit Feedback** tab and send a response.
- Switch to **Dashboard** to view analytics updates.

### Troubleshooting ⚙️

**❌ Submit button is disabled/greyed out?**
- The backend server is not running!
- **Solution**: Run `START_PROJECT.bat` and keep that window open
- The button will automatically enable when the backend connects

**❌ Submit button stops working after closing & reopening VS Code?**
- The backend was stopped when you closed VS Code
- **Solution**: Run `START_PROJECT.bat` again to restart the server

**❌ Connection errors or "Cannot reach backend"?**
- Check that `START_PROJECT.bat` window is still open
- Verify it shows "Flask running on http://localhost:5000"
- Try refreshing the webpage (F5) after the server is running

**❌ Missing NLTK data**: 
- The ML module auto-downloads required corpora on first run (may be slow)

**❌ Port 5000 already in use?**
- Another app is using that port
- Close any other Flask servers or services using port 5000

Enjoy exploring and extending the system! 🎓

