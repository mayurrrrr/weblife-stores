# PRD: Cross-Marketplace Laptop Intelligence Engine (Live Data Edition)

## Goal
Build a full-stack application that scrapes **live data** from Lenovo and HP official stores, merges it with canonical PDF specifications, and exposes the data through:

- A **structured API** (FastAPI),
- A **user-friendly web UI** (HTML/JS + Chart.js),
- An **LLM-powered chatbot and recommender** (Google Gemini API).

---

## Guiding Principles
- **Authenticity**: All market data is sourced live from Lenovo/HP product pages.  
- **Robustness**: Handle JavaScript-rendered content (using Playwright).  
- **Modularity**: Keep scraper, database, API, and frontend as separate but connected modules.  

---

## Phase 1: Data Foundation (Ground Truth + Live Data)

### Step 1.1: Identify Target URLs
Manually confirm the official PDP (Product Detail Pages) for:

- Lenovo ThinkPad E14 Gen 5 Intel  
- Lenovo ThinkPad E14 Gen 5 AMD  
- HP ProBook 450 G10  
- HP ProBook 440 G11  

> These are the mutable sources for prices, availability, reviews, and Q&A.

---

### Step 1.2: Live Web Scraper
**Tool**: Python + Playwright  

**Inputs**: URLs from Step 1.1  
**Outputs**:  
- `live_offers.json`: Price, currency, availability, shipping ETA, promotions  
- `live_reviews.json`: Ratings, review text, author, date  
- `live_qna.json`: Question, answer, date  

**Process**:
1. Launch headless Chromium with Playwright.  
2. `page.goto(url, wait_until="domcontentloaded")`.  
3. Wait for price selector (e.g., `.price-final`, `[data-testid='price']`).  
4. Extract:
   - Offer data: Price, currency, availability, shipping ETA, promo badges.  
   - Reviews: Loop through "Load More" until all reviews are fetched. Extract rating, review text, author, date.  
   - Q&A: Extract visible questions and answers.  
5. Save to JSON.  

**Cursor Prompt Example**:  
*"Using Playwright in Python, navigate to [TARGET_URL], wait for the element [data-testid='price'], and print its text."*

---

### Step 1.3: Canonical Specs (PDF Parsing)
**Tool**: PyMuPDF (fitz)  

**Inputs**: Provided PDFs  
**Outputs**:  
- `lenovo_e14_intel_specs.json`  
- `lenovo_e14_amd_specs.json`  
- `hp_probook_450_specs.json`  
- `hp_probook_440_specs.json`  

**Process**:
1. Extract text from PDFs.  
2. Regex/keyword search for fields (CPU, RAM, Storage, Ports, Display, Battery, Connectivity).  
3. Save structured JSON per model.  

---

### Step 1.4: Database Schema
**Tool**: SQLite (for local demo)  

**Tables**:
- **laptops**: id, brand, model_name, specs_json  
- **offers**: id, laptop_id, price, currency, is_available, timestamp  
- **reviews**: id, laptop_id, rating, review_text, timestamp  
- **qna**: id, laptop_id, question, answer, timestamp  

---

### Step 1.5: Data Ingestion
**Script**: `ingest_data.py`  

**Process**:
1. Run scraper (`scraper.py`) and PDF parser (`pdf_parser.py`).  
2. Create/update SQLite DB.  
3. Insert laptops (from specs).  
4. Insert offers, reviews, and Q&A (from scraper JSON).  

---

## Phase 2: Backend API
**Tool**: FastAPI  

**Endpoints**:
- `GET /api/v1/laptops` (filterable by brand, model, price, specs)  
- `GET /api/v1/laptops/{id}`  
- `GET /api/v1/laptops/{id}/offers`  
- `GET /api/v1/laptops/{id}/reviews`  
- `GET /api/v1/laptops/{id}/qna`  
- `POST /api/v1/chat` (natural language Q&A with citations)  
- `POST /api/v1/recommend` (recommend configs based on budget/specs)  

---

## Phase 3: LLM Intelligence
**Tool**: Google Gemini API  

- **Chatbot (`/chat`)**:  
  - RAG pipeline fetches specs + market data from DB.  
  - Injects into prompt.  
  - Returns natural language answer + citations (PDF for specs, PDP for offers).  

- **Recommender (`/recommend`)**:  
  - Filters laptops by budget/specs.  
  - LLM generates rationale and citations.  

---

## Phase 4: Front End
**Tool**: Vanilla HTML + JS + Chart.js  

**Components**:
- **Explore/Compare**: Table of laptops, filters, comparison view.  
- **Price Trends**: Chart.js line charts of price history.  
- **Reviews Intelligence**: Rating distribution + top review themes.  
- **Chat & Recommend**: Pane with chatbot and recommendations.  

---

## Phase 5: Deliverables
- **Public GitHub Repo** with:  
  - `scraper.py`  
  - `pdf_parser.py`  
  - `ingest_data.py`  
  - FastAPI app  
  - Frontend code  
  - SQLite DB schema + migrations  
  - Example outputs (`live_offers.json`, `live_reviews.json`, `*_specs.json`)  

- **README.md** with setup/run instructions.  
- **Schema Diagram** (PNG or Mermaid).  
- **Screen Recording (3–5 mins)** showing:  
  1. Scraper running.  
  2. API responses.  
  3. UI in action (explore, reviews, chat/recommend).  

---

## Live PDP URLs for Scraping
- [Lenovo ThinkPad E14 Gen 5 (Intel)](https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpade/thinkpad-e14-gen-5-14-inch-intel/len101t0064?srsltid=AfmBOooNPPXdBBurqIJ4MY8-Y67aKaeOYTYkOGehID-Qcr2473qxYrNWQ)  
- [Lenovo ThinkPad E14 Gen 5 (AMD)](https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpade/thinkpad-e14-gen-5-14-inch-amd/len101t0068?srsltid=AfmBOop_2D7HyC_aUBsVVcI3RiG9E5ZZdKu3fzripONG7BGs435Qax5s)  

- [HP ProBook 440 G11](https://www.hp.com/us-en/shop/pdp/hp-probook-440-14-inch-g11-notebook-pc)  
- [HP ProBook 450 G10 (US-EN PDP)](https://www.hp.com/us-en/shop/pdp/hp-probook-450-156-inch-g10-notebook-pc-wolf-pro-security-edition-p-8l0e0ua-aba-1)  
