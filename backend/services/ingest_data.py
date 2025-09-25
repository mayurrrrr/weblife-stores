"""Data ingestion script to populate the database with scraped data and PDF specifications."""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Laptop, Offer, Review, QnA, create_tables
from services.pdf_parser import PDFParser
from services import unified_scraper  # use unified scraper instead of old scraper
from app.config import PDF_MAPPINGS

class DataIngestion:
    def __init__(self):
        self.db = SessionLocal()
        self.laptop_mapping = {}  # Maps model_key to laptop_id
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def clear_existing_data(self):
        """Clear existing data from all tables."""
        print("Clearing existing data...")
        self.db.query(QnA).delete()
        self.db.query(Review).delete()
        self.db.query(Offer).delete()
        self.db.query(Laptop).delete()
        self.db.commit()
        print("Existing data cleared.")
    
    def ingest_laptop_specs(self, specs_data: dict):
        """Ingest laptop specifications into the database."""
        print("Ingesting laptop specifications...")
        
        model_brand_mapping = {
            "lenovo_e14_intel": ("Lenovo", "ThinkPad E14 Gen 5 (Intel)"),
            "lenovo_e14_amd": ("Lenovo", "ThinkPad E14 Gen 5 (AMD)"),
            "hp_probook_440": ("HP", "ProBook 440 G11"),
            "hp_probook_450": ("HP", "ProBook 450 G10"),
        }
        
        for model_key, spec_data in specs_data.items():
            brand, model_name = model_brand_mapping.get(model_key, ("Unknown", model_key))
            
            laptop = Laptop(
                brand=brand,
                model_name=model_name,
                specs_json=json.dumps(spec_data.get("specifications", {}))
            )
            
            self.db.add(laptop)
            self.db.flush()  # Get the ID without committing
            
            self.laptop_mapping[model_key] = laptop.id
            print(f"Added laptop: {brand} {model_name} (ID: {laptop.id})")
        
        self.db.commit()
        print(f"Ingested {len(specs_data)} laptop specifications.")
    
    def ingest_offers(self, offers_data: dict):
        """Ingest offer data into the database."""
        print("Ingesting offers...")
        total_offers = 0
        
        for model_key, offers in offers_data.items():
            laptop_id = self.laptop_mapping.get(model_key)
            if not laptop_id:
                print(f"No laptop found for model key: {model_key}")
                continue
            
            for offer_data in offers:
                price_val = offer_data.get("price")
                if price_val is None:
                    price_val = 0.0  # avoid NOT NULL violation
                currency_val = offer_data.get("currency") or "USD"
                shipping_eta_val = offer_data.get("shipping_eta") or offer_data.get("availability_text") or ""
                promotions_val = offer_data.get("promotions", []) or []
                ts_raw = offer_data.get("timestamp", datetime.utcnow().isoformat())
                try:
                    ts_val = datetime.fromisoformat(ts_raw)
                except Exception:
                    ts_val = datetime.utcnow()

                offer = Offer(
                    laptop_id=laptop_id,
                    price=float(price_val),
                    currency=currency_val,
                    is_available=offer_data.get("is_available", True),
                    shipping_eta=shipping_eta_val,
                    promotions=json.dumps(promotions_val),
                    timestamp=ts_val,
                    seller=offer_data.get("seller")
                )
                self.db.add(offer)
                total_offers += 1
        
        self.db.commit()
        print(f"Ingested {total_offers} offers.")
    
    def ingest_reviews(self, reviews_data: dict):
        """Ingest review data into the database."""
        print("Ingesting reviews...")
        total_reviews = 0
        
        for model_key, reviews in reviews_data.items():
            laptop_id = self.laptop_mapping.get(model_key)
            if not laptop_id:
                print(f"No laptop found for model key: {model_key}")
                continue
            
            for review_data in reviews:
                review = Review(
                    laptop_id=laptop_id,
                    rating=review_data.get("rating", 0.0) or 0.0,
                    review_text=review_data.get("review_text", "") or review_data.get("body", ""),
                    author=review_data.get("author", "Anonymous"),
                    timestamp=datetime.fromisoformat(review_data.get("timestamp", datetime.utcnow().isoformat()))
                )
                self.db.add(review)
                total_reviews += 1
        
        self.db.commit()
        print(f"Ingested {total_reviews} reviews.")
    
    def ingest_qna(self, qna_data: dict):
        """Ingest Q&A data into the database."""
        print("Ingesting Q&A...")
        total_qna = 0
        
        for model_key, qnas in qna_data.items():
            laptop_id = self.laptop_mapping.get(model_key)
            if not laptop_id:
                print(f"No laptop found for model key: {model_key}")
                continue
            
            for qna_item in qnas:
                qna = QnA(
                    laptop_id=laptop_id,
                    question=qna_item.get("question", ""),
                    answer=qna_item.get("answer", ""),
                    timestamp=datetime.fromisoformat(qna_item.get("timestamp", datetime.utcnow().isoformat()))
                )
                self.db.add(qna)
                total_qna += 1
        
        self.db.commit()
        print(f"Ingested {total_qna} Q&A items.")
    
    def load_json_file(self, filename: str) -> dict:
        """Load data from a JSON file."""
        file_path = Path(filename)
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            print(f"File not found: {filename}")
            return {}
    
    async def run_full_ingestion(self, clear_existing: bool = True):
        """Run the complete data ingestion process."""
        print("Starting full data ingestion process...")
        
        # Create tables if they don't exist
        create_tables()
        
        if clear_existing:
            self.clear_existing_data()
        
        # Step 1: Parse PDFs and get specifications
        print("\n=== Step 1: Parsing PDF specifications ===")
        pdf_parser = PDFParser()
        specs_data = pdf_parser.parse_all_pdfs()
        
        # Persist specs JSONs under data/specs for artifacts
        try:
            specs_dir = Path("../data/specs")
            specs_dir.mkdir(parents=True, exist_ok=True)
            # Combined file
            (specs_dir / "specs.json").write_text(json.dumps(specs_data, indent=2), encoding="utf-8")
            # Per-model files
            for model_key, spec in (specs_data or {}).items():
                (specs_dir / f"{model_key}.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
            # Relocate any stray root-level spec files
            try:
                project_root = Path("..").resolve()
                for stray in project_root.glob("*_specs.json"):
                    target = specs_dir / stray.name
                    try:
                        stray.replace(target)
                        print(f"Moved {stray.name} -> {target}")
                    except Exception as move_err:
                        print(f"Warning: could not move {stray}: {move_err}")
            except Exception as scan_err:
                print(f"Warning: failed scanning for stray specs: {scan_err}")
            print(f"Saved specs artifacts to {specs_dir}")
        except Exception as e:
            print(f"Warning: failed to save specs artifacts: {e}")
        
        if specs_data:
            self.ingest_laptop_specs(specs_data)
        else:
            print("No PDF specifications found. Creating placeholder laptops...")
            placeholder_specs = {
                "lenovo_e14_intel": {"specifications": {"cpu": ["Intel processor"], "ram": ["8GB"], "storage": ["256GB SSD"]}},
                "lenovo_e14_amd": {"specifications": {"cpu": ["AMD processor"], "ram": ["8GB"], "storage": ["256GB SSD"]}},
                "hp_probook_440": {"specifications": {"cpu": ["Intel processor"], "ram": ["8GB"], "storage": ["256GB SSD"]}},
                "hp_probook_450": {"specifications": {"cpu": ["Intel processor"], "ram": ["8GB"], "storage": ["512GB SSD"]}},
            }
            # Also save placeholder specs to artifacts for consistency
            try:
                specs_dir = Path("../data/specs")
                specs_dir.mkdir(parents=True, exist_ok=True)
                (specs_dir / "specs.json").write_text(json.dumps(placeholder_specs, indent=2), encoding="utf-8")
                for model_key, spec in placeholder_specs.items():
                    (specs_dir / f"{model_key}.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
                print(f"Saved placeholder specs artifacts to {specs_dir}")
            except Exception as e:
                print(f"Warning: failed to save placeholder specs artifacts: {e}")
            self.ingest_laptop_specs(placeholder_specs)
        
        # Step 2: Load existing data (offers from scraper, reviews/QnA from dummy data)
        print("\n=== Step 2: Scraping live offers data only ===")
        try:
            # Only scrape offers (working scraper), preserve dummy reviews/QnA
            await unified_scraper.main()
            print("✅ Offers scraping completed")
            
            # Ingest data from files
            print("\n=== Step 3: Ingesting data ===")
            offers_data = self.load_json_file("../data/live/live_offers.json")
            reviews_data = self.load_json_file("../data/live/live_reviews.json")
            qna_data = self.load_json_file("../data/live/live_qna.json")
            
            if offers_data:
                print("📊 Ingesting scraped offers data...")
                self.ingest_offers(offers_data)
            if reviews_data:
                print("📝 Ingesting dummy reviews data...")
                self.ingest_reviews(reviews_data)
            if qna_data:
                print("❓ Ingesting dummy Q&A data...")
                self.ingest_qna(qna_data)
        
        except Exception as e:
            print(f"Error during unified scraping: {e}")
            print("Attempting to load existing scraped data...")
            self.db.rollback()
            
            offers_data = self.load_json_file("../data/live/live_offers.json")
            reviews_data = self.load_json_file("../data/live/live_reviews.json")
            qna_data = self.load_json_file("../data/live/live_qna.json")
            
            if offers_data or reviews_data or qna_data:
                print("\n=== Step 3: Ingesting existing scraped data ===")
                if offers_data:
                    self.ingest_offers(offers_data)
                if reviews_data:
                    self.ingest_reviews(reviews_data)
                if qna_data:
                    self.ingest_qna(qna_data)
            else:
                print("No existing scraped data found. Creating sample data...")
                self.create_sample_data()
        
        print("\n=== Data ingestion completed! ===")
        self.print_summary()
    
    def create_sample_data(self):
        """Create sample data for demonstration purposes."""
        print("Creating sample data...")
        
        sample_offers = {}
        sample_reviews = {}
        
        for model_key, laptop_id in self.laptop_mapping.items():
            sample_offers[model_key] = [{
                "price": 899.99 if "lenovo" in model_key else 799.99,
                "currency": "USD",
                "is_available": True,
                "availability_text": "In Stock",
                "promotions": ["10% Student Discount"],
                "timestamp": datetime.utcnow().isoformat()
            }]
            sample_reviews[model_key] = [
                {
                    "rating": 4.5,
                    "review_text": "Great laptop for business use. Fast performance and good build quality.",
                    "author": "Business User",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        
        self.ingest_offers(sample_offers)
        self.ingest_reviews(sample_reviews)
    
    def print_summary(self):
        """Print a summary of the ingested data."""
        laptop_count = self.db.query(Laptop).count()
        offer_count = self.db.query(Offer).count()
        review_count = self.db.query(Review).count()
        qna_count = self.db.query(QnA).count()
        
        print(f"\n=== Database Summary ===")
        print(f"Laptops: {laptop_count}")
        print(f"Offers: {offer_count}")
        print(f"Reviews: {review_count}")
        print(f"Q&A: {qna_count}")
        print(f"Total records: {laptop_count + offer_count + review_count + qna_count}")

async def main():
    ingestion = DataIngestion()
    await ingestion.run_full_ingestion(clear_existing=True)

if __name__ == "__main__":
    asyncio.run(main())
