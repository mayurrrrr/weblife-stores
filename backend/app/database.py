"""Database models and setup for the Laptop Intelligence Engine."""

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
from app.config import DATABASE_URL

Base = declarative_base()

class Laptop(Base):
    __tablename__ = "laptops"
    
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    specs_json = Column(Text, nullable=False)  # JSON string of specifications
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    offers = relationship("Offer", back_populates="laptop")
    reviews = relationship("Review", back_populates="laptop")
    qna = relationship("QnA", back_populates="laptop")
    
    @property
    def specs(self):
        """Parse specs_json into a dictionary."""
        return json.loads(self.specs_json) if self.specs_json else {}

class Offer(Base):
    __tablename__ = "offers"
    
    id = Column(Integer, primary_key=True, index=True)
    laptop_id = Column(Integer, ForeignKey("laptops.id"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    is_available = Column(Boolean, default=True)
    shipping_eta = Column(String(50))
    promotions = Column(Text)  # JSON string of promotions
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    laptop = relationship("Laptop", back_populates="offers")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    laptop_id = Column(Integer, ForeignKey("laptops.id"), nullable=False)
    rating = Column(Float, nullable=False)
    review_text = Column(Text)
    author = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    laptop = relationship("Laptop", back_populates="reviews")

class QnA(Base):
    __tablename__ = "qna"
    
    id = Column(Integer, primary_key=True, index=True)
    laptop_id = Column(Integer, ForeignKey("laptops.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    laptop = relationship("Laptop", back_populates="qna")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
