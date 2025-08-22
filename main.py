# main.py
import os
import argparse
from dotenv import load_dotenv

from models import SearchConfig
from workflow import Workflow


def ensure_storage_state(path: str):
    """Check if the Playwright storage_state.json exists."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found.\n"
            "Run the login script first to create it:\n"
            "  python runner.py"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="LinkedIn search + scrape pipeline")
    parser.add_argument("--role", type=str, help="Role to search for (e.g., founder)")
    parser.add_argument("--country", type=str, help="Country (e.g., united kingdom)")
    parser.add_argument("--pages", type=int, help="Number of Google pages to paginate")
    parser.add_argument("--batch-size", type=int, help="Scraping batch size")
    parser.add_argument("--output-csv", type=str, help="Output CSV path")
    parser.add_argument("--browser", type=str, choices=["chromium", "firefox", "webkit"])
    parser.add_argument("--storage-state", type=str, help="Path to Playwright storage_state JSON")
    return parser.parse_args()


if __name__ == "__main__":
    load_dotenv()
    args = parse_args()

    # prefer CLI > ENV > defaults
    role = args.role or os.getenv("ROLE") or "founder"
    country = args.country or os.getenv("COUNTRY") or "united kingdom"

    pages_env = os.getenv("PAGES")
    pages = args.pages if args.pages is not None else (int(pages_env) if pages_env else 3)

    batch_size = args.batch_size or int(os.getenv("BATCH_SIZE", "5"))
    output_csv = args.output_csv or os.path.join(os.getcwd(), "output.csv")
    browser = args.browser or os.getenv("BROWSER", "chromium")
    storage_state = args.storage_state or os.getenv("STORAGE_STATE", "linkedin_auth.json")

    # build config
    cfg = SearchConfig(
        role=role,
        country=country,
        pages=pages,
        batch_size=batch_size,
        output_csv=output_csv,
        browser=browser,
        storage_state=storage_state,
    )

    ensure_storage_state(cfg.storage_state)

    # run workflow
    workflow = Workflow()
    workflow.run(cfg)

    print(f"✅ Done. Results saved to: {cfg.output_csv}")
