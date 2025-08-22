from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.linkedin.com/login")

    print("Please log in manually in the opened browser window...")
    input("Press Enter here after you have logged in successfully...")

    context.storage_state(path="./linkedin_auth.json")
    print("✅ Login session saved to linkedin_auth.json")
    browser.close()
