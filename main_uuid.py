"""
Tier 3 scraper: Playwright headless, chỉ để lấy FB numeric ID (userID/pageID) từ HTML.
"""

import re
from fastapi import FastAPI, HTTPException

app = FastAPI()

PATTERNS = [
    r'"userID":"(\d+)"',
    r'"entity_id":"(\d+)"',
    r'"profile_id":"(\d+)"',
    r'"pageID":"(\d+)"',
    r"fb://profile/(\d+)",
    r"fb://page/(\d+)",
]


def _get_async_playwright():
    try:
        from playwright.async_api import async_playwright

        return async_playwright
    except Exception:
        return None


async def get_uuid_via_playwright(url: str) -> str | None:
    async_playwright = _get_async_playwright()
    if not async_playwright:
        print(f"Playwright not available")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                # Block heavy resources
                await page.route(
                    "**/*.{png,jpg,jpeg,css,woff2,svg,gif}",
                    lambda route: route.abort(),
                )
                # page.goto(url, wait_until="networkidle")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                html = await page.content()

                for pattern in PATTERNS:
                    m = re.search(pattern, html, re.S)
                    if m:
                        return m.group(1)
                return None
            finally:
                await browser.close()
    except Exception as e:
        print(f"[-] Playwright browser error: {e}")
        return None


@app.get("/get_uuid")
async def get_uuid(url: str):
    uid = await get_uuid_via_playwright(url)
    if not uid:
        raise HTTPException(status_code=404, detail="UUID not found")
    return {"url": url, "uuid": uid}


@app.get("/health")
def health():
    return {"status": "ok"}
