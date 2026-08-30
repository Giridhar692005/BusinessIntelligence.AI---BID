# BusinessIntelligence.AI---BID

**BID - Business Investigation Department**

A comprehensive Business Intelligence platform designed to analyze business data, detect KPI anomalies, and generate AI-driven insights with automated PDF reports.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Modules](#modules)
- [Report Generation](#report-generation)

## 🎯 Overview

BID is an intelligent business analytics platform that:
- Ingests raw business data (orders, marketing metrics, KPIs)
- Detects anomalies in key performance indicators
- Performs root cause analysis on identified anomalies
- Generates AI-driven business narratives
- Creates professional PDF reports with actionable recommendations

## ✨ Features

- **Data Management**: PostgreSQL database for storing raw data, marketing metrics, and KPIs
- **Anomaly Detection**: Statistical analysis to identify KPI anomalies
- **Root Cause Analysis**: Driver-based analysis to identify factors contributing to anomalies
- **AI-Powered Narratives**: Persona-based business insights and explanations
- **Evidence Retrieval**: Supporting evidence for identified anomalies
- **PDF Report Generation**: Professional reports with graphs, tables, and recommendations
- **Confidence Scoring**: Reliability metrics for analysis results

## 🛠 Tech Stack

- **Backend**: Python 3.x
- **Database**: PostgreSQL
- **Frontend**: React + Vite (ES6+)
- **Report Generation**: ReportLab, Matplotlib
- **Environment Management**: python-dotenv
- **Styling**: CSS, HTML

**Language Composition**:
- Python: 69.2%
- JavaScript: 23.4%
- CSS: 7.3%
- HTML: 0.1%

## 📁 Project Structure

```
BusinessIntelligence.AI---BID/
├── Create_inputDataBase.py      # Database initialization script
├── report_pdf.py                # PDF report generation module
├── samplefrontend/              # React + Vite frontend
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## 🚀 Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Node.js 16+ (for frontend)
- pip or conda (Python package manager)

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

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd samplefrontend
   ```

2. **Install Node dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

## 🗄 Database Setup

### Prerequisites

- PostgreSQL running locally or remotely
- Database credentials ready

### Configuration

1. **Create `.env` file** from `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. **Configure database parameters** in `.env`:
   ```env
   DB_HOST=localhost
   DB_NAME=business_Ai
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_PORT=5432
   ```

3. **Initialize database tables**:
   ```bash
   python Create_inputDataBase.py --init
   ```

   This will create three tables:
   - `RawData`: Order and transaction data
   - `MarketingData`: Ad spend and website visit metrics
   - `Kpis`: Key performance indicators (conversion rate, revenue, AOV)

4. **Verify connection** (optional):
   ```bash
   python Create_inputDataBase.py
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
  production_cost  NUMERIC(10, 2) NOT NULL
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

## 📖 Usage

### Database Operations

**Test Database Connection**:
```bash
python Create_inputDataBase.py
```

**Initialize/Reset Database**:
```bash
python Create_inputDataBase.py --init
```

### Report Generation

The `report_pdf.py` module generates comprehensive PDF reports with the following sections:

```python
from report_pdf import create_report_pdf

buffer = create_report_pdf(
    kpi="revenue",
    date="2024-01-15",
    report={
        "drivers": {
            "primary_driver": "ad_spend",
            "primary_driver_pct_change": 25.5,
            "drivers_ranked": [...]
        },
        "confidence": {
            "confidence": "High",
            "score": 0.85,
            "should_abstain": False,
            "reason": "Sufficient data points"
        },
        "multi_kpi_overlap": {...}
    },
    narratives={...},
    evidence={...},
    recommendations=[...],
    graph_buffer=graph_image
)

# Save or transmit buffer
with open("report.pdf", "wb") as f:
    f.write(buffer.getvalue())
```

## ⚙ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DB_HOST=localhost
DB_NAME=business_Ai
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_PORT=5432

# API Configuration (if applicable)
API_KEY=your_api_key
DEBUG=False
```

### Report Customization

Modify styles in `report_pdf.py`:
- **Title Style**: Font size, alignment, color
- **Table Styling**: Colors, borders, row backgrounds
- **Body Text**: Font size, line spacing

## 📦 Modules

### `Create_inputDataBase.py`

**Purpose**: Database initialization and connection management

**Key Functions**:
- `get_connection()`: Establishes PostgreSQL connection
- `create_tables()`: Initializes schema with RawData, MarketingData, and Kpis tables

**Features**:
- Automatic table creation if not exists
- Index creation on order_date for performance
- Safe re-initialization with `--init` flag

### `report_pdf.py`

**Purpose**: Generate professional PDF reports with analysis results

**Key Functions**:
- `create_report_pdf()`: Generates complete PDF report
- `_fmt()`: Formats numerical values for display
- `_draw_header_footer()`: Adds consistent headers/footers

**Report Sections**:
1. Title & Metadata
2. Executive Summary
3. Root Cause Analysis (driver table)
4. Confidence Metrics
5. Affected KPIs
6. KPI Trend Graph
7. AI Business Narratives
8. Supporting Evidence
9. Recommended Actions

## 📄 Report Generation

Reports include:

- **Executive Summary**: Overview of primary drivers and analysis confidence
- **Root Cause Analysis**: Ranked factors with current values, baselines, and % change
- **Confidence Metrics**: Analysis reliability score and recommendations
- **KPI Trends**: Visual graphs showing anomalies and historical trends
- **AI Narratives**: Persona-based interpretations of anomalies
- **Evidence**: Supporting data points and sources
- **Recommendations**: Actionable steps with impact assessment

### Sample Report Structure

```
Business Intelligence Report
├── Executive Summary
├── Root Cause Analysis (Table)
├── Confidence Level
├── Affected KPIs
├── KPI Trend Graph
├── AI Narratives (multiple personas)
├── Supporting Evidence
└── Recommended Actions
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source. See LICENSE file for details.

## 🤝 Support

For issues, questions, or suggestions, please open an GitHub issue in the repository.

---

**Last Updated**: August 2026
**Author**: Giridhar692005
