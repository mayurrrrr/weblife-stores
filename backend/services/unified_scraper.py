import asyncio, json, re, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Page
from tenacity import retry, stop_after_attempt, wait_fixed

from .targets import TARGETS

OUT_OFFERS = Path("live_offers.json")
OUT_REVIEWS = Path("live_reviews.json")
OUT_QNA = Path("live_qna.json")


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
    s = str(txt)
    m = re.search(r"\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})", s.replace(",", ""))
    return float(m.group(1)) if m else None


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
    await page.wait_for_timeout(1500)
    ld = await read_jsonld_from_dom(page)
    prod = extract_product_from_jsonld(ld)

    offers = {}
    agg = {}
    if prod:
        offers = prod.get("offers") or {}
        agg = prod.get("aggregateRating") or {}

    price_text = None
    if not offers or not offers.get("price"):
        # Check selectors sequentially to avoid invalid mixed selectors
        for sel in [
            "[data-test='pricingPrice']",
            "[data-testid='pricingPrice']",
            ".price",
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    price_text = await el.text_content()
                    break
            except Exception:
                continue
        # Regex text locator as a last fallback
        if not price_text:
            try:
                tel = page.locator(r"text=/\$\s?\d[\d,]*\.?\d*/").first
                if await tel.is_visible():
                    price_text = await tel.text_content()
            except Exception:
                pass

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

    shipping_eta = None
    try:
        ship_el = page.locator(r"text=/Ships in|Delivery|Ship by/i").first
        if await ship_el.is_visible():
            shipping_eta = (await ship_el.text_content() or "").strip()
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
    await page.goto(url, wait_until="domcontentloaded")
    await page.mouse.wheel(0, 1200)
    await page.wait_for_timeout(1500)

    aggregate = {"source_url": url, "fetched_at": now_iso()}
    text = await page.locator("body").inner_text()
    m = re.search(r"([0-5]\.?[0-9]?)\s*out of\s*5", text, re.I)
    if m:
        aggregate["aggregate_rating"] = m.group(1)
    m2 = re.search(r"(\d{1,4})\s+reviews", text, re.I)
    if m2:
        aggregate["aggregate_review_count"] = m2.group(1)

    reviews: List[Dict[str, Any]] = []
    cards = page.locator(".review, .bv-content-item, [data-bv-review-id], article")
    cnt = await cards.count()
    for i in range(min(cnt, 200)):
        c = cards.nth(i)
        rating = None
        try:
            raria = await c.locator("[aria-label*='out of 5']").first.get_attribute("aria-label")
            if raria:
                mm = re.search(r"([0-5]\.?[0-9]?)\s*out of 5", raria, re.I)
                if mm:
                    rating = mm.group(1)
        except Exception:
            pass
        if not rating:
            try:
                rtxt = await c.locator(".rating, .bv-off-screen").first.text_content()
                if rtxt:
                    mm2 = re.search(r"([0-5]\.?[0-9]?)\s*out of 5", rtxt, re.I)
                    if mm2:
                        rating = mm2.group(1)
            except Exception:
                pass

        body = None
        title = None
        author = None
        date = None
        try:
            body = await c.locator(".bv-content-review-text, .content, .review-body, [itemprop='reviewBody']").first.text_content()
        except Exception:
            pass
        try:
            title = await c.locator(".review-title, .bv-content-title, [itemprop='name']").first.text_content()
        except Exception:
            pass
        try:
            author = await c.locator(".bv-author, .review-author, [itemprop='author']").first.text_content()
        except Exception:
            pass
        try:
            date = await c.locator("time, [itemprop='datePublished']").first.get_attribute("datetime")
            if not date:
                date = await c.locator("time").first.text_content()
        except Exception:
            pass

        if any([rating, body, title]):
            reviews.append({
                "source_url": url,
                "rating": rating,
                "title": title.strip() if title else None,
                "body": body.strip() if body else None,
                "author": author.strip() if author else None,
                "date": (date.strip() if isinstance(date, str) else date),
                "fetched_at": now_iso(),
            })

    qna: List[Dict[str, Any]] = []
    qblocks = page.locator(".qa, .question, .bv-question, [data-bv-question-id]")
    qcnt = await qblocks.count()
    for i in range(min(qcnt, 200)):
        q = qblocks.nth(i)
        qtxt = None
        ans = None
        try:
            qtxt = await q.locator(".question-text, .bv-question-summary, .bv-content-summary-body, [itemprop='question']").first.text_content()
        except Exception:
            pass
        try:
            ans = await q.locator(".answer, .bv-answer, [data-bv-answer-id], [itemprop='acceptedAnswer']").first.text_content()
        except Exception:
            pass
        if qtxt or ans:
            qna.append({
                "source_url": url,
                "question": qtxt.strip() if qtxt else None,
                "answer": ans.strip() if ans else None,
                "fetched_at": now_iso(),
            })

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

        for key in ["lenovo_e14_intel", "lenovo_e14_amd"]:
            url = TARGETS[key]["pdp"]
            try:
                data = await scrape_lenovo_pdp(page, url)
                offers[key].append(data)
            except Exception as e:
                print(f"[WARN] Lenovo scrape failed for {key}: {e}")

        for key in ["hp_probook_440", "hp_probook_450"]:
            url = TARGETS[key]["pdp"]
            try:
                data = await scrape_hp_pdp(page, url)
                offers[key].append(data)
            except Exception as e:
                print(f"[WARN] HP PDP scrape failed for {key}: {e}")

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

    OUT_OFFERS.write_text(json.dumps(offers, indent=2), encoding="utf-8")
    OUT_REVIEWS.write_text(json.dumps(reviews_map, indent=2), encoding="utf-8")
    OUT_QNA.write_text(json.dumps(qna_map, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_OFFERS}, {OUT_REVIEWS}, {OUT_QNA}")


if __name__ == "__main__":
    asyncio.run(main())
