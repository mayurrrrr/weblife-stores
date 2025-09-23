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
│   (Playwright)  │───▶│   (PyMuPDF)      │───▶│   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐           │
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
   cp env_example.txt .env
   # Edit .env and add your Google Gemini API key
   ```

5. **Run the application**
   ```bash
   python scripts/run.py
   ```

6. **Open your browser**
   Navigate to `http://localhost:8000`

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

**Scrape live data only:**
```bash
cd backend && python -m services.scraper
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
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
├── README.md            # This documentation file
├── requirements.txt     # Python dependencies
├── env_example.txt      # Environment variables template
├── backend/             # Backend application
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   ├── app/             # Core application modules
│   │   ├── __init__.py
│   │   ├── config.py    # Configuration settings
│   │   ├── database.py  # Database models and setup
│   │   └── api_models.py # Pydantic models for API
│   └── services/        # Business logic services
│       ├── __init__.py
│       ├── llm_service.py    # Google Gemini integration
│       ├── pdf_parser.py     # PDF specification extraction
│       ├── scraper.py        # Web scraping with Playwright
│       └── ingest_data.py    # Data ingestion pipeline
├── frontend/            # Frontend application
│   └── static/          # Static web files
│       ├── index.html   # Main HTML page
│       ├── style.css    # Custom styles
│       └── app.js       # Frontend JavaScript
├── data/                # Data storage
│   ├── pdfs/           # Laptop specification PDFs
│   │   ├── ThinkPad_E14_Gen_5_Intel_Spec.pdf
│   │   ├── ThinkPad_E14_Gen_5_AMD_Spec.pdf
│   │   ├── hp-probook-440.pdf
│   │   └── hp-probook-450.pdf
│   └── laptop_intelligence.db # SQLite database (created automatically)
├── scripts/             # Utility scripts
│   └── run.py          # Application startup script
└── docs/               # Documentation
    └── prd.md          # Product Requirements Document
```

### Adding New Laptops

1. **Add PDF specifications**: Place PDF files in the `data/pdfs/` directory
2. **Update configuration**: Add entries to `backend/app/config.py`:
   ```python
   PDF_MAPPINGS = {
       "new_laptop_model": "../../data/pdfs/new_laptop_spec.pdf"
   }
   
   SCRAPING_URLS = {
       "new_laptop_model": "https://official-store-url"
   }
   ```
3. **Update scraper**: Add brand-specific scraping logic in `backend/services/scraper.py`
4. **Re-run ingestion**: `python scripts/run.py`

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
- Ensure PDF files are in the root directory
- Check file names match those in `config.py`

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
# Reset database
rm data/laptop_intelligence.db
cd backend && python -c "from app.database import create_tables; create_tables()"
python scripts/run.py
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
