# BusinessIntelligence.AI---BID

**BID - Business Investigation Department**

A comprehensive Business Intelligence platform designed to analyze business data, detect KPI anomalies, perform root cause analysis, and generate AI-driven insights with automated PDF reports.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Model Training](#model-training)
- [Modules](#modules)
- [Report Generation](#report-generation)
- [Contributing](#contributing)
- [Support](#support)

---

## 🎯 Overview

BID is an intelligent business analytics platform that:
- Ingests raw business data (orders, marketing metrics, KPIs)
- Detects anomalies in key performance indicators using statistical methods
- Performs root cause analysis on identified anomalies
- Generates AI-driven business narratives (persona-based insights)
- Retrieves supporting evidence from customer reviews/tickets
- Creates professional PDF reports with actionable recommendations
- Learns from analyst feedback to improve recommendations over time (with 3000+ feedbacks)

---

## ✨ Features

- **Data Management**: PostgreSQL database for storing raw data, marketing metrics, and KPIs
- **Multi-Method Anomaly Detection**: Z-score analysis + Prophet forecasting for stronger detection
- **Root Cause Analysis**: Driver-based analysis to identify factors contributing to anomalies
- **AI-Powered Narratives**: Persona-based business insights (Marketing Manager, Sales Ops perspectives)
- **Evidence Retrieval (RAG)**: Supporting evidence from customer reviews and feedback
- **PDF Report Generation**: Professional reports with graphs, tables, and recommendations
- **Confidence Scoring**: Reliability metrics for analysis results
- **Feedback Loop**: Learn from analyst decisions to improve recommendations over time
- **Interactive API Docs**: Auto-generated Swagger UI for testing endpoints
- **Chat Interface**: Conversational AI for Q&A about anomalies
- **ML-Based Action Ranking (v5)**: Advanced recommendation engine trained on 3000+ analyst feedbacks

---

## 🛠 Tech Stack

- **Backend**: Python 3.8+ with FastAPI
- **Database**: PostgreSQL 12+
- **Frontend**: React 19+ with Vite (ES6+)
- **Report Generation**: ReportLab, Matplotlib, Pandas
- **Anomaly Detection**: SciPy (Z-score), Prophet (time-series forecasting)
- **ML Training**: scikit-learn, joblib (for v5 model)
- **LLM Integration**: Google Gemini for narratives and recommendations
- **Environment Management**: python-dotenv
- **API Server**: Uvicorn (ASGI)
- **Data Processing**: Pandas, NumPy

**Language Composition**:
- Python: 69.2%
- JavaScript: 23.4%
- CSS: 7.3%
- HTML: 0.1%

---

## 📁 Project Structure

```
BusinessIntelligence.AI---BID/
├── main.py                          # FastAPI application (entry point)
├── Create_inputDataBase.py          # Database initialization (core KPI tables)
├── database.py                      # Database utilities (feedback table for v5 model)
├── report_pdf.py                    # PDF report generation module
├── anomaly_detector.py              # Anomaly detection (Z-score)
├── prophet_detector.py              # Anomaly detection (Prophet time-series)
├── root_cause.py                    # Root cause analysis engine
├── action_engine.py                 # Business action recommendations
├── recommendation_engine_v5.py      # ML-based action ranking (requires 3000+ feedbacks)
├── llm_narrative.py                 # AI narrative generation
├── text_retrieval.py                # RAG / evidence retrieval
├── chatbot.py                       # Conversational AI
├── business_config.py               # Configuration for KPIs
├── seedfeedback.py                  # Seed sample feedback data for v5 testing
├── samplefrontend/                  # React + Vite frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── .env                             # Environment variables (NOT in version control)
└── requirements.txt                 # Python dependencies
```

---

## 🚀 Installation

### Prerequisites

- **Python** 3.8 or higher
- **PostgreSQL** 12 or higher (running locally or remotely)
- **Node.js** 16+ (for frontend)
- **pip** or conda (Python package manager)
- **Git**

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Giridhar692005/BusinessIntelligence.AI---BID.git
   cd BusinessIntelligence.AI---BID
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Core Python Libraries:**
   - `fastapi==0.141.1` - Web framework
   - `uvicorn==0.52.4` - ASGI server
   - `pandas==2.2.3` - Data processing
   - `numpy==2.1.2` - Numerical computing
   - `scikit-learn==1.6.0` - Machine learning
   - `scipy==1.14.1` - Statistical analysis
   - `prophet==1.4.0` - Time-series forecasting
   - `psycopg2-binary==2.9.12` - PostgreSQL adapter
   - `python-dotenv==1.0.1` - Environment variables
   - `python-multipart==0.0.32` - File upload handling
   - `pydantic==2.13.4` - Data validation
   - `matplotlib==3.9.3` - Visualization
   - `pillow==11.0.0` - Image processing
   - `reportlab==5.0.1` - PDF generation
   - `google-genai==2.20.0` - Google Gemini API
   - `requests==2.32.3` - HTTP client
   - `SQLAlchemy==2.0.52` - Database ORM
   - `joblib==1.4.2` - Model serialization (for v5)
   - `tenacity==9.1.4` - Retry handling

4. **Configure environment variables**
   ```bash
   # Create .env file in root directory
   # Edit with your configuration (see Configuration section below)
   ```

### Frontend Setup (Optional - for full UI)

1. **Navigate to frontend directory**
   ```bash
   cd samplefrontend
   ```

2. **Install Node dependencies**
   ```bash
   npm install
   ```
   
   **Core JavaScript/React Libraries:**
   - `react@^19.0.0` - UI framework
   - `react-dom@^19.0.0` - React DOM bindings
   - `vite@^7.0.0` - Build tool
   - `@vitejs/plugin-react@^5.0.0` - Vite React plugin
   - `recharts@^3.10.1` - Charting library
   - `react-mosaic-component@^7.0.0` - Mosaic layout component

3. **Start development server**
   ```bash
   npm run dev
   ```
   Frontend will be available at `http://127.0.0.1:5173`

---

## 🗄 Database Setup

### Prerequisites

- PostgreSQL running locally or remotely
- Database credentials ready

### Configuration

1. **Create `.env` file** in root directory:
   ```bash
   # Create a .env file with your configuration
   ```

2. **Configure database and API parameters** in `.env`:
   ```env
   # ============ DATABASE CONFIGURATION ============
   DB_HOST=localhost
   DB_NAME=business_Ai
   DB_USER=postgres
   DB_PASSWORD=your_secure_password
   DB_PORT=5432
   
   # ============ LLM CONFIGURATION ============
   # Google Gemini API for AI narratives
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # ============ API CONFIGURATION ============
   # IMPORTANT: Use GROQ_API_KEY (not API_KEY)
   GROQ_API_KEY=your_groq_api_key_for_external_callers
   
   DEBUG=False
   LOG_LEVEL=INFO
   ```

3. **Initialize core database tables** (for basic KPI analysis):
   ```bash
   python Create_inputDataBase.py --init
   ```

   Creates tables:
   - `RawData`: Order and transaction data
   - `MarketingData`: Ad spend and website visit metrics
   - `Kpis`: Key performance indicators (conversion rate, revenue, AOV)

4. **Initialize feedback database** (for recommendation_engine_v5.py ML training):
   ```bash
   python database.py --init
   ```

   Creates table:
   - `business_decisions`: Analyst feedback for ML model training (required for v5)

5. **Verify database connection** (optional):
   ```bash
   python Create_inputDataBase.py
   python database.py
   ```

### Database Schema

#### RawData Table
```sql
CREATE TABLE RawData (
  order_id         VARCHAR(20) PRIMARY KEY,
  customer_id      VARCHAR(20) NOT NULL,
  product_id       VARCHAR(30) NOT NULL,
  unit_price       NUMERIC(10, 2) NOT NULL,
  quantity         INTEGER NOT NULL,
  order_date       DATE NOT NULL,
  production_cost  NUMERIC(10, 2)
);
```

#### MarketingData Table
```sql
CREATE TABLE MarketingData (
  date             DATE PRIMARY KEY,
  ad_spend         NUMERIC(10, 2),
  website_visits   INTEGER
);
```

#### Kpis Table
```sql
CREATE TABLE Kpis (
  date             DATE PRIMARY KEY,
  conversion_rate  NUMERIC(6, 4),
  revenue          NUMERIC(12, 2),
  aov              NUMERIC(10, 2)
);
```

#### Business Decisions Table (for v5 ML model training)
```sql
CREATE TABLE business_decisions (
  id                          SERIAL PRIMARY KEY,
  kpi                         VARCHAR(50),
  anomaly_date                DATE,
  root_cause                  VARCHAR(200),
  action_id                   VARCHAR(50),
  recommended_action          TEXT,
  analyst_rating              INTEGER,
  action_taken                BOOLEAN,
  outcome                     VARCHAR(100),
  outcome_value               NUMERIC,
  primary_driver_pct_change   NUMERIC,
  confidence_score            NUMERIC,
  visitors_change             NUMERIC,
  orders_change               NUMERIC,
  revenue_change              NUMERIC,
  aov_change                  NUMERIC,
  cac_change                  NUMERIC,
  ad_spend_change             NUMERIC,
  created_at                  TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 Running the Application

### Start the FastAPI Backend Server

```bash
uvicorn main:app --reload --port 8000
```

**Parameters:**
- `main:app` — loads the FastAPI app from `main.py`
- `--reload` — auto-restarts server on code changes (development only)
- `--port 8000` — runs on `http://127.0.0.1:8000`

### Access the API Documentation

Once running, open your browser and navigate to:

```
http://127.0.0.1:8000/docs
```

This displays the **Interactive Swagger UI** where you can:
- View all available endpoints
- Test endpoints with sample data
- See request/response schemas
- Download API specifications

Alternative API docs (ReDoc format):
```
http://127.0.0.1:8000/redoc
```

### Health Check

```bash
curl http://127.0.0.1:8000/
# Response: {"status": "ok", "message": "KPI Anomaly Detection API is running"}
```

---

## 📡 API Endpoints

### 1. Data Upload Endpoints

#### Upload Order Data
```http
POST /upload-orders
Content-Type: multipart/form-data

Parameters:
  file: CSV file with columns [order_id, customer_id, product_id, unit_price, quantity, order_date, production_cost]

Response:
{
  "status": "ok",
  "rows_upserted": 150
}
```

#### Upload Marketing Data
```http
POST /upload-marketing
Content-Type: multipart/form-data

Parameters:
  file: CSV file with columns [date, ad_spend, website_visits]

Response:
{
  "status": "ok",
  "rows_upserted": 90
}
```

#### Upload Customer Reviews
```http
POST /upload-reviews
Content-Type: multipart/form-data

Parameters:
  file: CSV file with columns [date, text]

Response:
{
  "status": "ok",
  "rows_loaded": 200
}
```

---

### 2. KPI Management Endpoints

#### Calculate KPIs
```http
POST /calculate-kpis

Response:
{
  "status": "ok",
  "days_calculated": 90
}
```
Computes conversion_rate, revenue, and AOV from RawData + MarketingData.

#### Get Calculated KPIs
```http
GET /kpis

Response:
[
  {
    "date": "2024-01-15",
    "revenue": 15000.50,
    "conversion_rate": 0.0250,
    "aov": 125.75
  },
  ...
]
```

---

### 3. Anomaly Detection Endpoints

#### Basic Anomaly Detection (Z-Score)
```http
POST /detect?kpi=revenue&window=14&threshold=2.5
Content-Type: multipart/form-data

Parameters:
  file: CSV with KPI time series
  kpi: Column name to analyze (e.g., "revenue")
  window: Rolling window size in days (default: 14)
  threshold: Z-score cutoff (default: 2.5)

Response:
{
  "kpi": "revenue",
  "window": 14,
  "threshold": 2.5,
  "total_days": 90,
  "anomaly_count": 3,
  "data": [
    {
      "date": "2024-01-15",
      "value": 25000.00,
      "is_anomaly": true,
      "zscore": 3.2
    },
    ...
  ]
}
```

#### Strong Anomaly Detection (Z-Score + Prophet)
```http
POST /detect-strong?kpi=revenue&window=14&threshold=2.5&interval_width=0.90
Content-Type: multipart/form-data

Parameters:
  file: CSV with KPI time series
  kpi: Column name to analyze
  window: Rolling window size (default: 14)
  threshold: Z-score cutoff (default: 2.5)
  interval_width: Prophet confidence interval width (default: 0.90)

Response:
{
  "kpi": "revenue",
  "prophet_available": true,
  "window": 14,
  "threshold": 2.5,
  "interval_width": 0.90,
  "total_days": 90,
  "anomaly_count": 4,
  "zscore_only_count": 2,
  "prophet_only_count": 1,
  "both_count": 1,
  "data": [
    {
      "date": "2024-01-15",
      "value": 25000.00,
      "is_anomaly": true,
      "detected_by": ["zscore", "prophet"]
    },
    ...
  ]
}
```

#### Detect All KPIs
```http
POST /detect-all?window=14&threshold=2.5
Content-Type: multipart/form-data

Parameters:
  file: CSV with all KPI columns
  window: Rolling window size (default: 14)
  threshold: Z-score cutoff (default: 2.5)

Response:
{
  "revenue": {
    "anomaly_count": 3,
    "data": [...]
  },
  "conversion_rate": {
    "anomaly_count": 2,
    "data": [...]
  },
  "aov": {
    "anomaly_count": 1,
    "data": [...]
  }
}
```

---

### 4. Visualization Endpoints

#### Plot KPI with Anomalies (PNG Image)
```http
POST /plot?kpi=revenue&window=14&threshold=2.5
Content-Type: multipart/form-data

Response: PNG image (direct binary)
```
Returns an image showing:
- KPI trend line
- Anomalies marked as black X's
- Historical baseline

#### Plot KPI as Base64 JSON
```http
POST /plot-base64?kpi=revenue&window=14&threshold=2.5
Content-Type: multipart/form-data

Response:
{
  "kpi": "revenue",
  "anomaly_count": 3,
  "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANS..."
}
```
Easier for React frontends to display.

---

### 5. Root Cause Analysis Endpoints

#### Analyze Root Causes
```http
POST /root-cause?date=2024-01-15&window=14&threshold=2.5
Content-Type: multipart/form-data

Parameters:
  file: CSV with KPI data
  date: Anomaly date to analyze (YYYY-MM-DD)
  window: Rolling window for analysis (default: 14)
  threshold: Z-score threshold (default: 2.5)

Response:
{
  "date": "2024-01-15",
  "root_cause": {
    "drivers": {
      "primary_driver": "ad_spend",
      "primary_driver_pct_change": 25.5,
      "target_kpi": "revenue",
      "drivers_ranked": [
        {
          "factor": "ad_spend",
          "current_value": 5000,
          "baseline_value": 4000,
          "pct_change": 25.0,
          "correlation": 0.85
        },
        ...
      ]
    },
    "confidence": {
      "confidence": "High",
      "score": 0.85,
      "should_abstain": false,
      "reason": "Sufficient data points and strong correlation"
    },
    "multi_kpi_overlap": [...]
  },
  "decision_engine": {
    "primary_driver": "ad_spend",
    "recommendations": [
      {
        "action": "Review ad spend efficiency",
        "impact_score": 0.92,
        "reasoning": "Ad spend increased 25% but ROI decreased"
      },
      ...
    ]
  }
}
```

---

### 6. AI Narrative & Insights Endpoints

#### Generate Business Narratives
```http
POST /narrative?date=2024-01-15&window=14&threshold=2.5&persona=marketing_manager&use_reviews=true
Content-Type: multipart/form-data

Parameters:
  file: CSV with KPI data
  date: Anomaly date (YYYY-MM-DD)
  window: Rolling window (default: 14)
  threshold: Z-score threshold (default: 2.5)
  persona: Optional - "marketing_manager" or "sales_ops_manager" (if omitted, returns ALL personas)
  use_reviews: Whether to include customer review evidence via RAG (default: true)

Response:
{
  "report": {...},  # Full root cause analysis
  "evidence": [
    {
      "date": "2024-01-15",
      "text": "Customer complaint about slow website performance",
      "relevance": 0.92
    },
    ...
  ],
  "narratives": {
    "marketing_manager": {
      "narrative": "Revenue anomaly on Jan 15 was driven by a 25% spike in ad spend... Customer feedback indicates website performance issues may have limited conversion impact...",
      "tone": "analytical",
      "business_factors": ["increased_marketing_spend", "website_performance", "customer_experience"]
    },
    "sales_ops_manager": {
      "narrative": "From operations perspective, the revenue spike correlates with increased traffic but order processing was delayed...",
      "tone": "operational",
      "business_factors": ["order_processing_delay", "inventory_levels", "team_capacity"]
    }
  },
  "decision_engine": {
    "primary_driver": "ad_spend",
    "recommendations": [...]
  }
}
```

---

### 7. PDF Report Generation

#### Generate Complete PDF Report
```http
POST /report?kpi=revenue&date=2024-01-15&window=14&threshold=2.5&use_reviews=true
Content-Type: multipart/form-data

Parameters:
  file: CSV with KPI data
  kpi: Primary KPI to report on
  date: Analysis date (YYYY-MM-DD)
  window: Rolling window (default: 14)
  threshold: Z-score threshold (default: 2.5)
  use_reviews: Include customer evidence (default: true)

Response: PDF file (attachment)
```

**PDF Report Includes:**
1. **Title Page** — Report metadata and date
2. **Executive Summary** — Key findings and confidence level
3. **Root Cause Analysis** — Driver table with current values, baselines, and % changes
4. **Confidence Metrics** — Reliability score and analysis rationale
5. **Affected KPIs** — Multi-KPI overlap analysis
6. **KPI Trend Graph** — Visual representation with anomalies marked
7. **AI Narratives** — Persona-based interpretations (Marketing Manager, Sales Ops)
8. **Supporting Evidence** — Relevant customer reviews and tickets
9. **Recommended Actions** — Ranked business recommendations with impact scores

---

### 8. Business Actions & Recommendations

#### Get Candidate Actions for a KPI
```http
GET /actions?kpi=revenue

Response:
{
  "kpi": "revenue",
  "actions": [
    {
      "id": "action_1",
      "title": "Optimize ad spend allocation",
      "description": "Reallocate budget to highest-ROI channels",
      "impact": "High",
      "effort": "Medium"
    },
    ...
  ]
}
```

#### Get Historical Action Scores (v5 Model Only - Requires 3000+ Feedbacks)
```http
GET /actions/scores?kpi=revenue

Response:
{
  "action_1": {
    "title": "Optimize ad spend allocation",
    "historical_score": 0.87,
    "times_taken": 5,
    "average_outcome": "positive"
  },
  ...
}
```
⚠️ Only available after training v5 model with 3000+ analyst feedbacks.

---

### 9. Feedback & Learning Loop

#### Submit Analyst Feedback
```http
POST /feedback
Content-Type: application/json

Body:
{
  "kpi": "revenue",
  "anomaly_date": "2024-01-15",
  "root_cause": "ad_spend",
  "recommended_action": "Optimize ad spend allocation",
  "analyst_rating": 4,
  "action_taken": true,
  "outcome": "positive",
  "outcome_value": 5000.00,
  
  "primary_driver_pct_change": 25.5,
  "confidence_score": 0.85,
  
  "visitors_change": -5.2,
  "orders_change": 12.3,
  "revenue_change": 8.7,
  "aov_change": -3.5,
  "cac_change": 2.1,
  "ad_spend_change": 25.0
}

Response:
{
  "status": "success",
  "message": "Feedback stored successfully",
  "decision_id": 42
}
```

#### Retrieve Stored Feedback
```http
GET /feedback?kpi=revenue&limit=50

Response:
{
  "count": 42,
  "feedback": [
    {
      "id": 42,
      "kpi": "revenue",
      "anomaly_date": "2024-01-15",
      "recommended_action": "Optimize ad spend allocation",
      "analyst_rating": 4,
      "action_taken": true,
      "outcome": "positive",
      "outcome_value": 5000.00,
      "confidence_score": 0.85,
      "created_at": "2024-01-16T10:30:00"
    },
    ...
  ]
}
```

---

### 10. Chat Interface

#### Chat with AI about Anomalies
```http
POST /chat
Content-Type: multipart/form-data

Parameters:
  req: JSON string with chat request
  file: CSV with KPI data
  pdf: (Optional) PDF report file

Body (req parameter as JSON):
{
  "message": "Why did revenue spike on January 15?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

Response:
{
  "response": "Based on the data analysis, the revenue spike on January 15 was primarily driven by...",
  "sources": ["ad_spend_increase", "customer_reviews"]
}
```

---

## 📖 Usage Guide

### Workflow for Basic Analysis (No ML Training Required)

#### Step 1: Load Data
```bash
# Upload raw order data
curl -X POST "http://localhost:8000/upload-orders" \
  -F "file=@orders.csv"

# Upload marketing metrics
curl -X POST "http://localhost:8000/upload-marketing" \
  -F "file=@marketing.csv"

# Upload customer reviews (for evidence)
curl -X POST "http://localhost:8000/upload-reviews" \
  -F "file=@reviews.csv"
```

#### Step 2: Calculate KPIs
```bash
curl -X POST "http://localhost:8000/calculate-kpis"
```

#### Step 3: Detect Anomalies
```bash
# Strong detection (Z-Score + Prophet)
curl -X POST "http://localhost:8000/detect-strong?kpi=revenue" \
  -F "file=@kpi_data.csv"
```

#### Step 4: Analyze Root Causes
```bash
curl -X POST "http://localhost:8000/root-cause?date=2024-01-15" \
  -F "file=@kpi_data.csv"
```

#### Step 5: Generate Report with Narratives
```bash
curl -X POST "http://localhost:8000/narrative?date=2024-01-15&persona=marketing_manager" \
  -F "file=@kpi_data.csv"
```

#### Step 6: Generate PDF Report
```bash
curl -X POST "http://localhost:8000/report?kpi=revenue&date=2024-01-15" \
  -F "file=@kpi_data.csv" \
  -o revenue_report_2024-01-15.pdf
```

#### Step 7: Submit Feedback (for Learning)
```bash
curl -X POST "http://localhost:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "kpi": "revenue",
    "anomaly_date": "2024-01-15",
    "recommended_action": "Optimize ad spend allocation",
    "analyst_rating": 4,
    "action_taken": true,
    "outcome": "positive"
  }'
```

---

## 🤖 Advanced: Model Training with recommendation_engine_v5.py

### ⚠️ IMPORTANT: Data Requirements
**Only use recommendation_engine_v5.py if you have 3000+ analyst feedbacks** in the `business_decisions` table. With smaller datasets, the ML model will not train properly.

### Step 1: Seed Sample Feedback Data (For Testing Only)

If you want to test the v5 model with sample data before collecting real feedbacks:

```bash
python seedfeedback.py
```

This script will:
- Create 3000+ sample feedback records in `business_decisions` table
- Cover various KPI anomalies, root causes, and outcomes
- Generate realistic action effectiveness patterns
- Provide training data for the ML model to learn from

**Note**: In production, feedback comes from the `/feedback` API endpoint as users analyze anomalies.

### Step 2: Ensure Feedback Table is Initialized

```bash
python database.py --init
```

This creates the `business_decisions` table needed for ML training.

### Step 3: Accumulate Feedbacks

After using the platform for analysis, users submit feedback via the `/feedback` endpoint. The system learns patterns from these feedbacks.

### Step 4: Train the v5 Model

Once you have 3000+ feedbacks:

```bash
# The v5 model automatically trains when called with sufficient data
GET /actions/scores?kpi=revenue
```

The model will:
- Analyze patterns from 3000+ historical feedbacks
- Learn which actions have been most effective
- Identify success patterns by KPI, root cause, and context
- Rank recommendations based on learned patterns

### Step 5: Use Trained Recommendations

After training, recommendations are ranked by effectiveness:

```http
GET /actions/scores?kpi=revenue

Response:
{
  "action_1": {
    "title": "Optimize ad spend allocation",
    "historical_score": 0.87,    # Effectiveness score
    "times_taken": 25,           # Number of times used
    "average_outcome": "positive" # Average outcome
  },
  "action_2": {
    "title": "Improve website performance",
    "historical_score": 0.92,
    "times_taken": 18,
    "average_outcome": "positive"
  }
}
```

---

## ⚙ Configuration

### Environment Variables

Create a `.env` file in the root directory with:

```env
# ============ DATABASE CONFIGURATION ============
DB_HOST=localhost
DB_NAME=business_Ai
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_PORT=5432

# ============ LLM CONFIGURATION ============
# Google Gemini API for AI narratives and insights
GEMINI_API_KEY=your_gemini_api_key_here

# ============ API CONFIGURATION ============
# IMPORTANT: Use GROQ_API_KEY (this is the primary API key for external callers)
GROQ_API_KEY=your_groq_api_key_for_external_callers

# ============ LOGGING & DEBUG ============
DEBUG=False
LOG_LEVEL=INFO
```

### Report Customization

Modify styling in `report_pdf.py`:

```python
# Title style
TITLE_FONT_SIZE = 24
TITLE_COLOR = (0, 0, 0)  # RGB

# Table styling
TABLE_HEADER_COLOR = (0.2, 0.4, 0.8)  # Dark blue
TABLE_ROW_COLOR = (0.95, 0.95, 0.95)  # Light gray

# Body text
BODY_FONT_SIZE = 11
LINE_SPACING = 1.5
```

---

## 📦 Modules

### `main.py` — FastAPI Application (Entry Point)

**Purpose**: Core API server exposing all endpoints

**What it does**:
- Starts Uvicorn ASGI server on port 8000
- Auto-generates Swagger UI at `/docs`
- Exposes 30+ endpoints for data upload, anomaly detection, analysis, and reporting
- Manages CORS for frontend communication

**How to Run**:
```bash
uvicorn main:app --reload --port 8000
```

---

### `Create_inputDataBase.py` — Database Management (Core Tables)

**Purpose**: Database initialization and connection management for core KPI tables

**Key Functions**:
- `get_connection()`: Establishes PostgreSQL connection
- `create_tables()`: Initializes schema with RawData, MarketingData, Kpis tables
- `main()`: CLI interface for database operations

**Usage**:
```bash
# Test connection
python Create_inputDataBase.py

# Initialize database
python Create_inputDataBase.py --init
```

---

### `database.py` — Database Utilities & Feedback Management

**Purpose**: Database utilities and feedback table management for v5 ML model training

**Features**:
- Connection pooling
- Error logging
- Transaction management
- Feedback table initialization

**Usage**:
```bash
# Initialize feedback table for v5 model training
python database.py --init
```

---

### `seedfeedback.py` — Feedback Data Seeding

**Purpose**: Populate sample feedback data for testing the v5 model

**What it does**:
- Creates 3000+ sample feedback records in `business_decisions` table
- Covers various KPI anomalies and root causes
- Generates realistic action outcomes and effectiveness scores
- Provides training data for the ML recommendation engine

**Usage**:
```bash
python seedfeedback.py
```

**When to Use**:
- For testing v5 model in development
- To understand feedback data structure
- NOT needed for production (feedback comes via `/feedback` API)

---

### `anomaly_detector.py` — Statistical Anomaly Detection

**Purpose**: Detect anomalies using Z-score method

**Algorithm**:
1. Calculates 14-day rolling mean and standard deviation
2. Computes Z-score for each day: `(value - mean) / std`
3. Flags days with |Z-score| > threshold (default: 2.5) as anomalies

**Key Functions**:
- `detect_anomalies_zscore()`: Single KPI anomaly detection
- `detect_anomalies_multi()`: Multiple KPI anomaly detection

---

### `prophet_detector.py` — Time-Series Forecasting

**Purpose**: Detect anomalies using Facebook's Prophet

**Algorithm**:
1. Trains Prophet model on historical data
2. Generates forecasts with confidence intervals
3. Flags days outside confidence interval as anomalies
4. Combines results with Z-score detection (OR logic)

**Key Functions**:
- `detect_anomalies_ensemble()`: Combines Z-score + Prophet for stronger detection

---

### `root_cause.py` — Root Cause Analysis

**Purpose**: Identify which KPI or factor caused the anomaly

**Analysis Steps**:
1. Identify Primary Driver: Which KPI changed most on anomaly date
2. Factor Correlation: Analyze correlation between drivers
3. Baseline Comparison: Compare to 14-day baseline
4. Calculate % Changes: Quantify impact
5. Confidence Scoring: Assess reliability

---

### `action_engine.py` — Business Action Generation

**Purpose**: Generate candidate actions based on root cause

**Action Categories**:
- Pricing Actions: Adjust pricing, run promotions
- Marketing Actions: Optimize ad spend, change targeting
- Operational Actions: Scale resources, process improvements
- Product Actions: Feature updates, quality improvements

---

### `recommendation_engine_v5.py` — ML-Based Action Ranking

**⚠️ REQUIRES: 3000+ analyst feedbacks for proper training**

**Purpose**: Rank business actions using ML model trained on historical feedback

**What it does**:
1. Loads feedback from `business_decisions` table
2. Extracts features from anomalies, root causes, and outcomes
3. Trains scikit-learn model on action effectiveness
4. Ranks recommendations based on learned patterns

**Usage**:
```bash
# The model trains automatically when called with sufficient data (3000+)
GET /actions/scores?kpi=revenue
```

---

### `llm_narrative.py` — AI Narrative Generation

**Purpose**: Generate human-readable business insights using LLM

**Personas**:
1. **Marketing Manager**: Focus on marketing metrics, campaign effectiveness, ROI
2. **Sales Ops Manager**: Focus on operational efficiency, pipeline, conversion

**Features**:
- Uses Google Gemini API for generation
- Incorporates customer evidence and context
- Structured output with business factors

---

### `text_retrieval.py` — RAG / Evidence Retrieval

**Purpose**: Find supporting evidence from customer reviews/feedback

**Algorithm**:
1. Parses root cause analysis
2. Searches for related keywords in reviews
3. Ranks by relevance to anomaly date and factors
4. Returns top K matching reviews

---

### `report_pdf.py` — PDF Report Generation

**Purpose**: Create professional PDF reports with all analysis results

**Report Sections**:
1. Title Page
2. Executive Summary
3. Root Cause Analysis Table
4. Confidence Metrics
5. Affected KPIs
6. KPI Trend Graph
7. AI Narratives (Multiple Personas)
8. Supporting Evidence
9. Recommended Actions

**Libraries Used**:
- ReportLab: PDF generation
- Matplotlib: Visualization
- Pandas: Data manipulation
- Pillow: Image processing

---

### `chatbot.py` — Conversational AI

**Purpose**: Enable Q&A about anomalies via chat interface

**Features**:
- Conversation history management
- Context from KPI data and reports
- PDF document understanding
- Multi-turn conversations

---

### `business_config.py` — Configuration Management

**Purpose**: Centralized business configuration

**Contents**:
- KPI definitions
- Default analysis parameters
- Persona configurations

---

## 📄 Report Generation

### Report Sections In Detail

#### 1. Executive Summary
- What anomaly was detected
- Primary driver of the anomaly
- Confidence in the analysis
- Top recommendation

#### 2. Root Cause Analysis Table
| Driver | Current | Baseline | % Change | Correlation |
|--------|---------|----------|----------|-------------|
| ad_spend | $5,000 | $4,000 | +25% | 0.85 |
| website_visits | 45,000 | 50,000 | -10% | 0.72 |

#### 3. Confidence Metrics
- Confidence Level: High / Medium / Low
- Confidence Score: 0-1 numerical score
- Data Quality assessment

#### 4. KPI Trend Graph
- KPI line chart over time
- Baseline/trend line
- Anomalies marked with X

#### 5. AI Narratives (per Persona)
Human-readable explanations from:
- Marketing Manager: Focus on marketing metrics and ROI
- Sales Ops Manager: Focus on operational efficiency

#### 6. Supporting Evidence
Customer review snippets:
- Date, verbatim feedback, relevance score, sentiment

#### 7. Recommendations
Ranked action list with:
- Action description
- Rationale
- Impact Score (0-1)
- Effort (Low/Medium/High)
- Timeline

---

## 📝 Contributing

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/BusinessIntelligence.AI---BID.git
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Follow PEP 8 style guidelines for Python
   - Add docstrings to new functions
   - Test thoroughly

4. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature: description'
   ```

5. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Include examples if applicable

---

## 📄 License

This project is open source. See LICENSE file for details.

---

## 🤝 Support

For issues, questions, or suggestions:

1. **Check existing GitHub issues** for solutions
2. **Open a new GitHub issue** with:
   - Clear title describing the problem
   - Steps to reproduce
   - Expected vs. actual behavior
   - Error messages/logs
3. **Contact the maintainers** via email

---

## 🎯 Roadmap

**Future Enhancements**:
- [ ] Multi-language support for narratives
- [ ] Custom anomaly detection algorithms
- [ ] Real-time dashboard with WebSocket updates
- [ ] Integration with Slack/Teams for alerts
- [ ] Advanced time-series decomposition
- [ ] Automated report scheduling
- [ ] User role management and permissions
- [ ] Enhanced ML model with deep learning

---

**Last Updated**: August 2026  
**Author**: Giridhar692005  
**Repository**: [GitHub](https://github.com/Giridhar692005/BusinessIntelligence.AI---BID)
