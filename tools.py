# tools.py
import csv
import re
import time
from pathlib import Path
from typing import List, Dict, Set
from bs4 import BeautifulSoup

import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import time
import random
from typing import List, Set
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs
from playwright.sync_api import sync_playwright

def google_collect_linkedin_urls(query_base: str, pages: int = 3, per_page: int = 10, browser: str = "chromium") -> List[str]:
    """
    Use Playwright to fetch Google SERPs and collect LinkedIn /in/ URLs with improved reliability.
    """
    urls: Set[str] = set()

    def build_url(start: int) -> str:
        return f"https://www.google.com/search?q={quote_plus(query_base)}&start={start}"

    def _clean_linkedin_url(url: str) -> str:
        """Clean and normalize LinkedIn URLs"""
        if not url:
            return ""
        
        # Handle Google redirect URLs
        if url.startswith('/url?'):
            parsed = urlparse(f"https://google.com{url}")
            query_params = parse_qs(parsed.query)
            if 'url' in query_params:
                url = query_params['url'][0]
            elif 'q' in query_params:
                url = query_params['q'][0]
        
        # Clean the LinkedIn URL
        if "linkedin.com/in/" in url:
            # Extract just the LinkedIn profile part
            start_idx = url.find("linkedin.com/in/")
            if start_idx != -1:
                linkedin_part = url[start_idx:]
                # Remove any trailing parameters or fragments
                linkedin_part = linkedin_part.split('?')[0].split('#')[0]
                return f"https://{linkedin_part}"
        
        return url

    with sync_playwright() as p:
        # Use more realistic browser configuration
        browser_obj = getattr(p, browser)
        b = browser_obj.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Set realistic user agent and viewport
        ctx = b.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = ctx.new_page()
        
        # Add stealth measures
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        for page_index in range(pages):
            start = page_index * per_page
            search_url = build_url(start)
            
            print(f"🔍 Fetching page {page_index + 1}/{pages}: {search_url}")
            
            try:
                # Navigate with retry logic
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        response = page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                        if response and response.status == 200:
                            break
                        print(f"⚠️  Response status: {response.status if response else 'None'}, retrying...")
                    except Exception as e:
                        print(f"⚠️  Navigation error (retry {retry + 1}): {e}")
                        if retry == max_retries - 1:
                            raise
                        time.sleep(2)
                
                # Wait for content to load
                page.wait_for_timeout(2000)
                
                # Try multiple selectors for Google results
                selectors_to_try = [
                    "a[href*='linkedin.com/in/']",  # Direct LinkedIn links
                    "div.g a[href]",                # Standard Google result links
                    "h3 a[href]",                   # Title links
                    "a[href^='/url?']",             # Google redirect URLs
                    "a[data-ved]",                  # Google tracked links
                    "a:has(h3)",                    # Links containing h3 elements
                ]
                
                found_links = False
                for selector in selectors_to_try:
                    try:
                        anchors = page.locator(selector)
                        count = anchors.count()
                        
                        if count > 0:
                            print(f"✅ Found {count} links with selector: {selector}")
                            found_links = True
                            
                            for i in range(count):
                                try:
                                    href = anchors.nth(i).get_attribute("href")
                                    if href:
                                        print(f"🔗 Checking link {i+1}/{count}: {href[:100]}...")
                                        
                                        # Check if it's a LinkedIn URL (direct or through redirect)
                                        if ("linkedin.com/in/" in href or 
                                            (href.startswith('/url?') and 'linkedin.com%2Fin%2F' in href)):
                                            
                                            cleaned_url = _clean_linkedin_url(href)
                                            if cleaned_url and "linkedin.com/in/" in cleaned_url:
                                                urls.add(cleaned_url)
                                                print(f"✅ Added LinkedIn URL: {cleaned_url}")
                                
                                except Exception as e:
                                    print(f"⚠️  Error processing link {i}: {e}")
                                    continue
                            
                            # If we found LinkedIn links with this selector, we can break
                            if any("linkedin.com/in/" in url for url in urls):
                                break
                                
                    except Exception as e:
                        print(f"⚠️  Error with selector '{selector}': {e}")
                        continue
                
                if not found_links:
                    print("⚠️  No links found with any selector. Page might be blocked or structure changed.")
                    
                    # Debug: Save page content for inspection
                    if page_index == 0:  # Only for first page to avoid spam
                        content = page.content()
                        print(f"📄 Page title: {page.title()}")
                        print(f"📄 Page content length: {len(content)}")
                        
                        # Check if we're being blocked
                        if any(keyword in content.lower() for keyword in 
                               ['captcha', 'unusual traffic', 'blocked', 'robot']):
                            print("🚫 Detected blocking mechanism")
                        
                        # Optional: Save HTML for manual inspection
                        # with open(f'debug_page_{page_index}.html', 'w', encoding='utf-8') as f:
                        #     f.write(content)
                
                # Random delay between requests
                delay = random.uniform(2, 5)
                print(f"⏳ Waiting {delay:.1f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"❌ Error on page {page_index + 1}: {e}")
                continue

        ctx.close()
        b.close()

    print(f"🎉 Collected {len(urls)} unique LinkedIn URLs")
    return list(urls)


def _clean_linkedin_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    # normalize and keep only profile-like path
    if "/in/" in clean:
        return clean.rstrip("/")
    return clean.rstrip("/")


# ---------- LinkedIn profile scraping ----------
def scrape_linkedin_text(
    url: str,
    browser: str = "chromium",
    storage_state: str = "linkedin_auth.json",
    max_lines: int = 100
) -> List[str]:
    """
    Scrape raw text snippets (h1, span, div) from a LinkedIn profile page.
    Returns up to `max_lines` of text content.
    """
    results = []

    with sync_playwright() as p:
        b = getattr(p, browser).launch(headless=False)
        ctx = b.new_context(storage_state=storage_state)
        page = ctx.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        html = page.content()
        ctx.close()
        b.close()

    # --- Parse with BeautifulSoup ---
    soup = BeautifulSoup(html, "html.parser")

    # Collect <h1>, <span>, <div>
    for tag in soup.find_all(["h1", "span", "div"]):
        text = tag.get_text(strip=True)
        if text:
            results.append(text)
        if len(results) >= max_lines:
            break

    return results


def scrape_batch(
    urls: List[str],
    browser: str = "chromium",
    storage_state: str = "linkedin_auth.json",
    max_lines: int = 100,
) -> List[Dict]:
    """
    Scrape a batch of LinkedIn profiles into raw text lines.
    Returns: [{"url": <profile_url>, "lines": [<up to max_lines text lines>]}, ...]
    """
    out: List[Dict] = []
    for u in urls:
        try:
            lines = scrape_linkedin_text(
                u,
                browser=browser,
                storage_state=storage_state,
                max_lines=max_lines,
            )
            out.append({"url": u, "lines": lines})
        except Exception as e:
            out.append({"url": u, "lines": [], "error": str(e)})
        time.sleep(1.0)  # polite delay
    return out


# ---------- CSV append + dedupe ----------
def write_profiles_csv(rows: List[Dict], path: str) -> str:
    """
    Append rows to CSV, deduping by URL.
    Expects each row to have: name, role, email, about, url
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Dedupe by existing URLs in file (if any)
    seen: Set[str] = set()
    existing_headers = []
    if p.exists():
        with p.open("r", encoding="utf-8", newline="") as f:
            rdr = csv.reader(f)
            try:
                existing_headers = next(rdr)
            except StopIteration:
                existing_headers = []
        # If an old file has a different header (e.g., older schema), write to a new file suffix
        target_headers = ["name", "role", "email", "about", "url"]
        if existing_headers and existing_headers != target_headers:
            p = p.with_name(p.stem + "_v2" + p.suffix)

    # Recompute seen from the (possibly rotated) file
    if p.exists():
        with p.open("r", encoding="utf-8", newline="") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                if r.get("url"):
                    seen.add(r["url"])

    headers = ["name", "role", "email", "about", "url"]
    new_rows = [r for r in rows if r.get("url") and r["url"] not in seen]

    write_header = not p.exists()
    with p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        if write_header:
            w.writeheader()
        for r in new_rows:
            # Ensure keys exist even if empty
            row = {
                "name": r.get("name", ""),
                "role": r.get("role", ""),
                "email": r.get("email", ""),
                "about": r.get("about", ""),
                "url": r.get("url", ""),
            }
            w.writerow(row)

    return f"Wrote {len(new_rows)} new rows to {p} (skipped {len(rows) - len(new_rows)} duplicates)."


# ---------- batching helper ----------
def chunk_list(items: List[str], size: int) -> List[List[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]
