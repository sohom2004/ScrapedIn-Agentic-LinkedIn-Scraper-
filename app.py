# streamlit_app.py
import os
import streamlit as st
from dotenv import load_dotenv
import subprocess

from models import SearchConfig
from workflow import Workflow

import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def ensure_storage_state(path: str):
    """Ensure the Playwright storage_state.json exists. If missing, run runner.py."""
    if not os.path.exists(path):
        st.warning(
            f"{path} not found.\n"
            "Attempting to generate LinkedIn auth details by running runner.py..."
        )

        try:
            # Run runner.py automatically
            result = subprocess.run(
                ["python", "./runner.py"],
                check=True,
                capture_output=True,
                text=True
            )
            st.info(result.stdout)  # Show output logs in Streamlit
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Failed to generate auth details.\n{e.stderr}")
            st.stop()

        # Re-check after running runner.py
        if not os.path.exists(path):
            st.error("❌ Auth still not created. Please log in manually.")
            st.stop()


def run_scraper(role, country, pages, batch_size, output_csv, browser, storage_state):
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

    workflow = Workflow()
    workflow.run(cfg)

    return cfg.output_csv


# ----------------- Streamlit UI -----------------
def main():
    load_dotenv()
    st.title("🔍 ScrapedIn")

    st.sidebar.header("Configuration")

    role = st.sidebar.text_input("Role", value=os.getenv("ROLE", "founder"))
    country = st.sidebar.text_input("Country", value=os.getenv("COUNTRY", "united kingdom"))
    pages = st.sidebar.number_input("Pages", min_value=1, max_value=20, value=int(os.getenv("PAGES", "3")))
    batch_size = int(os.getenv("BATCH_SIZE", "5"))
    output_csv = st.sidebar.text_input("Output CSV filename", value=os.getenv("OUTPUT", "output.csv"))
    browser = st.sidebar.selectbox("Browser", ["chromium", "firefox", "webkit"], index=0)
    storage_state = os.getenv("STORAGE_STATE", "linkedin_auth.json")

    if st.button("🚀 Run Scraper"):
        with st.spinner("Running scraper..."):
            try:
                output_path = run_scraper(role, country, pages, batch_size, output_csv, browser, storage_state)
                st.success(f"✅ Done. Results saved to: {output_path}")

                # Optionally, show a preview of CSV if exists
                if os.path.exists(output_path):
                    import pandas as pd
                    df = pd.read_csv(output_path)
                    st.dataframe(df.head(20))  # preview first 20 rows
                    st.download_button("⬇️ Download CSV", df.to_csv(index=False), file_name=output_path)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
