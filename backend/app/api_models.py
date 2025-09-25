"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's question or message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")

class RecommendationRequest(BaseModel):
    budget_min: Optional[float] = Field(None, description="Minimum budget")
    budget_max: Optional[float] = Field(None, description="Maximum budget")
    preferred_brand: Optional[str] = Field(None, description="Preferred brand (Lenovo, HP)")
    use_case: Optional[str] = Field(None, description="Use case (business, gaming, student, etc.)")
    requirements: Optional[Dict[str, Any]] = Field(None, description="Specific requirements")

# Response models
class LaptopSpec(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    cpu: Optional[List[str]] = None
    ram: Optional[List[str]] = None
    storage: Optional[List[str]] = None
    display: Optional[List[str]] = None
    graphics: Optional[List[str]] = None
    battery: Optional[List[str]] = None
    ports: Optional[List[str]] = None
    dimensions: Optional[List[str]] = None
    weight: Optional[List[str]] = None
    operating_system: Optional[List[str]] = None

class OfferResponse(BaseModel):
    id: int
    price: float
    currency: str
    is_available: bool
    shipping_eta: Optional[str] = None
    promotions: List[str] = []
    timestamp: datetime
    seller: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    rating: float
    review_text: Optional[str] = None
    author: Optional[str] = None
    timestamp: datetime

class QnAResponse(BaseModel):
    id: int
    question: str
    answer: Optional[str] = None
    timestamp: datetime

class LaptopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    id: int
    brand: str
    model_name: str
    specifications: LaptopSpec
    created_at: datetime

class LaptopDetailResponse(LaptopResponse):
    latest_offer: Optional[OfferResponse] = None
    review_summary: Optional[Dict[str, Any]] = None
    total_reviews: int = 0
    total_qna: int = 0

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant's response")
    sources: List[str] = Field(default_factory=list, description="Sources used for the response")
    conversation_id: str = Field(..., description="Conversation ID for follow-up")

class RecommendationResponse(BaseModel):
    recommendations: List[LaptopDetailResponse]
    rationale: str = Field(..., description="Explanation of recommendations")
    sources: List[str] = Field(default_factory=list, description="Sources used")

# Removed unused APIResponse and LaptopFilter models

class AspectInsight(BaseModel):
    name: str
    mentions: int
    avg_rating: float

class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    count: int
    avg_rating: float

class ReviewInsightsResponse(BaseModel):
    laptop_id: int
    aspects: List[AspectInsight]
    trends: List[TrendPoint]
    summary: Optional[str] = None
