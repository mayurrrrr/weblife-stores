"""Main FastAPI application for the Laptop Intelligence Engine."""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from app.database import get_db, Laptop, Offer, Review, QnA
from app.api_models import (
    LaptopResponse, LaptopDetailResponse, OfferResponse, ReviewResponse, 
    QnAResponse, ChatRequest, ChatResponse, RecommendationRequest, 
    RecommendationResponse, APIResponse, LaptopFilter, LaptopSpec, ReviewInsightsResponse
)
from services.llm_service import LLMService
from app.config import API_PREFIX

app = FastAPI(
    title="Laptop Intelligence Engine",
    description="Cross-Marketplace Laptop Intelligence Engine with Live Data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Initialize LLM service
llm_service = LLMService()

@app.get("/")
async def read_root():
    """API root - redirect to proper frontend."""
    return {"message": "Laptop Intelligence Engine API", "frontend_url": "http://localhost:3001", "docs_url": "http://localhost:8000/docs"}

@app.get(f"{API_PREFIX}/laptops", response_model=List[LaptopResponse])
async def get_laptops(
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    available_only: bool = Query(False, description="Show only available laptops"),
    search_term: Optional[str] = Query(None, description="Search term"),
    db: Session = Depends(get_db)
):
    """Get all laptops with optional filtering."""
    try:
        print(f"[DEBUG] API called with params: brand={brand}, available_only={available_only}")
        
        query = db.query(Laptop)
        
        if brand:
            query = query.filter(Laptop.brand.ilike(f"%{brand}%"))
        
        if search_term:
            query = query.filter(
                Laptop.model_name.ilike(f"%{search_term}%") |
                Laptop.brand.ilike(f"%{search_term}%")
            )
        
        laptops = query.all()
        print(f"[DEBUG] Found {len(laptops)} laptops in database")
        
        # If no laptops found, return empty list
        if not laptops:
            print("[DEBUG] No laptops found in database")
            return []
        
        # Convert to response format (simplified - skip complex filtering for now)
        response_laptops = []
        for laptop in laptops:
            try:
                print(f"[DEBUG] Processing laptop: {laptop.brand} {laptop.model_name}")
                
                # Handle specs safely
                specs_dict = {}
                if laptop.specs and isinstance(laptop.specs, dict):
                    specs_dict = laptop.specs
                elif laptop.specs:
                    print(f"[DEBUG] Unexpected specs type: {type(laptop.specs)}")
                
                # Create LaptopSpec with only valid fields
                laptop_spec_fields = set(LaptopSpec.model_fields.keys())
                filtered_specs = {k: v for k, v in specs_dict.items() if k in laptop_spec_fields}
                laptop_spec = LaptopSpec(**filtered_specs)
                
                laptop_response = LaptopResponse(
                    id=laptop.id,
                    brand=laptop.brand,
                    model_name=laptop.model_name,
                    specifications=laptop_spec,
                    created_at=laptop.created_at
                )
                response_laptops.append(laptop_response)
                print(f"[DEBUG] Successfully processed laptop {laptop.id}")
                
            except Exception as laptop_error:
                print(f"[ERROR] Failed to process laptop {laptop.id}: {laptop_error}")
                # Skip this laptop and continue with others
                continue
        
        print(f"[DEBUG] Returning {len(response_laptops)} laptops")
        return response_laptops
        
    except Exception as e:
        print(f"[ERROR] API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching laptops: {str(e)}")

@app.get(f"{API_PREFIX}/laptops/{{laptop_id}}", response_model=LaptopDetailResponse)
async def get_laptop_detail(laptop_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific laptop."""
    try:
        laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
        if not laptop:
            raise HTTPException(status_code=404, detail="Laptop not found")
        
        # Get latest offer
        latest_offer = db.query(Offer).filter(
            Offer.laptop_id == laptop_id
        ).order_by(Offer.timestamp.desc()).first()
        
        # Get review summary
        reviews = db.query(Review).filter(Review.laptop_id == laptop_id).all()
        total_reviews = len(reviews)
        avg_rating = sum(r.rating for r in reviews if r.rating) / total_reviews if total_reviews > 0 else 0
        
        # Get Q&A count
        total_qna = db.query(QnA).filter(QnA.laptop_id == laptop_id).count()
        
        # Prepare response
        specs_dict = laptop.specs if laptop.specs else {}
        laptop_spec = LaptopSpec(**{k: v for k, v in specs_dict.items() if k in LaptopSpec.__fields__})
        
        offer_response = None
        if latest_offer:
            promotions = []
            if latest_offer.promotions:
                try:
                    promotions = json.loads(latest_offer.promotions)
                except:
                    promotions = []
            
            offer_response = OfferResponse(
                id=latest_offer.id,
                price=latest_offer.price,
                currency=latest_offer.currency,
                is_available=latest_offer.is_available,
                shipping_eta=latest_offer.shipping_eta,
                promotions=promotions,
                timestamp=latest_offer.timestamp,
                seller=getattr(latest_offer, 'seller', None)
            )
        
        review_summary = {
            "average_rating": round(avg_rating, 1),
            "total_reviews": total_reviews,
            "rating_distribution": {}
        }
        
        # Calculate rating distribution
        if reviews:
            rating_counts = {}
            for review in reviews:
                if review.rating:
                    rating = int(review.rating)
                    rating_counts[rating] = rating_counts.get(rating, 0) + 1
            review_summary["rating_distribution"] = rating_counts
        
        return LaptopDetailResponse(
            id=laptop.id,
            brand=laptop.brand,
            model_name=laptop.model_name,
            specifications=laptop_spec,
            created_at=laptop.created_at,
            latest_offer=offer_response,
            review_summary=review_summary,
            total_reviews=total_reviews,
            total_qna=total_qna
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching laptop details: {str(e)}")

@app.get(f"{API_PREFIX}/laptops/{{laptop_id}}/offers", response_model=List[OfferResponse])
async def get_laptop_offers(laptop_id: int, db: Session = Depends(get_db)):
    """Get all offers for a specific laptop."""
    try:
        laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
        if not laptop:
            raise HTTPException(status_code=404, detail="Laptop not found")
        
        offers = db.query(Offer).filter(
            Offer.laptop_id == laptop_id
        ).order_by(Offer.timestamp.desc()).all()
        
        offer_responses = []
        for offer in offers:
            promotions = []
            if offer.promotions:
                try:
                    promotions = json.loads(offer.promotions)
                except:
                    promotions = []
            
            offer_responses.append(OfferResponse(
                id=offer.id,
                price=offer.price,
                currency=offer.currency,
                is_available=offer.is_available,
                shipping_eta=offer.shipping_eta,
                promotions=promotions,
                timestamp=offer.timestamp,
                seller=getattr(offer, 'seller', None)
            ))
        
        return offer_responses
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching offers: {str(e)}")

@app.get(f"{API_PREFIX}/laptops/{{laptop_id}}/reviews", response_model=List[ReviewResponse])
async def get_laptop_reviews(laptop_id: int, db: Session = Depends(get_db)):
    """Get all reviews for a specific laptop."""
    try:
        laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
        if not laptop:
            raise HTTPException(status_code=404, detail="Laptop not found")
        
        reviews = db.query(Review).filter(
            Review.laptop_id == laptop_id
        ).order_by(Review.timestamp.desc()).all()
        
        return [ReviewResponse(
            id=review.id,
            rating=review.rating,
            review_text=review.review_text,
            author=review.author,
            timestamp=review.timestamp
        ) for review in reviews]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reviews: {str(e)}")

@app.get(f"{API_PREFIX}/laptops/{{laptop_id}}/qna", response_model=List[QnAResponse])
async def get_laptop_qna(laptop_id: int, db: Session = Depends(get_db)):
    """Get all Q&A for a specific laptop."""
    try:
        laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
        if not laptop:
            raise HTTPException(status_code=404, detail="Laptop not found")
        
        qnas = db.query(QnA).filter(
            QnA.laptop_id == laptop_id
        ).order_by(QnA.timestamp.desc()).all()
        
        return [QnAResponse(
            id=qna.id,
            question=qna.question,
            answer=qna.answer,
            timestamp=qna.timestamp
        ) for qna in qnas]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Q&A: {str(e)}")

@app.post(f"{API_PREFIX}/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat requests with natural language Q&A."""
    try:
        response_text, sources, conversation_id = llm_service.chat(
            db=db,
            user_message=request.message,
            conversation_id=request.conversation_id
        )
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.post(f"{API_PREFIX}/recommend", response_model=RecommendationResponse)
async def recommend_endpoint(request: RecommendationRequest, db: Session = Depends(get_db)):
    """Generate laptop recommendations based on criteria."""
    try:
        laptop_ids, rationale, sources = llm_service.recommend(
            db=db,
            budget_min=request.budget_min,
            budget_max=request.budget_max,
            preferred_brand=request.preferred_brand,
            use_case=request.use_case,
            requirements=request.requirements
        )
        
        # Get detailed laptop information
        recommendations = []
        for laptop_id in laptop_ids:
            try:
                laptop_detail = await get_laptop_detail(laptop_id, db)
                recommendations.append(laptop_detail)
            except:
                continue  # Skip if laptop details can't be fetched
        
        return RecommendationResponse(
            recommendations=recommendations,
            rationale=rationale,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get(f"{API_PREFIX}/laptops/{{laptop_id}}/reviews/insights", response_model=ReviewInsightsResponse)
async def get_review_insights(laptop_id: int, db: Session = Depends(get_db)):
    try:
        laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
        if not laptop:
            raise HTTPException(status_code=404, detail="Laptop not found")
        reviews = db.query(Review).filter(Review.laptop_id == laptop_id).all()
        # Trends by month (YYYY-MM)
        by_month: Dict[str, List[Review]] = {}
        for r in reviews:
            if not r.timestamp:
                continue
            month = r.timestamp.strftime("%Y-%m")
            by_month.setdefault(month, []).append(r)
        trends: List[Dict[str, Any]] = []
        for month in sorted(by_month.keys()):
            items = by_month[month]
            if not items:
                continue
            avg = sum([i.rating or 0 for i in items]) / len(items)
            trends.append({"month": month, "count": len(items), "avg_rating": round(avg, 2)})
        # Simple aspect buckets by keywords
        lexicon = {
            "battery": ["battery", "charge", "hours"],
            "display": ["display", "screen", "brightness", "color"],
            "keyboard": ["keyboard", "keys", "typing"],
            "performance": ["performance", "speed", "lag", "snappy"],
            "build": ["build", "chassis", "quality", "hinge"],
            "speakers": ["speaker", "audio", "sound"],
            "thermals": ["fan", "thermal", "hot", "warm", "cool"],
            "price": ["price", "value", "expensive", "cheap"],
            "portability": ["weight", "light", "portable"],
        }
        buckets: Dict[str, List[float]] = {k: [] for k in lexicon.keys()}
        for r in reviews:
            text = (r.review_text or "").lower()
            rating = float(r.rating or 0)
            for aspect, kws in lexicon.items():
                if any(kw in text for kw in kws):
                    buckets[aspect].append(rating)
        aspects: List[Dict[str, Any]] = []
        for aspect, ratings in buckets.items():
            if ratings:
                aspects.append({
                    "name": aspect,
                    "mentions": len(ratings),
                    "avg_rating": round(sum(ratings)/len(ratings), 2)
                })
        # Top aspects by mentions
        aspects.sort(key=lambda a: a["mentions"], reverse=True)
        summary = None
        return ReviewInsightsResponse(
            laptop_id=laptop_id,
            aspects=aspects[:6],
            trends=trends,
            summary=summary
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing insights: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
