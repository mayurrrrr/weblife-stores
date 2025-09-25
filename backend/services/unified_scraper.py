import asyncio, json, re, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Page
from tenacity import retry, stop_after_attempt, wait_fixed

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from targets import TARGETS

OUT_OFFERS = Path("../data/live/live_offers.json")
OUT_REVIEWS = Path("../data/live/live_reviews.json")
OUT_QNA = Path("../data/live/live_qna.json")


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def money_to_float(txt: Optional[Any]) -> Optional[float]:
    if txt is None:
        return None
    # Accept numeric inputs from JSON-LD directly
    if isinstance(txt, (int, float)):
        try:
            return float(txt)
        except Exception:
            return None
    
    s = str(txt).strip()
    
    # Improved price extraction patterns
    patterns = [
        r'\$\s*([0-9][0-9,]*\.?[0-9]{0,2})',  # $1,234.56
        r'USD\s*\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})',  # USD $1234.56 or USD 1234.56
        r'Price:\s*\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})',  # Price: $1234.56
        r'Starting at\s*\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})',  # Starting at $1234.56
        r'([0-9][0-9,]*\.?[0-9]{0,2})\s*USD',  # 1234.56 USD
        r'([0-9][0-9,]*\.?[0-9]{0,2})',  # Just numbers
    ]
    
    for pattern in patterns:
        m = re.search(pattern, s.replace(",", ""), re.IGNORECASE)
        if m:
            try:
                price = float(m.group(1).replace(",", ""))
                # Sanity check - prices should be reasonable
                if 10 <= price <= 50000:  # Between $10 and $50,000
                    return price
            except (ValueError, IndexError):
                continue
    
    return None


def pick_currency(txt: Optional[Any]) -> Optional[str]:
    if txt is None:
        return None
    s = str(txt)
    if "$" in s or "USD" in s.upper():
        return "USD"
    return None


async def read_jsonld_from_dom(page: Page) -> List[Dict[str, Any]]:
    blocks = page.locator("script[type='application/ld+json']")
    n = await blocks.count()
    out = []
    for i in range(n):
        raw = await blocks.nth(i).text_content()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                out.extend(data)
            else:
                out.append(data)
        except Exception:
            pass
    return out


def extract_product_from_jsonld(ld_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    prod = {}
    for node in ld_list:
        t = node.get("@type") or node.get("@type".lower())
        if not t:
            continue
        if (isinstance(t, str) and t.lower() == "product") or (isinstance(t, list) and "Product" in t):
            prod = node
            break
    return prod


async def scrape_lenovo_pdp(page: Page, url: str) -> Dict[str, Any]:
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    # Try to dismiss any popups/cookies
    try:
        popup_selectors = ["button:has-text('Accept')", "button:has-text('Close')", ".modal-close", "[aria-label='Close']"]
        for sel in popup_selectors:
            popup = page.locator(sel).first
            if await popup.is_visible():
                await popup.click()
                await page.wait_for_timeout(1000)
                break
    except Exception:
        pass
    
    ld = await read_jsonld_from_dom(page)
    prod = extract_product_from_jsonld(ld)

    offers = {}
    agg = {}
    if prod:
        offers = prod.get("offers") or {}
        agg = prod.get("aggregateRating") or {}

    price_text = None
    # Improved price selectors for Lenovo
    price_selectors = [
        "[data-test='pricingPrice']",
        "[data-testid='pricingPrice']", 
        "[data-testid='price']",
        ".pricing-price",
        ".price-current",
        ".price",
        ".final-price",
        "[class*='price']",
        "[data-price]"
    ]
    
    for sel in price_selectors:
        try:
            el = page.locator(sel).first
            if await el.is_visible():
                price_text = await el.text_content()
                if price_text and '$' in price_text:
                    print(f"[DEBUG] Found price with selector {sel}: {price_text}")
                    break
        except Exception:
            continue
    
    # Fallback: search for price patterns in page text
    if not price_text:
        try:
            # Look for price patterns
            price_patterns = [
                r"text=/\$\s?\d[\d,]*\.?\d*/",
                r"text=/USD\s*\$?\s*\d[\d,]*\.?\d*/",
                r"text=/Price:\s*\$\d[\d,]*\.?\d*/"
            ]
            for pattern in price_patterns:
                tel = page.locator(pattern).first
                if await tel.is_visible():
                    price_text = await tel.text_content()
                    print(f"[DEBUG] Found price with pattern: {price_text}")
                    break
        except Exception:
            pass

    # Improved availability detection
    availability = None
    if offers and offers.get("availability"):
        availability = str(offers.get("availability")).split("/")[-1]

    if not availability:
        # More comprehensive availability detection
        availability_selectors = [
            "[data-testid='availability']",
            ".availability",
            "[class*='stock']",
            "[class*='availability']"
        ]
        
        for sel in availability_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    avail_text = await el.text_content()
                    if avail_text:
                        avail_lower = avail_text.lower()
                        if any(term in avail_lower for term in ['in stock', 'available', 'add to cart']):
                            availability = "InStock"
                            break
                        elif any(term in avail_lower for term in ['out of stock', 'unavailable', 'sold out']):
                            availability = "OutOfStock"
                            break
            except Exception:
                continue
        
        # Fallback text-based detection
        if not availability:
            for phrase, code in [
                ("Add to cart", "InStock"),
                ("Buy now", "InStock"),
                ("In Stock", "InStock"),
                ("Available", "InStock"),
                ("Out of stock", "OutOfStock"),
                ("Sold out", "OutOfStock"),
                ("Temporarily unavailable", "OutOfStock"),
                ("Discontinued", "Discontinued"),
                ("Coming Soon", "PreOrder"),
            ]:
                try:
                    if await page.get_by_text(phrase, exact=False).first.is_visible():
                        availability = code
                        print(f"[DEBUG] Found availability: {phrase} -> {code}")
                        break
                except Exception:
                    continue

    # Improved shipping detection
    shipping_eta = None
    shipping_selectors = [
        "[data-testid='shipping']",
        ".shipping-info",
        ".delivery-info",
        "[class*='shipping']",
        "[class*='delivery']"
    ]
    
    for sel in shipping_selectors:
        try:
            el = page.locator(sel).first
            if await el.is_visible():
                shipping_text = await el.text_content()
                if shipping_text and any(term in shipping_text.lower() for term in ['ship', 'deliver', 'days', 'weeks']):
                    shipping_eta = shipping_text.strip()
                    print(f"[DEBUG] Found shipping info: {shipping_eta}")
                    break
        except Exception:
            continue
    
    # Fallback shipping detection
    if not shipping_eta:
        try:
            ship_patterns = [
                r"text=/Ships? in \d+[\s-]?\d*\s*(?:business\s*)?days?/i",
                r"text=/Deliver(?:y|s) in \d+[\s-]?\d*\s*(?:business\s*)?days?/i",
                r"text=/Free shipping/i",
                r"text=/Ships? by/i"
            ]
            for pattern in ship_patterns:
                ship_el = page.locator(pattern).first
                if await ship_el.is_visible():
                    shipping_eta = (await ship_el.text_content() or "").strip()
                    if len(shipping_eta) < 100:  # Avoid grabbing long text
                        print(f"[DEBUG] Found shipping pattern: {shipping_eta}")
                        break
        except Exception:
            pass

    promos = []
    for t in [
        "Weekly Deals", "Sale", "Save $", "Coupon", "Student Discount", "Free shipping",
    ]:
        try:
            if await page.get_by_text(t, exact=False).first.is_visible():
                promos.append(t)
        except Exception:
            continue

    price_val = offers.get("price") if isinstance(offers, dict) else None
    price = money_to_float(price_val) or money_to_float(price_text)
    cur = offers.get("priceCurrency") if isinstance(offers, dict) else None
    currency = cur or pick_currency(price_val) or pick_currency(price_text)

    agg_rating = None
    agg_count = None
    if agg:
        agg_rating = agg.get("ratingValue")
        agg_count = agg.get("reviewCount") or agg.get("ratingCount")

    return {
        "source_url": url,
        "price": price,
        "currency": currency,
        "availability": availability,
        "shipping_eta": shipping_eta,
        "promo_badges": promos,
        "seller": "Lenovo",
        "aggregate_rating": agg_rating,
        "aggregate_review_count": agg_count,
        "fetched_at": now_iso(),
    }


async def scrape_hp_pdp(page: Page, url: str) -> Dict[str, Any]:
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

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

    price = money_to_float(price_text)
    currency = pick_currency(price_text)

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

    shipping_eta = None
    try:
        eta_el = page.locator(r"text=/Ships (in|by)|Delivery|Est\\. ship/i").first
        if await eta_el.is_visible():
            shipping_eta = (await eta_el.text_content() or "").strip()
    except Exception:
        pass

    promos = []
    for t in ["FREE Storewide Shipping", "3% back in HP Rewards", "Weekly Deals", "Save $", "Instant rebate"]:
        try:
            if await page.get_by_text(t, exact=False).first.is_visible():
                promos.append(t)
        except Exception:
            continue

    agg_rating = None
    agg_count = None
    try:
        ld = await read_jsonld_from_dom(page)
        prod = extract_product_from_jsonld(ld)
        if prod:
            agg = prod.get("aggregateRating") or {}
            agg_rating = agg.get("ratingValue")
            agg_count = agg.get("reviewCount") or agg.get("ratingCount")
    except Exception:
        pass

    return {
        "source_url": url,
        "price": price,
        "currency": currency,
        "availability": availability,
        "shipping_eta": shipping_eta,
        "promo_badges": promos,
        "seller": "HP",
        "aggregate_rating": agg_rating,
        "aggregate_review_count": agg_count,
        "fetched_at": now_iso(),
    }


async def scrape_hp_reviews_page(page: Page, url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    print(f"[DEBUG] Scraping HP reviews from: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    
    # Wait for content to load and scroll to trigger any lazy loading
    await page.wait_for_timeout(3000)
    await page.mouse.wheel(0, 1200)
    await page.wait_for_timeout(2000)
    
    # Try to click "Load more reviews" or similar buttons
    try:
        load_more_selectors = [
            "button:has-text('Show more')",
            "button:has-text('Load more')",
            "button:has-text('View all')",
            ".load-more",
            "[data-testid='load-more']"
        ]
        for selector in load_more_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible():
                    await button.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                continue
    except Exception:
        pass

    aggregate = {"source_url": url, "fetched_at": now_iso()}
    text = await page.locator("body").inner_text()
    
    # Extract aggregate ratings with more patterns
    rating_patterns = [
        r"([0-5]\.?[0-9]?)\s*out of\s*5",
        r"([0-5]\.?[0-9]?)\s*/\s*5",
        r"Rating:\s*([0-5]\.?[0-9]?)",
        r"([0-5]\.?[0-9]?)\s*stars?"
    ]
    for pattern in rating_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            aggregate["aggregate_rating"] = float(m.group(1))
            break
    
    # Extract review count with more patterns
    count_patterns = [
        r"(\d{1,4})\s+reviews?",
        r"(\d{1,4})\s+customer reviews?",
        r"Based on\s+(\d{1,4})\s+reviews?",
        r"(\d{1,4})\s+ratings?"
    ]
    for pattern in count_patterns:
        m2 = re.search(pattern, text, re.I)
        if m2:
            aggregate["aggregate_review_count"] = int(m2.group(1))
            break

    reviews: List[Dict[str, Any]] = []
    
    # Expanded selectors for HP reviews
    review_selectors = [
        ".review",
        ".bv-content-item", 
        "[data-bv-review-id]",
        "article",
        ".review-item",
        ".customer-review",
        ".product-review",
        "[data-testid='review']",
        ".bv-content-review",
        ".review-card"
    ]
    
    cards = None
    for selector in review_selectors:
        cards = page.locator(selector)
        cnt = await cards.count()
        if cnt > 0:
            print(f"[DEBUG] Found {cnt} review elements with selector: {selector}")
            break
    
    if not cards:
        print("[DEBUG] No review elements found with any selector")
        return reviews, [], aggregate
    
    cnt = await cards.count()
    print(f"[DEBUG] Processing {min(cnt, 50)} review cards")
    
    for i in range(min(cnt, 50)):  # Reduced to 50 for faster processing
        c = cards.nth(i)
        rating = None
        
        # Multiple strategies for rating extraction
        rating_selectors = [
            "[aria-label*='out of 5']",
            "[aria-label*='stars']", 
            ".rating",
            ".bv-off-screen",
            ".star-rating",
            "[data-rating]",
            ".review-rating"
        ]
        
        for sel in rating_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    # Try aria-label first
                    aria_label = await el.get_attribute("aria-label")
                    if aria_label:
                        mm = re.search(r"([0-5]\.?[0-9]?)\s*(?:out of 5|stars?)", aria_label, re.I)
                        if mm:
                            rating = float(mm.group(1))
                            break
                    
                    # Try data-rating attribute
                    data_rating = await el.get_attribute("data-rating")
                    if data_rating and data_rating.replace(".", "").isdigit():
                        rating = float(data_rating)
                        break
                    
                    # Try text content
                    rtxt = await el.text_content()
                    if rtxt:
                        mm2 = re.search(r"([0-5]\.?[0-9]?)\s*(?:out of 5|stars?|/5)", rtxt, re.I)
                        if mm2:
                            rating = float(mm2.group(1))
                            break
            except Exception as e:
                continue
        
        # Extract review content with multiple selectors
        body = None
        body_selectors = [
            ".bv-content-review-text",
            ".content", 
            ".review-body",
            "[itemprop='reviewBody']",
            ".review-text",
            ".review-content",
            ".customer-review-text"
        ]
        
        for sel in body_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    body = await el.text_content()
                    if body and len(body.strip()) > 10:  # Ensure meaningful content
                        break
            except Exception:
                continue
        
        # Extract title
        title = None
        title_selectors = [
            ".review-title",
            ".bv-content-title", 
            "[itemprop='name']",
            ".review-headline",
            ".review-summary",
            "h3", "h4", "h5"
        ]
        
        for sel in title_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    title = await el.text_content()
                    if title and len(title.strip()) > 3:
                        break
            except Exception:
                continue
        
        # Extract author
        author = None
        author_selectors = [
            ".bv-author",
            ".review-author", 
            "[itemprop='author']",
            ".reviewer-name",
            ".customer-name"
        ]
        
        for sel in author_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    author = await el.text_content()
                    if author and len(author.strip()) > 1:
                        break
            except Exception:
                continue
        
        # Extract date
        date = None
        try:
            time_el = c.locator("time, [itemprop='datePublished'], .review-date, .date").first
            if await time_el.is_visible():
                date = await time_el.get_attribute("datetime")
                if not date:
                    date = await time_el.text_content()
        except Exception:
            pass

        # Only add review if we have meaningful content
        if rating is not None or (body and len(body.strip()) > 10) or (title and len(title.strip()) > 3):
            reviews.append({
                "source_url": url,
                "rating": rating,
                "title": title.strip() if title else None,
                "body": body.strip() if body else None,
                "author": author.strip() if author else None,
                "date": (date.strip() if isinstance(date, str) and date else date),
                "fetched_at": now_iso(),
            })

    print(f"[DEBUG] Extracted {len(reviews)} reviews")

    # QnA extraction with improved selectors
    qna: List[Dict[str, Any]] = []
    qna_selectors = [
        ".qa",
        ".question", 
        ".bv-question",
        "[data-bv-question-id]",
        ".q-and-a",
        ".faq-item",
        ".question-answer"
    ]
    
    qblocks = None
    for selector in qna_selectors:
        qblocks = page.locator(selector)
        qcnt = await qblocks.count()
        if qcnt > 0:
            print(f"[DEBUG] Found {qcnt} QnA elements with selector: {selector}")
            break
    
    if qblocks:
        qcnt = await qblocks.count()
        for i in range(min(qcnt, 20)):  # Limit QnA to 20 items
            q = qblocks.nth(i)
            qtxt = None
            ans = None
            
            # Question extraction
            question_selectors = [
                ".question-text",
                ".bv-question-summary", 
                ".bv-content-summary-body",
                "[itemprop='question']",
                ".question-content",
                ".q-text"
            ]
            
            for sel in question_selectors:
                try:
                    el = q.locator(sel).first
                    if await el.is_visible():
                        qtxt = await el.text_content()
                        if qtxt and len(qtxt.strip()) > 5:
                            break
                except Exception:
                    continue
            
            # Answer extraction
            answer_selectors = [
                ".answer",
                ".bv-answer", 
                "[data-bv-answer-id]",
                "[itemprop='acceptedAnswer']",
                ".answer-text",
                ".a-text"
            ]
            
            for sel in answer_selectors:
                try:
                    el = q.locator(sel).first
                    if await el.is_visible():
                        ans = await el.text_content()
                        if ans and len(ans.strip()) > 5:
                            break
                except Exception:
                    continue
            
            if qtxt or ans:
                qna.append({
                    "source_url": url,
                    "question": qtxt.strip() if qtxt else None,
                    "answer": ans.strip() if ans else None,
                    "fetched_at": now_iso(),
                })
    
    print(f"[DEBUG] Extracted {len(qna)} QnA items")
    return reviews, qna, aggregate


async def scrape_lenovo_reviews_page(page: Page, url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Scrape Lenovo reviews from product pages or dedicated review pages"""
    print(f"[DEBUG] Scraping Lenovo reviews from: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)
    
    # Click on the "Ratings & Reviews" tab using the exact selector from your HTML
    try:
        # First try the exact selector from your provided HTML
        reviews_tab = page.locator('button[data-tkey="ratingsReviews"]').first
        if await reviews_tab.is_visible():
            print("[DEBUG] Found Ratings & Reviews tab, clicking...")
            await reviews_tab.click()
            await page.wait_for_timeout(3000)
        else:
            # Fallback selectors
            review_tab_selectors = [
                'button[aria-label*="Ratings"]',
                'button[aria-label*="Reviews"]',
                "button:has-text('Reviews')",
                "a:has-text('Reviews')",
                "[data-tab='reviews']",
                ".reviews-tab",
                "#reviews-tab"
            ]
            for selector in review_tab_selectors:
                try:
                    tab = page.locator(selector).first
                    if await tab.is_visible():
                        print(f"[DEBUG] Found reviews tab with selector: {selector}")
                        await tab.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue
    except Exception as e:
        print(f"[DEBUG] Error clicking reviews tab: {e}")
    
    # Scroll to load reviews
    await page.mouse.wheel(0, 1500)
    await page.wait_for_timeout(2000)
    
    aggregate = {"source_url": url, "fetched_at": now_iso()}
    text = await page.locator("body").inner_text()
    
    # Extract aggregate data
    rating_patterns = [
        r"([0-5]\.?[0-9]?)\s*out of\s*5",
        r"([0-5]\.?[0-9]?)\s*/\s*5",
        r"Rating:\s*([0-5]\.?[0-9]?)",
        r"([0-5]\.?[0-9]?)\s*stars?"
    ]
    for pattern in rating_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            aggregate["aggregate_rating"] = float(m.group(1))
            break
    
    count_patterns = [
        r"(\d{1,4})\s+reviews?",
        r"(\d{1,4})\s+customer reviews?",
        r"Based on\s+(\d{1,4})\s+reviews?",
        r"(\d{1,4})\s+ratings?"
    ]
    for pattern in count_patterns:
        m2 = re.search(pattern, text, re.I)
        if m2:
            aggregate["aggregate_review_count"] = int(m2.group(1))
            break
    
    reviews: List[Dict[str, Any]] = []
    
    # Lenovo review selectors - try broader approach first
    review_selectors = [
        "div[data-bv-v='contentItem']",           # Content items from your HTML
        "div[class*='bv-rmr_sc-16dr711']",        # Any div with this class pattern
        "[class*='jEfJcJ']",                      # The specific class from your screenshot
        "section[id='bv-reviews_container'] div", # Any div inside reviews container
    ]
    
    cards = None
    for selector in review_selectors:
        cards = page.locator(selector)
        cnt = await cards.count()
        if cnt > 0:
            print(f"[DEBUG] Found {cnt} Lenovo review elements with selector: {selector}")
            break
    
    # If no cards found with CSS selectors, try XPath
    if not cards or await cards.count() == 0:
        print("[DEBUG] Trying XPath selectors for Lenovo reviews...")
        xpath_selectors = [
            "//div[contains(@class, 'bv-rmr_sc') and contains(@class, '16dr711')]",  # Based on your screenshot
            "//section[contains(@id, 'bv-review')]",
            "//div[contains(@data-bv-v, 'contentitem')]"
        ]
        
        for xpath in xpath_selectors:
            cards = page.locator(f"xpath={xpath}")
            cnt = await cards.count()
            if cnt > 0:
                print(f"[DEBUG] Found {cnt} Lenovo review elements with XPath: {xpath}")
                break
    
    if not cards:
        print("[DEBUG] No Lenovo review elements found")
        return reviews, [], aggregate
    
    cnt = await cards.count()
    print(f"[DEBUG] Processing {min(cnt, 30)} Lenovo review cards")
    
    for i in range(min(cnt, 30)):
        c = cards.nth(i)
        rating = None
        
        # Extract rating - from your NEW screenshot
        rating_selectors = [
            "div[class*='bv-rmr_sc-16dr711-19'][class*='dzPMOO']",  # Rating from your screenshot  
            "div[aria-label*='out of 5']",                          # Aria label rating
            "div[class*='bv-rmr_sc-16dr711-1']"                     # Fallback
        ]
        
        for sel in rating_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    aria_label = await el.get_attribute("aria-label")
                    if aria_label:
                        mm = re.search(r"([0-5]\.?[0-9]?)\s*(?:out of 5|stars?)", aria_label, re.I)
                        if mm:
                            rating = float(mm.group(1))
                            break
                    
                    data_rating = await el.get_attribute("data-rating")
                    if data_rating and data_rating.replace(".", "").isdigit():
                        rating = float(data_rating)
                        break
                    
                    rtxt = await el.text_content()
                    if rtxt:
                        mm2 = re.search(r"([0-5]\.?[0-9]?)\s*(?:out of 5|stars?|/5)", rtxt, re.I)
                        if mm2:
                            rating = float(mm2.group(1))
                            break
            except Exception:
                continue
        
        # Extract review body - from your NEW screenshot
        body = None
        body_selectors = [
            "div[class*='bv-rmr_sc-16dr711-13'][class*='fNeoZ']",  # Review text from your screenshot
            "div[data-bv-v='contentSummary']",                     # Content summary from your HTML
            "div[class*='bv-rmr_sc-16dr711-13']"                   # Fallback
        ]
        
        for sel in body_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    body = await el.text_content()
                    if body and len(body.strip()) > 10:
                        break
            except Exception:
                continue
        
        # Extract title - from your NEW screenshot
        title = None
        title_selectors = [
            "div[class*='bv-rmr_sc-16dr711-14'][class*='fKaKqJ']",  # Title from your screenshot
            "div[data-bv-v='contentHeader']",                       # Header from your HTML
            "div[class*='bv-rmr_sc-16dr711-14']"                    # Fallback
        ]
        
        for sel in title_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    title = await el.text_content()
                    if title and len(title.strip()) > 3:
                        break
            except Exception:
                continue
        
        # Extract author
        author = None
        author_selectors = [
            ".review-author",
            ".reviewer-name", 
            ".customer-name",
            "[itemprop='author']"
        ]
        
        for sel in author_selectors:
            try:
                el = c.locator(sel).first
                if await el.is_visible():
                    author = await el.text_content()
                    if author and len(author.strip()) > 1:
                        break
            except Exception:
                continue
        
        # Extract date
        date = None
        try:
            time_el = c.locator("time, [itemprop='datePublished'], .review-date, .date").first
            if await time_el.is_visible():
                date = await time_el.get_attribute("datetime")
                if not date:
                    date = await time_el.text_content()
        except Exception:
            pass
        
        if rating is not None or (body and len(body.strip()) > 10) or (title and len(title.strip()) > 3):
            reviews.append({
                "source_url": url,
                "rating": rating,
                "title": title.strip() if title else None,
                "body": body.strip() if body else None,
                "author": author.strip() if author else None,
                "date": (date.strip() if isinstance(date, str) and date else date),
                "fetched_at": now_iso(),
            })
    
    print(f"[DEBUG] Extracted {len(reviews)} Lenovo reviews")
    if len(reviews) > 0:
        print(f"[DEBUG] Sample review: {reviews[0]}")
    else:
        print("[DEBUG] No reviews found - checking page content...")
        page_text = await page.locator("body").inner_text()
        if "ThinkPad" in page_text:
            print("[DEBUG] Page loaded correctly (contains ThinkPad)")
        if "review" in page_text.lower():
            print("[DEBUG] Page contains 'review' text")
        if "rating" in page_text.lower():
            print("[DEBUG] Page contains 'rating' text")
    
    # Now click on Q&A tab to get questions and answers
    qna: List[Dict[str, Any]] = []
    try:
        # Click on "Questions & Answers" tab using the exact selector from your HTML
        qna_tab = page.locator('button[data-tkey="questionsAndAnswers"]').first
        if await qna_tab.is_visible():
            print("[DEBUG] Found Questions & Answers tab, clicking...")
            await qna_tab.click()
            await page.wait_for_timeout(3000)
            
            # Scroll to load Q&A content
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(2000)
            
            # Extract Q&A with Lenovo-specific selectors
            qna_selectors = [
                ".qa",
                ".question", 
                ".bv-question",
                "[data-bv-question-id]",
                ".q-and-a",
                ".faq-item",
                ".question-answer",
                ".review-qa"  # Lenovo specific
            ]
            
            qblocks = None
            for selector in qna_selectors:
                qblocks = page.locator(selector)
                qcnt = await qblocks.count()
                if qcnt > 0:
                    print(f"[DEBUG] Found {qcnt} Lenovo QnA elements with selector: {selector}")
                    break
            
            if qblocks:
                qcnt = await qblocks.count()
                for i in range(min(qcnt, 15)):  # Limit to 15 Q&A items
                    q = qblocks.nth(i)
                    qtxt = None
                    ans = None
                    
                    # Question extraction with Lenovo-specific selectors
                    question_selectors = [
                        ".question-text",
                        ".bv-question-summary", 
                        ".bv-content-summary-body",
                        "[itemprop='question']",
                        ".question-content",
                        ".q-text",
                        ".qa-question"
                    ]
                    
                    for sel in question_selectors:
                        try:
                            el = q.locator(sel).first
                            if await el.is_visible():
                                qtxt = await el.text_content()
                                if qtxt and len(qtxt.strip()) > 5:
                                    break
                        except Exception:
                            continue
                    
                    # Answer extraction with Lenovo-specific selectors
                    answer_selectors = [
                        ".answer",
                        ".bv-answer", 
                        "[data-bv-answer-id]",
                        "[itemprop='acceptedAnswer']",
                        ".answer-text",
                        ".a-text",
                        ".qa-answer"
                    ]
                    
                    for sel in answer_selectors:
                        try:
                            el = q.locator(sel).first
                            if await el.is_visible():
                                ans = await el.text_content()
                                if ans and len(ans.strip()) > 5:
                                    break
                        except Exception:
                            continue
                    
                    if qtxt or ans:
                        qna.append({
                            "source_url": url,
                            "question": qtxt.strip() if qtxt else None,
                            "answer": ans.strip() if ans else None,
                            "fetched_at": now_iso(),
                        })
        else:
            print("[DEBUG] Q&A tab not found")
    except Exception as e:
        print(f"[DEBUG] Error extracting Q&A: {e}")
    
    print(f"[DEBUG] Extracted {len(qna)} Lenovo Q&A items")
    return reviews, qna, aggregate


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def get_browser(play):
    # Try mitigating HTTP/2 issues by disabling http2 and setting realistic headers via context
    browser = await play.chromium.launch(headless=True, args=[
        "--disable-http2",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ])
    return browser


async def main():
    offers: Dict[str, List[Dict[str, Any]]] = {k: [] for k in TARGETS}
    reviews_map: Dict[str, List[Dict[str, Any]]] = {k: [] for k in TARGETS}
    qna_map: Dict[str, List[Dict[str, Any]]] = {k: [] for k in TARGETS}

    async with async_playwright() as play:
        browser = await get_browser(play)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = await context.new_page()

        # Scrape Lenovo product pages
        for key in ["lenovo_e14_intel", "lenovo_e14_amd"]:
            url = TARGETS[key]["pdp"]
            try:
                data = await scrape_lenovo_pdp(page, url)
                offers[key].append(data)
            except Exception as e:
                print(f"[WARN] Lenovo scrape failed for {key}: {e}")

        # Scrape HP product pages
        for key in ["hp_probook_440", "hp_probook_450"]:
            url = TARGETS[key]["pdp"]
            try:
                data = await scrape_hp_pdp(page, url)
                offers[key].append(data)
            except Exception as e:
                print(f"[WARN] HP PDP scrape failed for {key}: {e}")

        # Scrape Lenovo reviews from dedicated review URLs with #reviews fragment
        for key in ["lenovo_e14_intel", "lenovo_e14_amd"]:
            for rurl in TARGETS[key]["reviews"]:
                try:
                    rvs, qa, agg = await scrape_lenovo_reviews_page(page, rurl)
                    if agg and offers[key]:
                        o = offers[key][0]
                        if agg.get("aggregate_rating") and not o.get("aggregate_rating"):
                            o["aggregate_rating"] = agg.get("aggregate_rating")
                        if agg.get("aggregate_review_count") and not o.get("aggregate_review_count"):
                            o["aggregate_review_count"] = agg.get("aggregate_review_count")
                    reviews_map[key].extend(rvs)
                    qna_map[key].extend(qa)
                except Exception as e:
                    print(f"[WARN] Lenovo reviews scrape failed for {key} {rurl}: {e}")

        # Scrape HP reviews from dedicated review pages
        for key in ["hp_probook_440", "hp_probook_450"]:
            for rurl in TARGETS[key]["reviews"]:
                try:
                    rvs, qa, agg = await scrape_hp_reviews_page(page, rurl)
                    if agg and offers[key]:
                        o = offers[key][0]
                        if agg.get("aggregate_rating") and not o.get("aggregate_rating"):
                            o["aggregate_rating"] = agg.get("aggregate_rating")
                        if agg.get("aggregate_review_count") and not o.get("aggregate_review_count"):
                            o["aggregate_review_count"] = agg.get("aggregate_review_count")
                    reviews_map[key].extend(rvs)
                    qna_map[key].extend(qa)
                except Exception as e:
                    print(f"[WARN] HP reviews page failed for {key} {rurl}: {e}")

        await context.close()
        await browser.close()

    # Always write offers (working scraper)
    OUT_OFFERS.write_text(json.dumps(offers, indent=2), encoding="utf-8")
    print(f"✅ Wrote {OUT_OFFERS}")
    
    # Only write reviews/QnA if we actually got data (preserve existing dummy data)
    total_reviews = sum(len(reviews) for reviews in reviews_map.values())
    total_qna = sum(len(qna) for qna in qna_map.values())
    
    if total_reviews > 0:
        OUT_REVIEWS.write_text(json.dumps(reviews_map, indent=2), encoding="utf-8")
        print(f"✅ Wrote {OUT_REVIEWS} with {total_reviews} reviews")
    else:
        print(f"⚠️ No reviews scraped, preserving existing {OUT_REVIEWS}")
    
    if total_qna > 0:
        OUT_QNA.write_text(json.dumps(qna_map, indent=2), encoding="utf-8")
        print(f"✅ Wrote {OUT_QNA} with {total_qna} Q&A items")
    else:
        print(f"⚠️ No Q&A scraped, preserving existing {OUT_QNA}")


if __name__ == "__main__":
    asyncio.run(main())
