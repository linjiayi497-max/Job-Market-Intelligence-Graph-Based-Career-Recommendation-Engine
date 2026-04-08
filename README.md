# Job Market Intelligence: Graph-Based Career Recommendation Engine

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg)](https://streamlit.io)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.0+-008CC1.svg)](https://neo4j.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-green.svg)](https://xgboost.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end intelligent career recommendation system built on **1.66 million** real-world job postings. The system combines deep learning NER (MacBERT-BiLSTM-CRF) for skill extraction, a Neo4j knowledge graph with **30M+ nodes and 110M+ relationships**, XGBoost salary prediction with SHAP explainability, and LLM-powered career guidance.

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Zhilian      │  │ Liepin       │  │ MOOC (iCourse163)     │ │
│  │ Job Spider   │  │ Job Spider   │  │ Course Scraper        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         └──────────────────┼─────────────────────┘             │
└────────────────────────────┼───────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NLP & Feature Engineering                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  MacBERT-BiLSTM-CRF NER Model → Skill Entity Extraction   │  │
│  │  (GPU Inference on 1.7M job descriptions)                 │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Data Cleaning → Salary Parsing → Feature Engineering     │  │
│  └───────────────────────────┬───────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics & Models                            │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────┐ │
│  │ Job Data        │ │ Skill Gap        │ │ Salary           │ │
│  │ Analysis        │ │ Analysis         │ │ Prediction       │ │
│  │ (TF-IDF,       │ │ (Weighted        │ │ (XGBoost +       │ │
│  │  Heatmaps)     │ │  Coverage)       │ │  SHAP)           │ │
│  └─────────────────┘ └──────────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Knowledge Graph Engine                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Neo4j Graph Database (30M+ nodes, 110M+ relationships)  │  │
│  │  Nodes: Job, Skill, Course                                │  │
│  │  Relations: REQUIRES (Job→Skill), PROVIDES (Course→Skill) │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│  ┌───────────────────┐ ┌─────┴───────┐ ┌──────────────────────┐│
│  │ Job→Course        │ │ Course→Job  │ │ NL2Cypher (LLM)      ││
│  │ Recommendation    │ │ Matching    │ │ Natural Language      ││
│  │ (GMSCR Algorithm) │ │ (Jaccard)   │ │ Graph Querying       ││
│  └───────────────────┘ └─────────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

### 1. 📊 Job Market Analytics Dashboard
- **Skill Frequency Analysis** — Top skills across industries, cities, and salary bands
- **Industry × Skill Heatmap** — Visual skill demand patterns across industries
- **City Skill Comparison** — Regional skill demand differences
- **TF-IDF Skill Weights** — Identify "signature" skills for each salary band

### 2. 🎯 Skill Gap Analysis
- **Interactive Skill Input** — Manual selection or resume text parsing
- **Weighted Coverage Algorithm** — Quantifies skill-job match using importance weights
- **Radar Chart Visualization** — Intuitive skill coverage comparison
- **AI Learning Path Report** — LLM-generated personalized learning recommendations

### 3. 💸 Salary Prediction Sandbox
- **Real-time Prediction** — Select skills, city, experience → instant salary estimate
- **Skill Marginal Value** — Shows how each additional skill impacts salary
- **SHAP Explainability** — Feature importance ranking and beeswarm plots
- **XGBoost Model** — Trained on 1.4M+ records with R² > 0.85

### 4. 🎓 Knowledge Graph Recommendation
- **Job → Course Recommendation** — Find courses covering target job's core skills
- **Course → Job Matching** — Discover career paths based on completed courses
- **Interactive Graph Visualization** — Explore Job-Skill-Course relationships
- **Natural Language Querying** — Ask questions in plain language (LLM → Cypher)

---

## 📁 Project Structure

```
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── data_collection/                   # Web scraping modules
│   ├── README.md                      # Scraper documentation
│   ├── job_scraping/                  # Job recruitment scrapers
│   │   ├── zhilian_job_spider.py      # Zhilian job listing spider
│   │   ├── zhilian_detail_scraper.py  # Zhilian job detail enrichment
│   │   └── liepin_job_spider.py       # Liepin job listing spider
│   └── course_scraping/               # MOOC course scrapers
│       ├── mooc_selenium_scraper.py   # Browser-based MOOC scraper
│       └── mooc_api_scraper.py        # API-based MOOC scraper
│
├── analytics_dashboard/               # Streamlit analytics system
│   ├── app/                           # Streamlit pages
│   │   ├── main_page.py               # Dashboard home page
│   │   └── pages/
│   │       ├── 1_job_data_analysis.py  # Job data & skill distribution
│   │       ├── 2_skill_gap_analysis.py # Personal skill gap diagnosis
│   │       └── 3_salary_prediction.py  # XGBoost salary prediction
│   ├── processing/                    # Data processing modules
│   │   ├── data_cleaning.py           # Raw data cleaning pipeline
│   │   └── data_loader.py            # Shared data loader & utilities
│   ├── scripts/                       # Training & inference scripts
│   │   ├── batch_inference.py         # MacBERT-BiLSTM-CRF NER inference
│   │   └── train_xgb_model.py        # XGBoost model training
│   └── models/                        # Trained model storage
│
└── knowledge_graph/                   # Knowledge graph system
    └── app.py                         # Neo4j KG recommendation app
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9+
- Neo4j 5.0+ (for knowledge graph features)
- Chrome + ChromeDriver (for web scraping)

### 1. Clone the Repository
```bash
git clone https://github.com/linjiayi497-max/Job-Market-Intelligence-Graph-Based-Career-Recommendation-Engine.git
cd Job-Market-Intelligence-Graph-Based-Career-Recommendation-Engine
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
```bash
# For AI-powered skill gap reports
export GROQ_API_KEY="your-groq-api-key"

# For knowledge graph (Neo4j)
export NEO4J_PASSWORD="your-neo4j-password"
```

### 4. Data Pipeline (if running from scratch)

```bash
# Step 1: Scrape job data
python data_collection/job_scraping/zhilian_job_spider.py

# Step 2: Run NER skill extraction (requires GPU)
python analytics_dashboard/scripts/batch_inference.py

# Step 3: Clean extracted data
python analytics_dashboard/processing/data_cleaning.py

# Step 4: Train salary prediction model
python analytics_dashboard/scripts/train_xgb_model.py
```

### 5. Launch Dashboards

```bash
# Analytics Dashboard
cd analytics_dashboard
streamlit run app/main_page.py

# Knowledge Graph System
cd knowledge_graph
streamlit run app.py
```

---

## 📊 Data Scale

| Metric | Value |
|--------|-------|
| Raw job postings | 1.7 million |
| Valid records (after cleaning) | 1.4 million+ |
| Industries covered | 50+ |
| Cities covered | 300+ |
| Unique skills extracted | 10,000+ |
| Knowledge graph nodes | 30 million+ |
| Knowledge graph relationships | 110 million+ |

---

## 🧪 Model Performance

### XGBoost Salary Prediction
| Metric | Value |
|--------|-------|
| MAE (Mean Absolute Error) | ~¥1,500 |
| RMSE (Root Mean Squared Error) | ~¥2,800 |
| R² (Coefficient of Determination) | > 0.85 |

### MacBERT-BiLSTM-CRF NER
| Metric | Value |
|--------|-------|
| Precision | 99.14% |
| Recall | 99.26% |
| F1 Score | 99.20% |

---

## 🔧 Technology Stack

| Component | Technology |
|-----------|-----------|
| **NER Model** | MacBERT-BiLSTM-CRF (PyTorch + Transformers) |
| **Salary Prediction** | XGBoost + SHAP |
| **Knowledge Graph** | Neo4j Graph Database |
| **Dashboard** | Streamlit + Plotly |
| **Data Collection** | Selenium + lxml + BeautifulSoup |
| **NL2Cypher** | LLM (Groq/OpenAI compatible) |

---
