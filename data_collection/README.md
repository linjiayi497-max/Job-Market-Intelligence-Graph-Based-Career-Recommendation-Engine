# Data Collection Module

This module contains web scrapers used to collect raw data from two sources:

## 1. Job Recruitment Data (`job_scraping/`)

Scrapers for collecting job postings from major Chinese recruitment platforms:

| Script | Platform | Description |
|--------|----------|-------------|
| `zhilian_job_spider.py` | Zhilian (智联招聘) | Scrapes job listings across all provinces with keyword search |
| `zhilian_detail_scraper.py` | Zhilian (智联招聘) | Enriches listings with full job descriptions, skill tags, headcount |
| `liepin_job_spider.py` | Liepin (猎聘网) | Scrapes job listings with district-level granularity |

### Data Fields Collected
- Job title, company name, industry
- Salary range, city/location
- Education & experience requirements
- Full job description text
- Skill tags

## 2. Online Course Data (`course_scraping/`)

Scrapers for collecting MOOC course data from iCourse163 (中国大学MOOC):

| Script | Method | Description |
|--------|--------|-------------|
| `mooc_selenium_scraper.py` | Selenium | Browser-based scraping with pagination |
| `mooc_api_scraper.py` | HTTP API | Faster API-based scraping with content fetching |

### Data Fields Collected
- Course title, university, instructor
- Enrollment count
- Course description/syllabus content

## Prerequisites

```bash
pip install selenium lxml colorama tqdm pandas beautifulsoup4 requests openpyxl
```

- Chrome browser + ChromeDriver (matching version)
- For API scraper: session cookies captured from browser DevTools

## Usage

```bash
# Job scraping
python job_scraping/zhilian_job_spider.py

# Course scraping  
python course_scraping/mooc_selenium_scraper.py
```

> **Note**: These scrapers require manual login to the respective platforms before automated scraping begins. All scrapers support resumable progress tracking.
