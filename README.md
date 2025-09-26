# Cross-Marketplace Laptop Intelligence Engine

A full-stack application that scrapes live data from Lenovo and HP official stores, merges it with canonical PDF specifications, and provides intelligent insights through an AI-powered interface.

## Features

- **Live Data Scraping**: Real-time price, availability, and review data from official stores
- **PDF Specification Parsing**: Automated extraction of technical specifications from PDF documents
- **AI-Powered Chatbot**: Natural language Q&A using Google Gemini API
- **Smart Recommendations**: Personalized laptop recommendations based on budget and use case
- **Interactive UI**: Modern web interface with comparison tools and price trend visualization
- **RESTful API**: Comprehensive API for accessing all laptop data

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │    │   PDF Parser     │    │   Database      │
│   (Playwright)  │───▶│   (PyMuPDF)      │───▶│   (SQLite)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐             │
│   Frontend      │    │   FastAPI        │◀──────────┘
│   (HTML/JS)     │◀───│   Backend        │
└─────────────────┘    └──────────────────┘
                                │
                       ┌──────────────────┐
                       │   Google Gemini  │
                       │   LLM Service    │
                       └──────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js (for Playwright browser installation)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd weblife-stores
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

4. **Set up environment variables**
   ```bash
   # If you have an env template, copy it; otherwise create .env manually
   # cp env_example.txt .env
   # Then edit .env and add your Google Gemini API key
   ```

5. **Run the application (startup script)**
   ```bash
   python scripts/run_backend.py
   ```

6. **Open your browser**
   Navigate to `http://localhost:8000` (API) and `http://localhost:3001` (frontend)

## API Endpoints

### Laptops
- `GET /api/v1/laptops` - List all laptops with filtering
- `GET /api/v1/laptops/{id}` - Get laptop details
- `GET /api/v1/laptops/{id}/offers` - Get price history
- `GET /api/v1/laptops/{id}/reviews` - Get reviews
- `GET /api/v1/laptops/{id}/qna` - Get Q&A

### AI Features
- `POST /api/v1/chat` - Chat with AI assistant
- `POST /api/v1/recommend` - Get personalized recommendations
- `GET /api/v1/laptops/{id}/reviews/insights` - Aggregated review trends and aspects
- `GET /health` - Service health check

### Example API Usage

```python
import requests

# Get all laptops
response = requests.get('http://localhost:8000/api/v1/laptops')
laptops = response.json()

# Chat with AI
response = requests.post('http://localhost:8000/api/v1/chat', json={
    'message': 'What is the best laptop for programming?'
})
chat_response = response.json()

# Get recommendations
response = requests.post('http://localhost:8000/api/v1/recommend', json={
    'budget_min': 800,
    'budget_max': 1200,
    'use_case': 'business'
})
recommendations = response.json()
```

## Data Sources

### Live Web Scraping
- **Lenovo ThinkPad E14 Gen 5 (Intel)**: Official Lenovo store
- **Lenovo ThinkPad E14 Gen 5 (AMD)**: Official Lenovo store  
- **HP ProBook 440 G11**: Official HP store
- **HP ProBook 450 G10**: Official HP store

### PDF Specifications
The application processes the following PDF documents for technical specifications:
- `ThinkPad_E14_Gen_5_Intel_Spec.pdf`
- `ThinkPad_E14_Gen_5_AMD_Spec.pdf`
- `hp-probook-440.pdf`
- `hp-probook-450.pdf`

## Configuration

### Environment Variables

Create a `.env` file based on `env_example.txt`:

```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_api_key_here

# Optional: Database configuration
DATABASE_URL=sqlite:///laptop_intelligence.db

# Optional: Scraping settings
HEADLESS_BROWSER=true
SCRAPING_DELAY=2
BROWSER_TIMEOUT=30000
```

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

## Usage Examples

### Running Individual Components

**Parse PDFs only:**
```bash
cd backend && python -m services.pdf_parser
```

**Scrape live data only (unified scraper):**
```bash
cd backend && python -m services.unified_scraper
```

**Run data ingestion only:**
```bash
cd backend && python -m services.ingest_data
```

**Start API server only:**
```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Features

1. **Explore Tab**: Browse and filter laptops with grid/list views
2. **Compare Tab**: Side-by-side specification comparison
3. **Price Trends**: Historical price visualization with Chart.js
4. **Reviews**: Rating distribution and recent reviews analysis
5. **AI Assistant**: Natural language queries and smart recommendations

### API Integration

The FastAPI backend provides a complete REST API:

```python
# Example: Filter laptops by brand and price
import requests

response = requests.get('http://localhost:8000/api/v1/laptops', params={
    'brand': 'lenovo',
    'min_price': 500,
    'max_price': 1000,
    'available_only': True
})

laptops = response.json()
```

## Database Schema

```sql
-- Laptops table
CREATE TABLE laptops (
    id INTEGER PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    specs_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Offers table (price history)
CREATE TABLE offers (
    id INTEGER PRIMARY KEY,
    laptop_id INTEGER REFERENCES laptops(id),
    price REAL NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    is_available BOOLEAN DEFAULT TRUE,
    shipping_eta VARCHAR(50),
    promotions TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    seller VARCHAR(100)
);

-- Reviews table
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    laptop_id INTEGER REFERENCES laptops(id),
    rating REAL NOT NULL,
    review_text TEXT,
    author VARCHAR(100),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Q&A table
CREATE TABLE qna (
    id INTEGER PRIMARY KEY,
    laptop_id INTEGER REFERENCES laptops(id),
    question TEXT NOT NULL,
    answer TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Development

### Project Structure

```
weblife-stores/
├── README.md
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── app/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── api_models.py
│   └── services/
│       ├── llm_service.py
│       ├── pdf_parser.py
│       ├── targets.py
│       ├── unified_scraper.py
│       └── ingest_data.py
├── frontend/
│   ├── server.py
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── data/
│   ├── pdfs/
│   │   ├── ThinkPad_E14_Gen_5_Intel_Spec.pdf
│   │   ├── ThinkPad_E14_Gen_5_AMD_Spec.pdf
│   │   ├── hp-probook-440.pdf
│   │   └── hp-probook-450.pdf
│   ├── live/
│   │   ├── live_offers.json
│   │   ├── live_reviews.json
│   │   └── live_qna.json
│   └── laptop_intelligence.db
├── scripts/
│   ├── run_backend.py
│   └── run_frontend.py
└── docs/
    ├── api.md
    ├── prd.md
    └── db-schema-diagram.png
```

### Adding New Laptops

1. **Add PDF specifications**: Place PDF files in the `data/pdfs/` directory
2. **Update targets**: Add entries in `backend/services/targets.py` for `pdp` and `reviews` URLs
   ```python
   TARGETS["new_laptop_model"] = {
       "pdp": "https://official-store-url",
       "reviews": ["https://official-store-url#reviews"]
   }
   ```
3. **Re-run ingestion**: `python scripts/run_backend.py`

### Extending the API

Add new endpoints in `backend/main.py`:

```python
@app.get("/api/v1/custom-endpoint")
async def custom_endpoint(db: Session = Depends(get_db)):
    # Your custom logic here
    return {"data": "custom response"}
```

## Troubleshooting

### Common Issues

**1. Playwright browser not found**
```bash
playwright install chromium
```

**2. PDF files not found**
- Ensure PDF files are in `data/pdfs/`
- Check file names match those in `data/pdfs/`

**3. Gemini API errors**
- Verify your API key is correct
- Check API quota limits
- Ensure the key has proper permissions

**4. Scraping failures**
- Website structure may have changed
- Check for rate limiting
- Verify target URLs are accessible

**5. Database errors**
```bash
# Reset database (Windows PowerShell)
Remove-Item data/laptop_intelligence.db -ErrorAction Ignore
python - <<EOF
from backend.app.database import create_tables
create_tables()
EOF
python scripts/run_backend.py
```

### Debug Mode

Run with debug logging:
```bash
cd backend && uvicorn main:app --log-level debug
```

## Performance Optimization

- **Caching**: Implement Redis for API response caching
- **Database**: Consider PostgreSQL for production
- **Scraping**: Use proxy rotation for large-scale scraping
- **Frontend**: Implement pagination for large datasets

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **Rate Limiting**: Implement rate limiting for API endpoints
- **Input Validation**: All user inputs are validated via Pydantic
- **CORS**: Configure CORS properly for production

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Playwright** for robust web scraping
- **FastAPI** for the high-performance API framework
- **Google Gemini** for AI capabilities
- **Chart.js** for beautiful data visualization
- **Bootstrap** for responsive UI components

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review existing GitHub issues
3. Create a new issue with detailed information

---

**Built with ❤️ for intelligent laptop shopping**
