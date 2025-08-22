# models.py
from typing import List, Dict, Optional, TypedDict
from pydantic import BaseModel

class SearchConfig(BaseModel):
    # user-provided
    role: str
    country: str
    pages: Optional[int] = 5     # user can omit; default 3 pages
    # engine/runtime
    per_page: int = 10           # Google default
    dedupe: bool = True
    batch_size: int = 5          # Playwright scraping batch size
    output_csv: str = "output.csv"
    browser: str = "chromium"    # "chromium" | "firefox" | "webkit"
    storage_state: str = "linkedin_auth.json"  # saved session for LinkedIn

class Profile(BaseModel):
    name: str = ""
    about: str = ""
    gmail: str = ""
    url: str

class GraphState(TypedDict):
    config: SearchConfig
    query_base: str            # e.g. site:linkedin.com/in "founder" "@gmail.com" "united kingdom"
    current_page: int          # 1-based page index while searching Google
    urls: List[str]            # aggregated LinkedIn profile URLs
    batches: List[List[str]]   # chunked URLs for scraping
    current_batch: List[str]   # batch currently being scraped
    batch_results: List[Dict]  # now holds structured rows before save, or {"url","lines"} right after scraping
