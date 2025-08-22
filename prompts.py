class LinkedInPrompts:
    """Prompts for search + scraping, with pagination included as user input."""

    # High-level behavior guide for a search agent (kept here for clarity / future LLM use)
    SEARCH_SYSTEM = """You are a web search specialist.
    - Build precise Google queries to find LinkedIn profile pages for people.
    - Include role, country, and heuristics that increase chances of visible emails."""

    @staticmethod
    def search_user(role: str, country: str, pages: int) -> str:
        return f"""Generate Google queries to find LinkedIn profile pages.
        Role: {role}
        Country: {country}
        Pages to paginate: {pages}

        Rules:
        - Use: site:linkedin.com/in
        - Include: "{role}", "@gmail.com", "{country}"
        - Example: site:linkedin.com/in "founder" "@gmail.com" "United Kingdom"
        - We will paginate Google using &start=0,10,20,... (handled in code).
        Return only the base query string we should use before pagination."""

    # Deterministic base query builder (no LLM required)
    @staticmethod
    def build_base_query(role: str, country: str) -> str:
        # Quoting role and country improves precision; gmail heuristic raises chance of email mentions
        return f'site:linkedin.com/in "{role}" "@gmail.com" "{country}"'

    # Scraper guidance (for reference or LLM future use)
    SCRAPER_SYSTEM = """You extract profile fields from LinkedIn pages:
    - name
    - about
    - gmail (if visible on page)
    - url
    Leave missing fields as empty strings."""

    # Save guidance (for reference)
    SAVE_SYSTEM = """Append results to a single CSV file, never overwrite, and deduplicate by URL."""
    
    # -------- NEW: for extraction node --------
    EXTRACT_SYSTEM = "You extract precise fields from noisy LinkedIn text and return STRICT JSON."

    @staticmethod
    def extract_user(url: str, lines: list[str]) -> str:
        return (
            "Extract fields from this LinkedIn profile text.\n"
            "Return a JSON object with exactly these keys:\n"
            '{ "name": "", "role": "", "email": "", "about": "", "url": "" }\n\n'
            "Rules:\n"
            "- name: person's full name if present, else empty string.\n"
            "- role: current role/position or headline.\n"
            "- email: any email on the page (prefer the most plausible personal one). "
            "If none, empty string.\n"
            "- about: short summary (1–3 sentences) synthesized from the text, "
            "or empty if not available.\n"
            f"- url: set to this exact URL: {url}\n"
            "- If uncertain about a field, leave it as an empty string.\n\n"
            "Text lines:\n" + "\n".join(lines[:100])
        )