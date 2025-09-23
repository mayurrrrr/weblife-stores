"""Web scraper to extract live data from Lenovo and HP product pages."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Page
from app.config import SCRAPING_URLS, SCRAPING_DELAY, HEADLESS_BROWSER, BROWSER_TIMEOUT

class LaptopScraper:
    def __init__(self):
        self.results = {
            "offers": {},
            "reviews": {},
            "qna": {}
        }
    
    async def create_browser_context(self, playwright):
        """Create a browser context with appropriate settings."""
        browser = await playwright.chromium.launch(
            headless=HEADLESS_BROWSER,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        return browser, context
    
    async def wait_for_page_load(self, page: Page, selectors: List[str], timeout: int = 10000):
        """Wait for any of the given selectors to appear on the page."""
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                return selector
            except:
                continue
        return None
    
    async def scrape_lenovo_page(self, page: Page, model_key: str) -> Dict[str, Any]:
        """Scrape Lenovo product page for offers, reviews, and Q&A."""
        result = {"offers": [], "reviews": [], "qna": []}
        
        try:
            # Price and availability selectors for Lenovo
            price_selectors = [
                '[data-testid="price"]',
                '.price-final',
                '.price-current',
                '.sr-price',
                '.price'
            ]
            
            # Wait for price to load
            found_selector = await self.wait_for_page_load(page, price_selectors)
            
            if found_selector:
                # Extract price
                price_element = await page.query_selector(found_selector)
                if price_element:
                    price_text = await price_element.text_content()
                    price_match = re.search(r'[\$]?([0-9,]+\.?[0-9]*)', price_text.replace(',', ''))
                    if price_match:
                        price = float(price_match.group(1))
                        
                        # Check availability
                        availability_selectors = [
                            '[data-testid="availability"]',
                            '.availability',
                            '.stock-status'
                        ]
                        
                        is_available = True
                        availability_text = ""
                        for selector in availability_selectors:
                            avail_element = await page.query_selector(selector)
                            if avail_element:
                                availability_text = await avail_element.text_content()
                                if any(word in availability_text.lower() for word in ['out of stock', 'unavailable', 'discontinued']):
                                    is_available = False
                                break
                        
                        # Extract promotions
                        promo_selectors = [
                            '.promotion',
                            '.deal',
                            '.offer',
                            '[data-testid="promotion"]'
                        ]
                        
                        promotions = []
                        for selector in promo_selectors:
                            promo_elements = await page.query_selector_all(selector)
                            for element in promo_elements:
                                promo_text = await element.text_content()
                                if promo_text and promo_text.strip():
                                    promotions.append(promo_text.strip())
                        
                        result["offers"].append({
                            "price": price,
                            "currency": "USD",
                            "is_available": is_available,
                            "availability_text": availability_text,
                            "promotions": promotions,
                            "timestamp": datetime.utcnow().isoformat()
                        })
            
            # Extract reviews (if available)
            review_selectors = [
                '.review',
                '.rating',
                '[data-testid="review"]'
            ]
            
            for selector in review_selectors:
                review_elements = await page.query_selector_all(selector)
                for element in review_elements[:5]:  # Limit to first 5 reviews
                    try:
                        review_text = await element.text_content()
                        # Try to extract rating
                        rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*5', review_text)
                        rating = float(rating_match.group(1)) if rating_match else None
                        
                        if review_text and len(review_text.strip()) > 10:
                            result["reviews"].append({
                                "rating": rating,
                                "review_text": review_text.strip(),
                                "author": "Anonymous",
                                "timestamp": datetime.utcnow().isoformat()
                            })
                    except:
                        continue
                
                if result["reviews"]:
                    break
        
        except Exception as e:
            print(f"Error scraping Lenovo page for {model_key}: {e}")
        
        return result
    
    async def scrape_hp_page(self, page: Page, model_key: str) -> Dict[str, Any]:
        """Scrape HP product page for offers, reviews, and Q&A."""
        result = {"offers": [], "reviews": [], "qna": []}
        
        try:
            # Price selectors for HP
            price_selectors = [
                '[data-testid="price-current"]',
                '.price-current',
                '.price',
                '.product-price',
                '.price-value'
            ]
            
            found_selector = await self.wait_for_page_load(page, price_selectors)
            
            if found_selector:
                price_element = await page.query_selector(found_selector)
                if price_element:
                    price_text = await price_element.text_content()
                    price_match = re.search(r'[\$]?([0-9,]+\.?[0-9]*)', price_text.replace(',', ''))
                    if price_match:
                        price = float(price_match.group(1))
                        
                        # Check availability for HP
                        availability_selectors = [
                            '[data-testid="availability"]',
                            '.availability-status',
                            '.stock-status',
                            '.product-availability'
                        ]
                        
                        is_available = True
                        availability_text = ""
                        for selector in availability_selectors:
                            avail_element = await page.query_selector(selector)
                            if avail_element:
                                availability_text = await avail_element.text_content()
                                if any(word in availability_text.lower() for word in ['out of stock', 'unavailable', 'discontinued']):
                                    is_available = False
                                break
                        
                        result["offers"].append({
                            "price": price,
                            "currency": "USD",
                            "is_available": is_available,
                            "availability_text": availability_text,
                            "promotions": [],
                            "timestamp": datetime.utcnow().isoformat()
                        })
        
        except Exception as e:
            print(f"Error scraping HP page for {model_key}: {e}")
        
        return result
    
    async def scrape_single_url(self, context, url: str, model_key: str) -> Dict[str, Any]:
        """Scrape a single URL and return the extracted data."""
        page = await context.new_page()
        
        try:
            print(f"Scraping {model_key}: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT)
            
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Determine scraper based on URL
            if "lenovo.com" in url:
                result = await self.scrape_lenovo_page(page, model_key)
            elif "hp.com" in url:
                result = await self.scrape_hp_page(page, model_key)
            else:
                result = {"offers": [], "reviews": [], "qna": []}
            
            print(f"Scraped {model_key}: {len(result['offers'])} offers, {len(result['reviews'])} reviews")
            return result
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {"offers": [], "reviews": [], "qna": []}
        
        finally:
            await page.close()
    
    async def scrape_all_urls(self) -> Dict[str, Any]:
        """Scrape all URLs and return combined results."""
        async with async_playwright() as playwright:
            browser, context = await self.create_browser_context(playwright)
            
            try:
                all_results = {}
                
                for model_key, url in SCRAPING_URLS.items():
                    result = await self.scrape_single_url(context, url, model_key)
                    all_results[model_key] = result
                    
                    # Add delay between requests
                    await asyncio.sleep(SCRAPING_DELAY)
                
                return all_results
                
            finally:
                await browser.close()
    
    def save_results(self, results: Dict[str, Any]):
        """Save scraping results to JSON files."""
        # Save combined results
        with open("live_data.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save separate files for each data type
        offers_data = {}
        reviews_data = {}
        qna_data = {}
        
        for model_key, data in results.items():
            offers_data[model_key] = data.get("offers", [])
            reviews_data[model_key] = data.get("reviews", [])
            qna_data[model_key] = data.get("qna", [])
        
        with open("live_offers.json", 'w') as f:
            json.dump(offers_data, f, indent=2)
        
        with open("live_reviews.json", 'w') as f:
            json.dump(reviews_data, f, indent=2)
        
        with open("live_qna.json", 'w') as f:
            json.dump(qna_data, f, indent=2)
        
        print("Scraping results saved to:")
        print("- live_data.json (combined)")
        print("- live_offers.json")
        print("- live_reviews.json") 
        print("- live_qna.json")

async def main():
    """Main function to run the scraper."""
    scraper = LaptopScraper()
    results = await scraper.scrape_all_urls()
    scraper.save_results(results)
    
    # Print summary
    total_offers = sum(len(data.get("offers", [])) for data in results.values())
    total_reviews = sum(len(data.get("reviews", [])) for data in results.values())
    total_qna = sum(len(data.get("qna", [])) for data in results.values())
    
    print(f"\nScraping completed!")
    print(f"Total offers: {total_offers}")
    print(f"Total reviews: {total_reviews}")
    print(f"Total Q&A: {total_qna}")

if __name__ == "__main__":
    asyncio.run(main())
