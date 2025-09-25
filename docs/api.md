# Laptop Intelligence Engine API Documentation

Base URL: `http://localhost:8000`
API Prefix: `/api/v1`

## OpenAPI / Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## How to Run (dev)
1. Activate venv (Windows): `venv311\Scripts\activate`
2. Install deps (once): `pip install -r requirements.txt`
3. Start backend: `python scripts\run_backend.py` (or `uvicorn backend.main:app --reload`)
4. Start frontend: `python scripts\run_frontend.py` → visit `http://localhost:3001`
5. Optional: Re-ingest data: `python -m backend.services.ingest_data`

## Overview
- Versioned REST API providing laptop catalog/specs, offers & price history, reviews, Q&A, recommendations, and chat.
- Content-Type: `application/json` for requests and responses.
- Authentication: None (development mode).
- CORS: Enabled for all origins.

## Health/Root
GET `/` → Basic info and helpful URLs.

---
## Catalog & Specs
### List Laptops
GET `/api/v1/laptops`

Query Parameters (all optional):
- `brand`: string (e.g., `lenovo`, `hp`)
- `min_price`: number
- `max_price`: number
- `available_only`: boolean (default: false)
- `search_term`: string

Response: `LaptopResponse[]`
- `id`: number
- `brand`: string
- `model_name`: string
- `specifications`: `LaptopSpec`
- `created_at`: datetime (ISO8601)

`LaptopSpec`
- `cpu`, `ram`, `storage`, `display`, `graphics`, `battery`, `ports`, `dimensions`, `weight`, `operating_system`: string[] | null

Example:
```bash
curl "http://localhost:8000/api/v1/laptops?brand=lenovo&available_only=true"
```

### Laptop Detail
GET `/api/v1/laptops/{laptop_id}`

Path Params:
- `laptop_id`: number

Response: `LaptopDetailResponse`
- Inherits from `LaptopResponse`
- `latest_offer`: `OfferResponse | null`
- `review_summary`: object | null
  - `average_rating`: number
  - `total_reviews`: number
  - `rating_distribution`: { [rating: number]: count }
- `total_reviews`: number
- `total_qna`: number

Example:
```bash
curl "http://localhost:8000/api/v1/laptops/1"
```

---
## Offers & Price History
### All Offers for a Laptop
GET `/api/v1/laptops/{laptop_id}/offers`

Response: `OfferResponse[]`
- `id`: number
- `price`: number
- `currency`: string
- `is_available`: boolean
- `shipping_eta`: string | null
- `promotions`: string[]
- `timestamp`: datetime (ISO8601)
- `seller`: string | null

Example:
```bash
curl "http://localhost:8000/api/v1/laptops/1/offers"
```

---
## Reviews
### All Reviews for a Laptop
GET `/api/v1/laptops/{laptop_id}/reviews`

Response: `ReviewResponse[]`
- `id`: number
- `rating`: number
- `review_text`: string | null
- `author`: string | null
- `timestamp`: datetime (ISO8601)

Example:
```bash
curl "http://localhost:8000/api/v1/laptops/1/reviews"
```

---
## Q&A
### All Q&A for a Laptop
GET `/api/v1/laptops/{laptop_id}/qna`

Response: `QnAResponse[]`
- `id`: number
- `question`: string
- `answer`: string | null
- `timestamp`: datetime (ISO8601)

Example:
```bash
curl "http://localhost:8000/api/v1/laptops/1/qna"
```

---
## Recommendations
POST `/api/v1/recommend`

Request Body (all optional):
```json
{
  "budget_min": 700,
  "budget_max": 1200,
  "preferred_brand": "lenovo",
  "use_case": "business",
  "requirements": {
    "ram": "16GB",
    "storage": "512GB"
  }
}
```

Response: `RecommendationResponse`
- `recommendations`: `LaptopDetailResponse[]`
- `rationale`: string
- `sources`: string[]

Example:
```bash
curl -X POST "http://localhost:8000/api/v1/recommend" \
  -H "Content-Type: application/json" \
  -d '{"budget_min":700,"budget_max":1200,"preferred_brand":"lenovo"}'
```

---
## Chat / Query
POST `/api/v1/chat`

Request Body:
```json
{
  "message": "Which ThinkPad is best for travel under $1200?",
  "conversation_id": "optional-session-id"
}
```

Response: `ChatResponse`
- `response`: string
- `sources`: string[]
- `conversation_id`: string

Example:
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Best HP ProBook for office use?"}'
```

---
## Error Handling
Errors return standard FastAPI error envelopes:
```json
{
  "detail": "Error message here"
}
```
Common HTTP statuses:
- 400 Bad Request: invalid parameters/body
- 404 Not Found: resource not found (e.g., laptop_id)
- 500 Internal Server Error: unexpected server error

---
## Data Notes
- Specs are sourced from PDF parsing artifacts located under `data/specs/`.
- Offers (including `seller`) are scraped/written into `data/live/live_offers.json` and ingested into the DB.
- Reviews/Q&A are ingested from `data/live/{live_reviews.json, live_qna.json}` when available.
- The database is SQLite at `data/laptop_intelligence.db`.

---
## Changelog (relevant)
- Added `seller` to `OfferResponse` and underlying DB model.
- Price Trends UI consumes `/laptops/{id}/offers` and displays the latest `seller`.
