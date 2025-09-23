"""LLM service using Google Gemini API for chatbot and recommendations."""

import google.generativeai as genai
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.database import Laptop, Offer, Review, QnA
from app.config import GEMINI_API_KEY
import uuid

class LLMService:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            print("Warning: GEMINI_API_KEY not found. LLM features will be limited.")
            self.model = None
        
        self.conversations = {}  # Simple in-memory conversation storage
    
    def get_laptop_context(self, db: Session, laptop_ids: List[int] = None) -> str:
        """Get context about laptops from the database."""
        query = db.query(Laptop)
        if laptop_ids:
            query = query.filter(Laptop.id.in_(laptop_ids))
        
        laptops = query.all()
        context_parts = []
        
        for laptop in laptops:
            # Get latest offer
            latest_offer = db.query(Offer).filter(
                Offer.laptop_id == laptop.id
            ).order_by(Offer.timestamp.desc()).first()
            
            # Get review summary
            reviews = db.query(Review).filter(Review.laptop_id == laptop.id).all()
            avg_rating = sum(r.rating for r in reviews if r.rating) / len(reviews) if reviews else 0
            
            laptop_info = {
                "brand": laptop.brand,
                "model": laptop.model_name,
                "specifications": laptop.specs,
                "latest_price": latest_offer.price if latest_offer else "Not available",
                "availability": latest_offer.is_available if latest_offer else False,
                "average_rating": round(avg_rating, 1) if avg_rating else "No ratings",
                "review_count": len(reviews)
            }
            
            context_parts.append(f"Laptop: {laptop.brand} {laptop.model_name}")
            context_parts.append(f"Price: ${laptop_info['latest_price']}")
            context_parts.append(f"Available: {laptop_info['availability']}")
            context_parts.append(f"Rating: {laptop_info['average_rating']}/5 ({laptop_info['review_count']} reviews)")
            context_parts.append(f"Specifications: {json.dumps(laptop.specs, indent=2)}")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def create_chat_prompt(self, user_message: str, context: str, conversation_history: List[Dict] = None) -> str:
        """Create a prompt for the chatbot."""
        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_parts.append(f"{role.capitalize()}: {content}")
            history_text = "Conversation History:\n" + "\n".join(history_parts) + "\n"
        
        prompt = f"""You are a helpful laptop shopping assistant. You have access to current laptop data including specifications, prices, and reviews.

Available Laptop Data:
{context}

Guidelines:
- Provide helpful, accurate information based on the available data
- Compare laptops when asked
- Explain technical specifications in user-friendly terms
- Mention specific prices and availability when relevant
- If you don't have specific information, say so clearly
- Keep responses concise but informative

{history_text}

User: {user_message}"""
        
        return prompt
    
    def chat(self, db: Session, user_message: str, conversation_id: str = None) -> Tuple[str, List[str], str]:
        """Handle chat requests with context from database."""
        if not self.model:
            return self.fallback_response(user_message), [], conversation_id or str(uuid.uuid4())
        
        # Get conversation ID
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Get laptop context
        context = self.get_laptop_context(db)
        
        # Get conversation history
        conversation_history = self.conversations.get(conversation_id, [])
        
        # Create prompt
        prompt = self.create_chat_prompt(user_message, context, conversation_history)
        
        try:
            # Generate response
            response = self.model.generate_content(prompt)
            ai_response = response.text
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": ai_response})
            self.conversations[conversation_id] = conversation_history
            
            # Extract sources (simplified)
            sources = ["Live product data", "Official specifications"]
            
            return ai_response, sources, conversation_id
            
        except Exception as e:
            print(f"Error generating chat response: {e}")
            return f"Sorry, I encountered an error: {str(e)}", [], conversation_id
    
    def recommend(self, db: Session, budget_min: float = None, budget_max: float = None, 
                  preferred_brand: str = None, use_case: str = None, 
                  requirements: Dict[str, Any] = None) -> Tuple[List[int], str, List[str]]:
        """Generate laptop recommendations based on criteria."""
        
        # Filter laptops based on criteria
        query = db.query(Laptop)
        
        if preferred_brand:
            query = query.filter(Laptop.brand.ilike(f"%{preferred_brand}%"))
        
        laptops = query.all()
        
        # Filter by budget if specified
        filtered_laptops = []
        for laptop in laptops:
            latest_offer = db.query(Offer).filter(
                Offer.laptop_id == laptop.id
            ).order_by(Offer.timestamp.desc()).first()
            
            if latest_offer:
                price = latest_offer.price
                if budget_min and price < budget_min:
                    continue
                if budget_max and price > budget_max:
                    continue
            
            filtered_laptops.append(laptop)
        
        # Get context for filtered laptops
        laptop_ids = [laptop.id for laptop in filtered_laptops[:5]]  # Top 5
        context = self.get_laptop_context(db, laptop_ids)
        
        # Generate recommendation rationale
        if self.model:
            criteria_text = []
            if budget_min or budget_max:
                budget_range = f"${budget_min or 0}-${budget_max or 'unlimited'}"
                criteria_text.append(f"Budget: {budget_range}")
            if preferred_brand:
                criteria_text.append(f"Brand: {preferred_brand}")
            if use_case:
                criteria_text.append(f"Use case: {use_case}")
            
            criteria = ", ".join(criteria_text) if criteria_text else "general use"
            
            prompt = f"""Based on the following laptop data, provide recommendations for {criteria}.

Available Laptops:
{context}

Provide a clear rationale explaining why these laptops are good matches for the criteria. Be specific about features, value, and trade-offs."""
            
            try:
                response = self.model.generate_content(prompt)
                rationale = response.text
            except Exception as e:
                print(f"Error generating recommendation rationale: {e}")
                rationale = f"Based on your criteria ({criteria}), here are the available options that match your requirements."
        else:
            rationale = f"Here are the laptops that match your criteria."
        
        sources = ["Live pricing data", "Product specifications", "User reviews"]
        
        return laptop_ids, rationale, sources
    
    def fallback_response(self, user_message: str) -> str:
        """Provide a fallback response when LLM is not available."""
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ['compare', 'difference', 'vs']):
            return "I'd be happy to help you compare laptops! Please specify which models you'd like to compare, and I'll provide details about their specifications, pricing, and features."
        
        elif any(word in user_lower for word in ['recommend', 'suggest', 'best']):
            return "I can help recommend laptops based on your needs! Please let me know your budget, preferred brand, and intended use (business, gaming, student, etc.)."
        
        elif any(word in user_lower for word in ['price', 'cost', 'budget']):
            return "I have current pricing information for all laptops in our database. You can browse the available models or ask about specific ones."
        
        elif any(word in user_lower for word in ['spec', 'specification', 'feature']):
            return "I can provide detailed specifications for any laptop in our database, including CPU, RAM, storage, display, and more."
        
        else:
            return "I'm here to help with laptop shopping! I can compare models, provide recommendations, check current prices, and explain specifications. What would you like to know?"
