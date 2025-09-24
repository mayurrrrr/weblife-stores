"""Web scraper to extract live data from Lenovo and HP product pages."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Page, Frame
from app.config import SCRAPING_URLS, SCRAPING_DELAY, HEADLESS_BROWSER, BROWSER_TIMEOUT
import json as _json

# Direct HP reviews pages (use only the provided link for faster path)
HP_REVIEWS_URLS = {
    "hp_probook_450": "https://www.hp.com/us-en/shop/reviews/hp-probook-450-156-inch-g10-notebook-pc-wolf-pro-security-edition-p-8l0e0ua-aba-1",
}

# ---------------- Offer helpers ----------------

def _money_to_float(val: Optional[Any]) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return float(val)
        except Exception:
            return None
    s = str(val)
    m = re.search(r"\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})", s.replace(",", ""))
    return float(m.group(1)) if m else None


def _pick_currency(val: Optional[Any]) -> Optional[str]:
    if val is None:
        return None
    s = str(val)
    if "$" in s or "USD" in s.upper():
        return "USD"
    return None

async def _read_jsonld(page: Page) -> List[Dict[str, Any]]:
    blocks = page.locator("script[type='application/ld+json']")
    n = await blocks.count()
    out: List[Dict[str, Any]] = []
    for i in range(n):
        raw = await blocks.nth(i).text_content()
        if not raw:
            continue
        try:
            data = _json.loads(raw)
            if isinstance(data, list):
                out.extend(data)
            else:
                out.append(data)
        except Exception:
            continue
    return out

# ------------------------------------------------

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
    
    async def dismiss_cookie_banners(self, page: Page):
        selectors = [
            "button:has-text('Accept all')",
            "button:has-text('Accept All')",
            "button:has-text('I Accept')",
            "button:has-text('I agree')",
            "#onetrust-accept-btn-handler",
            "button#truste-consent-button",
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(300)
                    break
            except Exception:
                continue

    async def auto_scroll(self, page: Page, max_steps: int = 4, step_px: int = 1000, wait_ms: int = 250):
        try:
            last_height = await page.evaluate("document.body.scrollHeight")
            for _ in range(max_steps):
                await page.mouse.wheel(0, step_px)
                await page.wait_for_timeout(wait_ms)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception:
            pass

    # --------------- Lenovo offers only -----------------
    async def scrape_lenovo_page(self, page: Page, model_key: str) -> Dict[str, Any]:
        result = {"offers": [], "reviews": [], "qna": []}
        try:
            await self.dismiss_cookie_banners(page)
            await self.auto_scroll(page, max_steps=4)

            # Prefer JSON-LD
            ld = await _read_jsonld(page)
            prod = {}
            for node in ld:
                t = node.get("@type")
                if (isinstance(t, str) and t.lower() == "product") or (isinstance(t, list) and "Product" in t):
                    prod = node
                    break

            offers = prod.get("offers") if isinstance(prod, dict) else {}
            agg = prod.get("aggregateRating") if isinstance(prod, dict) else {}

            # Price fallback: sequential selectors then regex
            price_text = None
            if not offers or not offers.get("price"):
                for sel in ["[data-test='pricingPrice']", "[data-testid='pricingPrice']", ".price"]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            price_text = await el.text_content()
                            break
                    except Exception:
                        continue
                if not price_text:
                    try:
                        tel = page.locator(r"text=/\$\s?\d[\d,]*\.?\d*/").first
                        if await tel.is_visible():
                            price_text = await tel.text_content()
                    except Exception:
                        pass

            # Availability
            availability = None
            if offers and offers.get("availability"):
                availability = str(offers.get("availability")).split("/")[-1]
            if not availability:
                for phrase, code in [
                    ("Add to cart", "InStock"),
                    ("In Stock", "InStock"),
                    ("Out of stock", "OutOfStock"),
                    ("Temporarily unavailable", "OutOfStock"),
                    ("Discontinued", "Discontinued"),
                    ("Coming Soon", "PreOrder"),
                ]:
                    try:
                        if await page.get_by_text(phrase, exact=False).first.is_visible():
                            availability = code
                            break
                    except Exception:
                        continue

            # Shipping ETA (best-effort)
            shipping_eta = None
            try:
                ship_el = page.locator(r"text=/Ships in|Delivery|Ship by/i").first
                if await ship_el.is_visible():
                    shipping_eta = (await ship_el.text_content() or "").strip()
            except Exception:
                pass

            # Promos
            promos = []
            for t in ["Weekly Deals", "Sale", "Save $", "Coupon", "Student Discount", "Free shipping"]:
                try:
                    if await page.get_by_text(t, exact=False).first.is_visible():
                        promos.append(t)
                except Exception:
                    continue

            price_val = offers.get("price") if isinstance(offers, dict) else None
            price = _money_to_float(price_val) or _money_to_float(price_text)
            cur = offers.get("priceCurrency") if isinstance(offers, dict) else None
            currency = cur or _pick_currency(price_val) or _pick_currency(price_text)

            if price is not None or availability:
                result["offers"].append({
                    "price": price if price is not None else 0.0,
                    "currency": currency or "USD",
                    "is_available": (availability or "").lower() in ("instock", "in stock", "preorder"),
                    "availability_text": availability or "",
                    "promotions": promos,
                    "shipping_eta": shipping_eta,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Skip Lenovo reviews/Q&A per request
        except Exception as e:
            print(f"Error scraping Lenovo page for {model_key}: {e}")
        return result

    # --------------- HP offers + direct reviews link kept disabled ---------------
    async def scrape_hp_page(self, page: Page, model_key: str) -> Dict[str, Any]:
        result = {"offers": [], "reviews": [], "qna": []}
        try:
            await self.dismiss_cookie_banners(page)
            await page.wait_for_timeout(500)
            await self.auto_scroll(page, max_steps=4)

            # Price via sequential selectors then regex
            price_text = None
            for sel in [
                "[data-automation-id='product-price']",
                "[data-testid='price']",
                "[data-automation='final-price']",
                ".product-price",
                ".price",
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible():
                        price_text = await el.text_content()
                        break
                except Exception:
                    continue
            if not price_text:
                try:
                    tel = page.locator(r"text=/\$\s?\d[\d,]*\.?\d*/").first
                    if await tel.is_visible():
                        price_text = await tel.text_content()
                except Exception:
                    pass

            price = _money_to_float(price_text)
            currency = _pick_currency(price_text)

            # Availability
            availability = "UNKNOWN"
            try:
                if await page.get_by_text("ADD TO CART", exact=False).first.is_visible():
                    availability = "IN_STOCK"
                elif await page.get_by_text("Out of stock", exact=False).first.is_visible():
                    availability = "OUT_OF_STOCK"
                elif await page.get_by_text("Customize & Buy", exact=False).first.is_visible():
                    availability = "CUSTOMIZABLE"
            except Exception:
                pass

            # Shipping ETA
            shipping_eta = None
            try:
                eta_el = page.locator(r"text=/Ships (in|by)|Delivery|Est\\. ship/i").first
                if await eta_el.is_visible():
                    shipping_eta = (await eta_el.text_content() or "").strip()
            except Exception:
                pass

            # Promos
            promos: List[str] = []
            for t in ["FREE Storewide Shipping", "3% back in HP Rewards", "Weekly Deals", "Save $", "Instant rebate"]:
                try:
                    if await page.get_by_text(t, exact=False).first.is_visible():
                        promos.append(t)
                except Exception:
                    continue

            if price is not None or availability != "UNKNOWN":
                result["offers"].append({
                    "price": price if price is not None else 0.0,
                    "currency": currency or "USD",
                    "is_available": availability in ("IN_STOCK", "CUSTOMIZABLE"),
                    "availability_text": availability,
                    "promotions": promos,
                    "shipping_eta": shipping_eta,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Skip reviews (Lenovo disabled; HP reviews handled elsewhere on demand)
        except Exception as e:
            print(f"Error scraping HP page for {model_key}: {e}")
        return result
    
    async def scrape_single_url(self, context, url: str, model_key: str) -> Dict[str, Any]:
        page = await context.new_page()
        
        try:
            print(f"Scraping {model_key}: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT)
            await page.wait_for_timeout(1000)
            
            if "lenovo.com" in url:
                result = await self.scrape_lenovo_page(page, model_key)
            elif "hp.com" in url:
                result = await self.scrape_hp_page(page, model_key)
            else:
                result = {"offers": [], "reviews": [], "qna": []}
            
            print(f"Scraped {model_key}: {len(result['offers'])} offers, {len(result['reviews'])} reviews, {len(result['qna'])} qna")
            return result
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {"offers": [], "reviews": [], "qna": []}
        
        finally:
            await page.close()
    
    async def scrape_all_urls(self) -> Dict[str, Any]:
        async with async_playwright() as playwright:
            browser, context = await self.create_browser_context(playwright)
            
            try:
                all_results = {}
                for model_key, url in SCRAPING_URLS.items():
                    result = await self.scrape_single_url(context, url, model_key)
                    all_results[model_key] = result
                    await asyncio.sleep(SCRAPING_DELAY)
                return all_results
            finally:
                await browser.close()
    
    def save_results(self, results: Dict[str, Any]):
        with open("live_data.json", 'w') as f:
            json.dump(results, f, indent=2)
        offers_data, reviews_data, qna_data = {}, {}, {}
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
    scraper = LaptopScraper()
    results = await scraper.scrape_all_urls()
    scraper.save_results(results)
    print("\nScraping completed!")
    total_offers = sum(len(data.get("offers", [])) for data in results.values())
    total_reviews = sum(len(data.get("reviews", [])) for data in results.values())
    total_qna = sum(len(data.get("qna", [])) for data in results.values())
    print(f"Total offers: {total_offers}")
    print(f"Total reviews: {total_reviews}")
    print(f"Total Q&A: {total_qna}")

if __name__ == "__main__":
    asyncio.run(main())
